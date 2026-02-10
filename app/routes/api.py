# app/routes/api.py
"""
API JSON para o frontend React.
Endpoints:
  GET  /api/context  → retorna loja, impressoras, modos
  POST /api/print    → recebe JSON, imprime (ou simula), retorna status
"""
import fnmatch
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app.services.mapping_service import load_printer_map_from
from app.services.product_service import consulta_Base, busca_por_descricao
from app.services.printing_service import enviar_para_impressora_ip
from app.services.templates_service import list_templates_by_mode, render_zpl
from app.services.log_service import log_audit, log_error
from app.services.trace_service import start_trace

bp = Blueprint("api", __name__, url_prefix="/api")


# ---------------------------------------------------------
# CORS básico para dev local (frontend em porta diferente)
# ---------------------------------------------------------
@bp.after_request
def _add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@bp.route("/context", methods=["GET", "OPTIONS"])
def context():
    """Retorna info de contexto: loja detectada, impressoras, modos disponíveis."""
    if request.method == "OPTIONS":
        return "", 204

    from app.services.printing_service import _is_test_mode

    DIRS = current_app.config["DIRS"]
    data_dir = DIRS["data"]
    templates_dir = DIRS["templates"]

    mappings = load_printer_map_from(data_dir)
    client_ip = request.remote_addr
    is_test_config = _is_test_mode()
    
    # Detecta modo teste: settings.txt OU acesso via localhost
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
    is_test = is_test_config or is_localhost

    # DEBUG
    print(f"[DEBUG /api/context] client_ip={client_ip}, is_test_config={is_test_config}, is_localhost={is_localhost}, is_test={is_test}")

    # Identificação da loja
    loja_map = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
    
    # MODO TESTE: Se não encontrou loja e modo teste está ativo, usa loja fake
    if not loja_map and is_test:
        loja_map = {
            "loja": "9999",
            "pattern": "*",
            "nome": "Impressora Teste",
            "ip": "127.0.0.1",
            "funcao": ["floricultura", "flv"],
            "ls_flor": 0,
            "ls_flv": 0,
        }
        printers = [loja_map]
    elif not loja_map:
        return jsonify({"error": "Loja não cadastrada", "client_ip": client_ip}), 404
    else:
        printers = [p for p in mappings if p["loja"] == loja_map["loja"]]

    # Modos válidos (baseado em templates existentes)
    valid_modes = {
        f.split("_")[0].lower()
        for f in list_templates_by_mode(templates_dir).keys()
    }

    modos_mapeados = {}
    for p in printers:
        for m in p.get("funcao", []):
            chave = m.lower().strip()
            if chave in valid_modes:
                modos_mapeados[chave] = " ".join(x.capitalize() for x in chave.split("_"))

    return jsonify({
        "loja": loja_map["loja"],
        "printers": [
            {
                "ip": p["ip"], 
                "nome": p.get("nome", p["ip"]), 
                "funcao": p.get("funcao", []),
                "ls_flor": p.get("ls_flor", 0),
                "ls_flv": p.get("ls_flv", 0),
            }
            for p in printers
        ],
        "modos": [{"key": k, "label": v} for k, v in sorted(modos_mapeados.items())],
        "ls_flor": loja_map.get("ls_flor"),
        "ls_flv": loja_map.get("ls_flv"),
        "test_mode": is_test,
    })


@bp.route("/search", methods=["GET", "OPTIONS"])
def search_products():
    """Busca produtos por código ou descrição."""
    if request.method == "OPTIONS":
        return "", 204

    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "codigo")  # codigo ou descricao
    modo = request.args.get("modo", "flv").lower()
    
    # Limite opcional, padrão 50 (aumentado de 10)
    try:
        limit = int(request.args.get("limit", 50))
    except:
        limit = 50

    if not query:
        return jsonify({"products": [], "error": "Query vazia"})

    # Seleciona a base de dados correta
    db = current_app.config["DB_FLV"] if modo == "flv" else current_app.config["DB"]

    products = []

    if search_type == "descricao":
        # Busca por descrição - retorna lista
        resultados = busca_por_descricao(query, db, limite=limit)
        products = [
            {
                "codprod": r["codprod"],
                "ean": r["ean"],
                "descricao": r["descricao"],
                "validade": r.get("validade"),
            }
            for r in resultados
        ]
    else:
        # Busca por código - retorna um item (ou lista de 1)
        rec = consulta_Base(query, db)
        if rec:
            products = [{
                "codprod": rec["codprod"],
                "ean": rec["ean"],
                "descricao": rec["descricao"],
                "validade": rec.get("validade"),
            }]

    return jsonify({
        "products": products,
        "count": len(products),
        "query": query,
        "type": search_type,
        "modo": modo,
    })


