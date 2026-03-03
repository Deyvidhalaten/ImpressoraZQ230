from flask import Blueprint, request, jsonify
from app.services.auth_service import check_login, generate_auth_token

bp = Blueprint("auth_controller", __name__, url_prefix="/api")

@bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return "", 204
    
    data = request.get_json(force=True)
    user = data.get("username", "").strip()
    pwd = data.get("password", "").strip()
    
    if check_login(user, pwd):
        token = generate_auth_token(user)
        return jsonify({"success": True, "token": token})
    
    return jsonify({"success": False, "error": "Credenciais inválidas"}), 401
