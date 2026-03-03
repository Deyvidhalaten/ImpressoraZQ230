from flask import Blueprint, request, jsonify, current_app
from app.repositories.printer_repository import load_printer_map_from, save_printer_map_to
from app.services.auth_service import require_auth
from app.services.log_service import log_audit

bp = Blueprint("admin_controller", __name__, url_prefix="/api")

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
            "ls": p.get("ls", {}),
        }
        for p in mappings
    ])


@bp.route("/printers", methods=["POST", "OPTIONS"])
@require_auth
def add_printer():
    """Adiciona uma nova impressora."""
    if request.method == "OPTIONS":
        return "", 204
        
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
        "ls": data.get("ls", {}),
    }

    mappings.append(new_printer)
    save_printer_map_to(DIRS["data"], mappings)

    log_audit("printer_add", ip=request.remote_addr, detalhes=f"loja={loja}, nome={new_printer['nome']}")

    return jsonify({"success": True, "printer": new_printer})


@bp.route("/printers", methods=["DELETE", "OPTIONS"])
@require_auth
def delete_printer():
    """Remove uma impressora."""
    if request.method == "OPTIONS":
        return "", 204
        
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
@require_auth
def update_ls():
    """Atualiza LS de uma impressora."""
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(force=True)
    target_ip = data.get("ip")
    ls_data = data.get("ls", {})
    funcao_data = data.get("funcao")

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    updated = False
    for p in mappings:
        if p.get("ip") == target_ip:
            if "ls" not in p: p["ls"] = {}
            p["ls"].update(ls_data)
            
            if funcao_data is not None:
                p["funcao"] = funcao_data
                
            updated = True
            break

    if not updated:
        return jsonify({"success": False, "error": "Impressora não encontrada"}), 404

    save_printer_map_to(DIRS["data"], mappings)
    log_audit("ls_update", ip=request.remote_addr, detalhes=f"ip={target_ip}, ls={ls_data}")

    return jsonify({"success": True})