@bp.route("/print", methods=["POST", "OPTIONS"])
def print_label():
    """Recebe JSON e envia para impressora (ou simula)."""
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(force=True)
    DIRS = current_app.config["DIRS"]
    data_dir = DIRS["data"]

    trace = start_trace("impressao_api")

    modo = data.get("modo", "").lower()
    codigo = data.get("codigo", "").strip()
    copies = max(1, min(int(data.get("copies", 1)), 100))
    printer_ip = data.get("printer_ip")

    trace.add("request", modo=modo, codigo=codigo, copies=copies, printer_ip=printer_ip)

    # Identificação da loja
    from app.services.printing_service import _is_test_mode
    
    mappings = load_printer_map_from(data_dir)
    client_ip = request.remote_addr
    loja_map = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
    
    # Detecta modo teste: settings.txt OU acesso via localhost
    is_test_config = _is_test_mode()
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
    is_test = is_test_config or is_localhost

    # DEBUG TEMPORÁRIO
    print(f"[DEBUG /api/print] client_ip={client_ip}, is_test={is_test}, loja_map={loja_map}")

    # MODO TESTE: Se não encontrou loja e modo teste está ativo, usa loja fake
    if not loja_map and is_test:
        print("[DEBUG] Usando loja fake para modo teste")
        loja_map = {
            "loja": "9999",
            "pattern": "*",
            "nome": "Impressora Teste",
            "ip": "127.0.0.1",
            "funcao": ["floricultura", "flv"],
            "ls_flor": 0,
            "ls_flv": 0,
        }

    if not loja_map:
        print(f"[DEBUG] Loja NÃO encontrada! Retornando 404")
        trace.add("loja_nao_encontrada")
        dados = trace.finish("falha")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Loja não cadastrada"}), 404

    # Consulta produto
    db = current_app.config["DB_FLV"] if modo == "flv" else current_app.config["DB"]
    try:
        rec = consulta_Base(codigo, db)
        trace.add("consulta_db_result", found=bool(rec))
    except Exception as e:
        trace.add("consulta_db_erro", erro=str(e))
        log_error("Erro DB", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Erro ao consultar banco"}), 500

    if not rec:
        trace.add("produto_nao_encontrado", codigo=codigo)
        dados = trace.finish("falha")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Produto não encontrado"}), 404

    # Render ZPL
    tpl = f"{modo}_default.zpl.j2"
    nutri_list = rec.get("info_nutri", [])
    nutri_obj = nutri_list[0] if isinstance(nutri_list, list) and nutri_list else {}

    ctx = {
        "modo": modo,
        "texto": rec["descricao"][:27],
        "codprod": rec["codprod"],
        "ean": rec["ean"],
        "copies": copies,
        "ls": loja_map["ls_flor"] if modo == "floricultura" else loja_map["ls_flv"],
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validade": rec.get("validade"),
        "infnutri": nutri_list,
        "nutri": nutri_obj,
    }

    try:
        zpl = render_zpl(current_app.config["ZPL_ENV"], tpl, **ctx)
        trace.add("render_zpl_success", length=len(zpl))
    except Exception as e:
        trace.add("render_zpl_erro", erro=str(e))
        log_error("Erro render ZPL", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        return jsonify({"success": False, "error": "Erro ao renderizar etiqueta"}), 500

    # Envio (ou simulação)
    trace.add("send_to_printer", ip=printer_ip)
    sucesso = enviar_para_impressora_ip(zpl, printer_ip, client_ip=client_ip)

    if sucesso:
        trace.add("print_success", copies=copies)
    else:
        trace.add("print_failed", ip=printer_ip)

    dados = trace.finish("sucesso" if sucesso else "falha")
    log_audit("impressao" if sucesso else "impressao_falha", trace=dados)

    return jsonify({
        "success": sucesso,
        "message": f"{copies} etiqueta(s) enviadas" if sucesso else "Falha ao enviar",
        "printer_ip": printer_ip,
        "produto": rec["descricao"],
    })


# =============================================================
# ENDPOINTS DE ADMIN - Gerenciamento de Impressoras
# =============================================================

@bp.route("/printers", methods=["GET", "OPTIONS"])
def list_printers():
    """Lista todas as impressoras cadastradas."""
    if request.method == "OPTIONS":
        return "", 204

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    return jsonify([
        {
            "loja": p.get("loja"),
            "nome": p.get("nome", p.get("ip")),
            "ip": p.get("ip"),
            "funcao": p.get("funcao", []),
            "pattern": p.get("pattern"),
            "ls_flor": p.get("ls_flor", 0),
            "ls_flv": p.get("ls_flv", 0),
        }
        for p in mappings
    ])


@bp.route("/printers", methods=["POST"])
def add_printer():
    """Adiciona uma nova impressora."""
    from app.services.mapping_service import save_printer_map_to

    data = request.get_json(force=True)
    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    loja = str(data.get("loja", "")).strip()
    if not loja.isdigit():
        return jsonify({"success": False, "error": "Loja inválida"}), 400

    new_printer = {
        "loja": loja,
        "pattern": f"10.{int(loja)}.*",
        "nome": data.get("nome", ""),
        "ip": data.get("ip", ""),
        "funcao": data.get("funcao", []),
        "ls_flor": int(data.get("ls_flor", 0)),
        "ls_flv": int(data.get("ls_flv", 0)),
    }

    mappings.append(new_printer)
    save_printer_map_to(DIRS["data"], mappings)

    log_audit("printer_add", ip=request.remote_addr, detalhes=f"loja={loja}, nome={new_printer['nome']}")

    return jsonify({"success": True, "printer": new_printer})


@bp.route("/printers", methods=["DELETE"])
def delete_printer():
    """Remove uma impressora."""
    from app.services.mapping_service import save_printer_map_to

    data = request.get_json(force=True)
    ip = data.get("ip")
    pattern = data.get("pattern")

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    original_count = len(mappings)
    mappings = [p for p in mappings if not (p.get("ip") == ip and p.get("pattern") == pattern)]

    if len(mappings) == original_count:
        return jsonify({"success": False, "error": "Impressora não encontrada"}), 404

    save_printer_map_to(DIRS["data"], mappings)
    log_audit("printer_delete", ip=request.remote_addr, detalhes=f"ip={ip}")

    return jsonify({"success": True})


@bp.route("/printers/ls", methods=["PUT", "OPTIONS"])
def update_ls():
    """Atualiza LS de uma impressora."""
    if request.method == "OPTIONS":
        return "", 204

    from app.services.mapping_service import save_printer_map_to

    data = request.get_json(force=True)
    target_ip = data.get("ip")
    ls_flor = int(data.get("ls_flor", 0))
    ls_flv = int(data.get("ls_flv", 0))

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    updated = False
    for p in mappings:
        if p.get("ip") == target_ip:
            p["ls_flor"] = ls_flor
            p["ls_flv"] = ls_flv
            updated = True
            break

    if not updated:
        return jsonify({"success": False, "error": "Impressora não encontrada"}), 404

    save_printer_map_to(DIRS["data"], mappings)
    log_audit("ls_update", ip=request.remote_addr, detalhes=f"ip={target_ip}, ls_flor={ls_flor}, ls_flv={ls_flv}")

    return jsonify({"success": True})


# =============================================================
# ENDPOINTS DE ESTATÍSTICAS
# =============================================================

@bp.route("/stats", methods=["GET", "OPTIONS"])
def get_stats():
    """Retorna estatísticas de impressão baseadas no audit.jsonl corretamente parseado."""
    if request.method == "OPTIONS":
        return "", 204

    import json
    from datetime import datetime, timedelta
    from app.services.mapping_service import load_printer_map_from

    DIRS = current_app.config["DIRS"]
    audit_jsonl = DIRS["logs"] / "audit.jsonl"

    dias = int(request.args.get("dias", 30))
    filtro_loja = request.args.get("loja")

    cutoff = datetime.now() - timedelta(days=dias)

    por_loja = {}
    por_dia = {}
    total = 0
    lojas_set = set()
    
    # Carrega mapeamento de lojas para identificar por IP
    mappings = load_printer_map_from(DIRS["data"])

    if audit_jsonl.exists():
        with open(audit_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    
                    # O formato do log é {"trace_id": "...", "events": [...], ...}
                    events = entry.get("events", [])
                    if not isinstance(events, list):
                        continue

                    # Verifica se houve sucesso de impressão
                    print_success_event = next((e for e in events if e.get("event") == "print_success"), None)
                    if not print_success_event:
                        continue
                        
                    # Verifica explicitamente se NÃO teve produto_nao_encontrado (redundante pois print_success implica que achou, mas pedido explícito)
                    produto_nao_encontrado = next((e for e in events if e.get("event") == "produto_nao_encontrado"), None)
                    if produto_nao_encontrado:
                        continue

                    # Extrai data do evento de sucesso ou do primeiro evento
                    ts_str = print_success_event.get("t") or (events[0].get("t") if events else "")
                    if not ts_str:
                        continue

                    try:
                        # Formato esperado: "YYYY-MM-DD HH:MM:SS"
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                        except:
                            continue

                    if ts < cutoff:
                        continue

                    # Identifica loja pelo IP do evento 'inicio'
                    inicio_event = next((e for e in events if e.get("event") == "inicio"), None)
                    client_ip = inicio_event.get("ip") if inicio_event else None
                    
                    loja = "Desconhecida"
                    if client_ip:
                         # Tenta casar IP com loja usando fnmatch (mesma lógica do context)
                        printer_match = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
                        if printer_match:
                            loja = printer_match["loja"]
                        else:
                            # Tenta extrair do IP se for 10.x.y.z -> x
                            parts = client_ip.split(".")
                            if len(parts) == 4 and parts[0] == "10":
                                loja = parts[1]

                    lojas_set.add(loja)

                    if filtro_loja and loja != filtro_loja:
                        continue

                    # Atualiza contadores
                    copies = int(print_success_event.get("copies", 1))
                    total += copies

                    por_loja[loja] = por_loja.get(loja, 0) + copies

                    dia = ts.strftime("%d/%m")
                    por_dia[dia] = por_dia.get(dia, 0) + copies

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    # Logar erro de parse silenciosamente ou printar em dev
                    continue

    media_diaria = round(total / max(dias, 1), 1)

    return jsonify({
        "total": total,
        "lojas": sorted(list(lojas_set)),
        "media_diaria": media_diaria,
        "por_loja": por_loja,
        "por_dia": por_dia,
    })

