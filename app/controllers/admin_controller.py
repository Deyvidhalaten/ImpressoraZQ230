from flask import Blueprint, request, jsonify, current_app
from app.repositories.printer_repository import load_printer_map_from, save_printer_map_to
from app.services.auth_service import require_auth, require_admin_nivel, verify_auth_token, get_users_file
from app.services.log_service import log_audit
import json

bp = Blueprint("admin_controller", __name__, url_prefix="/api")

@bp.route("/printers", methods=["GET", "OPTIONS"])
@require_auth
def list_printers():
    """Lista todas as impressoras cadastradas (filtradas pelo Nível de Acesso)."""
    if request.method == "OPTIONS":
        return "", 204

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])
    
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    user_data = verify_auth_token(token)
    nivel = user_data.get("nivel", 1)
    lojas_permitidas = user_data.get("lojas", [])

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
        if nivel >= 2 or "*" in lojas_permitidas or str(p.get("loja")).zfill(2) in [str(l).zfill(2) for l in lojas_permitidas]
    ])


@bp.route("/printers", methods=["POST", "OPTIONS"])
@require_auth
def add_printer():
    """Adiciona uma nova impressora."""
    if request.method == "OPTIONS":
        return "", 204
        
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    user_data = verify_auth_token(token)
    nivel = user_data.get("nivel", 1)
    lojas_permitidas = user_data.get("lojas", [])

    data = request.get_json(force=True)
    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    loja = str(data.get("loja", "")).strip()
    if not loja.isdigit():
        return jsonify({"success": False, "error": "Loja inválida"}), 400

    # Nível 1 security check
    if nivel < 2 and "*" not in lojas_permitidas and str(loja).zfill(2) not in [str(l).zfill(2) for l in lojas_permitidas]:
        return jsonify({"success": False, "error": "Acesso negado para criar nesta loja"}), 403

    ip = data.get("ip", "").strip()
    
    # Validação do IP vs Loja para todos os níveis
    # Ex: Loja 17 obriga a rede a ser 10.17.*
    required_prefix = f"10.{int(loja)}."
    if not ip.startswith(required_prefix):
        return jsonify({"success": False, "error": f"O IP da impressora ({ip}) não condiz com a rede da Loja {loja} ({required_prefix}*)"}), 400

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

    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    user_data = verify_auth_token(token)
    nivel = user_data.get("nivel", 1)
    lojas_permitidas = user_data.get("lojas", [])
        
    data = request.get_json(force=True)
    ip = data.get("ip")
    pattern = data.get("pattern")

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])
    
    # Locate the printer to check its store
    target_printer = next((p for p in mappings if p.get("ip") == ip and p.get("pattern") == pattern), None)
    if not target_printer:
        return jsonify({"success": False, "error": "Impressora não encontrada"}), 404
        
    # Nível 1 security check
    target_loja = str(target_printer.get("loja", ""))
    if nivel < 2 and "*" not in lojas_permitidas and target_loja.zfill(2) not in [str(l).zfill(2) for l in lojas_permitidas]:
        return jsonify({"success": False, "error": "Acesso negado para excluir nesta loja"}), 403

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

    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    user_data = verify_auth_token(token)
    nivel = user_data.get("nivel", 1)
    lojas_permitidas = user_data.get("lojas", [])

    data = request.get_json(force=True)
    target_ip = data.get("ip")
    ls_data = data.get("ls", {})
    funcao_data = data.get("funcao")

    DIRS = current_app.config["DIRS"]
    mappings = load_printer_map_from(DIRS["data"])

    updated = False
    for p in mappings:
        if p.get("ip") == target_ip:
            # Nível 1 security check
            target_loja = str(p.get("loja", ""))
            if nivel < 2 and "*" not in lojas_permitidas and target_loja.zfill(2) not in [str(l).zfill(2) for l in lojas_permitidas]:
                return jsonify({"success": False, "error": "Acesso negado para editar LS nesta loja"}), 403
                
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


# ==========================================
# Gestão de Usuários (Nível 2)
# ==========================================

@bp.route("/users", methods=["GET", "OPTIONS"])
@require_admin_nivel(2)
def list_users():
    """Lista usuários cadastrados."""
    if request.method == "OPTIONS":
        return "", 204
    
    users_file = get_users_file()
    if not users_file.exists():
        return jsonify({})
    try:
        with users_file.open("r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/users", methods=["POST", "PUT", "OPTIONS"])
