import asyncio
import fnmatch
from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify, current_app

from app.repositories.printer_repository import load_printer_map_from
from app.services.filial_service import FilialService
from app.services.filial_service import FilialService
from app.services.product_service import ProductService
from app.services.printing_service import enviar_para_impressora_ip, _is_test_mode
from app.services.templates_service import list_templates_by_mode, render_zpl
from app.services.log_service import log_audit, log_error, log_stats
from app.services.trace_service import start_trace
from app.dtos.print_request_dto import PrintRequestDTO

bp = Blueprint("print_controller", __name__, url_prefix="/api")

@bp.route("/print", methods=["POST", "OPTIONS"])
def print_label():
    service = current_app.config.get('PRODUCT_SERVICE')
    if request.method == "OPTIONS":
        return "", 204

    f_service: FilialService = current_app.config.get('FILIAL_SERVICE_INSTANCIA')
    """Recebe JSON e envia para impressora (ou simula)."""
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
    #db = current_app.config["DB_FLV"] if dto.modo == "flv" or "padaria" else current_app.config["DB"]
    try:
        client_ip = request.remote_addr
        rec = None
        
        # Bypass DB Query se o Frontend enviou o DTO preenchido em cache
        if hasattr(dto, 'produto_dados') and dto.produto_dados:
            rec = dto.produto_dados
            trace.add("cache_frontend", hit=True)
        else:
            if is_test:
                cod_empresa = 175
            elif f_service: 
                cod_empresa = f_service.encontra_filial_por_ip(client_ip)
            else:
                cod_empresa = None

            if not cod_empresa:
                return jsonify({"success": False, "error": "Falta de IP ou Base de Filiais Offline (ative o modo teste)"}), 400
            
            res_api = asyncio.run(service.buscar_por_codigo(cod_empresa, dto.codigo))
            if res_api and hasattr(res_api, 'sucesso') and res_api.sucesso:
                dados_brutos = res_api.dados.get("dados", []) if isinstance(res_api.dados, dict) else res_api.dados
                lista = dados_brutos if isinstance(dados_brutos, list) else [dados_brutos]
                rec = lista[0] if lista else None

            trace.add("consulta_db_result", found=bool(rec))
    except Exception as e:
        trace.add("consulta_db_erro", erro=str(e))
        log_error("Erro DB/Cache", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Erro ao consultar banco ou ler cache"}), 500

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
    
    nutri_obj = {
        "porcao": rec.get("PORCAO", ""),
        "kcal": rec.get("VL_CAL_100", rec.get("VL_CALORICO", "")),
        "carb": rec.get("VL_CARBOIDRATOS_100", rec.get("CARBOIDRATOS", "")),
        "prot": rec.get("VL_PROTEINAS_100", rec.get("PROTEINAS", "")),
        "gord": rec.get("VL_GORD_TOT_100", rec.get("GOR_TOT", "")),
        "sat": rec.get("VL_GORD_SAT_100", rec.get("GOR_SAT", "")),
        "trans": rec.get("VL_GORD_TRANS_100", rec.get("GOR_TRANS", "")),
        "fibra": rec.get("VL_FIBRA_100", rec.get("FIBRA", "")),
        "sodio_mg": rec.get("VL_SODIO_100", rec.get("SODIO", "")),
    } if "VL_CAL_100" in rec or "VL_CALORICO" in rec else (rec.get("nutri") or {})
    
    nutri_list = [nutri_obj] if nutri_obj else []

    # Lógica de EAN Dinâmico
    ean_raw = str(rec.get("ean") or rec.get("EAN") or "")
    ean_final = ean_raw
    tipoean = "BE"

    if len(ean_raw) < 13:
        tipoean = "B2"
        if len(ean_raw) < 12:
            ean_final = ean_raw.zfill(12)

    val_dias = rec.get("validade") or 0
    data_hoje = date.today()
    
    try:
        val_dias_int = int(val_dias)
        dataobj = data_hoje + timedelta(days=val_dias_int)
        dataValidade = dataobj.strftime("%d/%m/%Y")
    except:
        # Tenta pegar DT_VALIDADE (que já é string em formato brasileiro da BAPI)
        dataValidade = rec.get("DT_VALIDADE", "")
        
    codprod = str(rec.get('codprod') or rec.get('CODPROD') or rec.get('SEQPRODUTO') or '')
    descricao = str(rec.get('descricao') or rec.get('DESCRICAO') or '')

    ctx = {
        "tipoean": tipoean,
        "modo": dto.modo,
        "texto": descricao[:27],
        "codprod": codprod,
        "ean": ean_final,
        "copies": dto.copies,
        "ls": loja_map.get("ls", {}).get(dto.modo, 0),
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validade": val_dias,
        "infnutri": nutri_list,
        "nutri": nutri_obj,
        "dataValidade": dataValidade,
    }
    
    # Merge de todas as variáveis cruas na raiz do JINJA para flexibilidade nos ZPLs
    for k, v in rec.items():
        if k not in ctx:
            ctx[k] = v

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
        "produto": rec["DESCRICAO"],
    })
