import asyncio

from flask import Blueprint, request, jsonify
from app.services.auth_service import generate_auth_token, realizar_login_ad, get_user_data, Autenticado
from app.services.printing_service import _is_test_mode

bp = Blueprint("auth_controller", __name__, url_prefix="/api")

@bp.route("/login", methods=["POST", "OPTIONS"])
async def login():
    if request.method == "OPTIONS":
        return "", 204
    
    data = request.get_json(force=True)
    user = data.get("username", "").strip()
    pwd = data.get("password", "").strip()
    
    # Login Bypass for Test Mode
    if _is_test_mode():
        user_data = get_user_data(user)
        if user_data:
            autenticado = Autenticado(sucesso=True, mensagem="DEBUG: Login AD bypass ativo.", status=200)
        else:
            autenticado = Autenticado(sucesso=False, mensagem="Usuário local não existe. Crie no users.json.", status=401)
    else:
        autenticado = await realizar_login_ad(user, pwd)
        print(autenticado)

    if autenticado.sucesso:

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
