import asyncio

from flask import Blueprint, request, jsonify
from app.services.auth_service import check_login, generate_auth_token, realizar_login_ad

bp = Blueprint("auth_controller", __name__, url_prefix="/api")

@bp.route("/login", methods=["POST", "OPTIONS"])
async def login():
    if request.method == "OPTIONS":
        return "", 204
    
    data = request.get_json(force=True)
    user = data.get("username", "").strip()
    pwd = data.get("password", "").strip()
    
    autenticado = await realizar_login_ad(user, pwd)
    print(autenticado)

    if autenticado.sucesso:

        from app.services.auth_service import generate_auth_token
        token = generate_auth_token(user)
        return jsonify({
            "success": True, 
            "token": token,
            "mensagem": autenticado.mensagem
        })
    

    return jsonify({
        "success": False, 
        "error": str(autenticado.mensagem) 
    }), 401
