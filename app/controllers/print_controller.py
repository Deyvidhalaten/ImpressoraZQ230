import fnmatch
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify, current_app

from app.repositories.printer_repository import load_printer_map_from
from app.services.product_service import consulta_Base
from app.services.printing_service import enviar_para_impressora_ip, _is_test_mode
from app.services.templates_service import list_templates_by_mode, render_zpl
from app.services.log_service import log_audit, log_error, log_stats
from app.services.trace_service import start_trace

bp = Blueprint("print_controller", __name__, url_prefix="/api")

@bp.route("/print", methods=["POST", "OPTIONS"])
def print_label():
    """Recebe JSON e envia para impressora (ou simula)."""
    if request.method == "OPTIONS":
        return "", 204

    from app.dtos.print_request_dto import PrintRequestDTO
    
    data = request.get_json(force=True)
    dto = PrintRequestDTO.from_dict(data)

    if not dto.is_valid():
        return jsonify({"success": False, "error": "Parâmetros 'modo' ou 'codigo' ausentes"}), 400

    DIRS = current_app.config["DIRS"]
    data_dir = DIRS["data"]

    trace = start_trace("impressao_api")
    trace.add("request", modo=dto.modo, codigo=dto.codigo, copies=dto.copies, printer_ip=dto.printer_ip)

    # Identificação da loja
    mappings = load_printer_map_from(data_dir)
    client_ip = request.remote_addr
    loja_map = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
    
    # Detecta modo teste
    is_test_config = _is_test_mode()
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
    is_test = is_test_config or is_localhost

    # MODO TESTE: Se não encontrou loja e modo teste está ativo, usa loja fake
    if not loja_map and is_test:
        valid_modes = list(list_templates_by_mode(current_app.config["DIRS"]["templates"]).keys())
        loja_map = {
            "loja": "9999",
            "pattern": "*",
            "nome": "Impressora Teste",
            "ip": "127.0.0.1",
            "funcao": valid_modes,
            "ls": {k: 0 for k in valid_modes},
        }

    if not loja_map:
        trace.add("loja_nao_encontrada")
        dados = trace.finish("falha")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Loja não cadastrada"}), 404

    # Consulta produto
    db = current_app.config["DB_FLV"] if dto.modo == "flv" or "padaria" else current_app.config["DB"]
    try:
        rec = consulta_Base(dto.codigo, db)
        trace.add("consulta_db_result", found=bool(rec))
    except Exception as e:
        trace.add("consulta_db_erro", erro=str(e))
        log_error("Erro DB", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Erro ao consultar banco"}), 500

    if not rec:
        trace.add("produto_nao_encontrado", codigo=dto.codigo)
        dados = trace.finish("falha")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Produto não encontrado"}), 404

    # Seleção do Template
    templates_do_modo = list_templates_by_mode(current_app.config["DIRS"]["templates"]).get(dto.modo, [])
    
    tpl = dto.template
    if not tpl:
        if templates_do_modo:
            tpl = next((t for t in templates_do_modo if t.endswith(".zpl")), templates_do_modo[0])
        else:
            tpl = f"{dto.modo}_default.zpl.j2"
    
    template_path = current_app.config["DIRS"]["templates"] / tpl
    
    nutri_obj = rec.get("nutri") or {} 
    nutri_list = [nutri_obj] if nutri_obj else []

    # Lógica de EAN Dinâmico
    ean_raw = str(rec.get("ean") or "")
    ean_final = ean_raw
    tipoean = "BE"

    if len(ean_raw) < 13:
        tipoean = "B2"
        if len(ean_raw) < 12:
            ean_final = ean_raw.zfill(12)

    dias_para_adicionar = rec.get("validade")
    data = date.today()
    dataobj = data + timedelta(days=dias_para_adicionar)
    dataValidade = dataobj.strftime("%d/%m/%Y")
    ctx = {
        "tipoean": tipoean,
        "modo": dto.modo,
        "texto": rec["descricao"][:27],
        "codprod": rec["codprod"],
        "ean": ean_final,
        "copies": dto.copies,
        "ls": loja_map.get("ls", {}).get(dto.modo, 0),
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validade": rec.get("validade"),
        "infnutri": nutri_list,
        "nutri": nutri_obj,
        "dataValidade": dataValidade,
    }

    try:
        if tpl.endswith(".zpl"):
            from app.services.templates_service import render_zpl_dynamico
            zpl = render_zpl_dynamico(template_path, **ctx)
        else:
            zpl = render_zpl(current_app.config["ZPL_ENV"], tpl, **ctx)
            
        trace.add("render_zpl_success", length=len(zpl))
    except Exception as e:
        trace.add("render_zpl_erro", erro=str(e))
        log_error("Erro render ZPL", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Erro ao renderizar etiqueta"}), 500

    # Envio
    trace.add("send_to_printer", ip=dto.printer_ip)
    sucesso = enviar_para_impressora_ip(zpl, dto.printer_ip, client_ip=client_ip)

    if sucesso:
        trace.add("print_success", copies=dto.copies)
        log_stats(loja=loja_map["loja"], modo=dto.modo, copies=dto.copies)
    else:
        trace.add("print_failed", ip=dto.printer_ip)

    dados = trace.finish("sucesso" if sucesso else "falha")
    log_audit("impressao" if sucesso else "impressao_falha", trace=dados)

    return jsonify({
        "success": sucesso,
        "message": f"{dto.copies} etiqueta(s) enviadas" if sucesso else "Falha ao enviar",
        "printer_ip": dto.printer_ip,
        "produto": rec["descricao"],
    })