@require_admin_nivel(2)
def save_user():
    """Adiciona ou Edita um usuário."""
    if request.method == "OPTIONS":
        return "", 204
        
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    nivel = int(data.get("nivel", 1))
    lojas = data.get("lojas", [])
    
    if not username:
        return jsonify({"success": False, "error": "Username é obrigatório"}), 400
        
    users_file = get_users_file()
    users = {}
    if users_file.exists():
        with users_file.open("r", encoding="utf-8") as f:
            users = json.load(f)
            
    # Quem está editando:
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    admin_data = verify_auth_token(token)
    
    # Nível 2 não pode criar/editar um usuário para Nível 3
    if admin_data.get("nivel", 1) < 3 and nivel == 3:
        return jsonify({"success": False, "error": "Acesso negado: Você não pode criar administradores nível 3."}), 403
        
    # Impedir que Nível 2 rebaixe Nível 3 ou se rebaixe acidentalmente (front end também deve bloquear)
    if username in users and users[username].get("nivel", 1) == 3 and admin_data.get("nivel", 1) < 3:
        return jsonify({"success": False, "error": "Acesso negado: Você não pode editar um administrador nível 3."}), 403
        
    users[username] = {
        "nivel": nivel,
        "lojas": lojas
    }
    
    with users_file.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)
        
    log_audit("user_saved", ip=request.remote_addr, detalhes=f"username={username}, nivel={nivel}")
    return jsonify({"success": True})

@bp.route("/users/<username>", methods=["DELETE", "OPTIONS"])
@require_admin_nivel(2)
def delete_user(username):
    """Remove um usuário."""
    if request.method == "OPTIONS":
        return "", 204
        
    users_file = get_users_file()
    users = {}
    if users_file.exists():
        with users_file.open("r", encoding="utf-8") as f:
            users = json.load(f)
            
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    admin_data = verify_auth_token(token)
    
    if username not in users:
        return jsonify({"success": False, "error": "Usuário não encontrado"}), 404
        
    # Nível 2 não pode deletar Nível 3
    if users[username].get("nivel", 1) == 3 and admin_data.get("nivel", 1) < 3:
        return jsonify({"success": False, "error": "Acesso negado: Você não pode excluir um administrador nível 3."}), 403

    del users[username]
    
    with users_file.open("w", encoding="utf-8") as f:
        json.dump(users, f, indent=4)
        
    log_audit("user_deleted", ip=request.remote_addr, detalhes=f"username={username}")
    return jsonify({"success": True})

# ==========================================
# Gestão de Templates ZPL (Nível 3)
# ==========================================

@bp.route("/templates", methods=["GET", "OPTIONS"])
@require_admin_nivel(3)
def list_templates():
    """Lista todos os templates ZPL e seus conteúdos textuais."""
    if request.method == "OPTIONS":
        return "", 204
        
    templates_dir = current_app.config["DIRS"]["templates"]
    templates = {}
    
    if templates_dir.exists():
        for file_path in templates_dir.glob("*.zpl.j2"):
            with file_path.open("r", encoding="utf-8") as f:
                templates[file_path.name] = f.read()
                
    return jsonify(templates)

@bp.route("/templates", methods=["POST", "PUT", "OPTIONS"])
@require_admin_nivel(3)
def save_template():
    """Salva conteudo de um template ZPL."""
    if request.method == "OPTIONS":
        return "", 204
        
    data = request.get_json(force=True)
    filename = data.get("filename", "").strip()
    content = data.get("content", "")
    
    if not filename.endswith(".zpl.j2"):
        if not filename.endswith(".zpl"):
            filename += ".zpl.j2"
        else:
            filename += ".j2"
            
    if not filename:
        return jsonify({"success": False, "error": "Nome do arquivo inválido."}), 400
        
    # Validação do Template ZPL para garantir que não vai quebrar as impressões
    try:
        from jinja2 import Environment
        env: Environment = current_app.config.get("ZPL_ENV")
        if env:
            env.parse(content)
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro de sintaxe no ZPL/Jinja: {str(e)}"}), 400
        
    templates_dir = current_app.config["DIRS"]["templates"]
    file_path = templates_dir / filename
    
    with file_path.open("w", encoding="utf-8") as f:
        f.write(content)
        
    log_audit("template_saved", ip=request.remote_addr, detalhes=f"filename={filename}")
    
    # Atualiza o Environment Jinja global da app
    from app.services.templates_service import criar_ambiente_zpl
    current_app.config["ZPL_ENV"] = criar_ambiente_zpl(templates_dir)
    
    return jsonify({"success": True, "filename": filename})

@bp.route("/templates/<filename>", methods=["DELETE", "OPTIONS"])
@require_admin_nivel(3)
def delete_template(filename):
    """Exclui um template ZPL."""
    if request.method == "OPTIONS":
        return "", 204
        
    templates_dir = current_app.config["DIRS"]["templates"]
    file_path = templates_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"success": False, "error": "Arquivo não encontrado."}), 404
        
    try:
        file_path.unlink()
        log_audit("template_deleted", ip=request.remote_addr, detalhes=f"filename={filename}")
        
        # Atualiza o Environment Jinja global da app
        from app.services.templates_service import criar_ambiente_zpl
        current_app.config["ZPL_ENV"] = criar_ambiente_zpl(templates_dir)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": f"Erro ao excluir: {str(e)}"}), 500
