from base64 import urlsafe_b64decode, urlsafe_b64encode
import json
from pathlib import Path
import platform
from typing import Any
from aiohttp import ClientSession
from pydantic import BaseModel
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app, request, jsonify
from functools import wraps
from cryptography.fernet import Fernet 

from dotenv import load_dotenv

load_dotenv()  # Carrega variaveis do .env local se existir

def get_users_file() -> Path:
    return current_app.config["DIRS"]["data"] / "users.json"

def init_users_file(data_dir: Path):
    users_file = data_dir / "users.json"
    if not users_file.exists():
        users_file.parent.mkdir(parents=True, exist_ok=True)
        # default user: admin, nivel 3 (max), com acesso global representado por '*'
        default_user = {
            "deyvid.silva": {
                "nivel": 3,
                "lojas": ["*"]
            },
            "fabiano.bertoti": {
                "nivel": 3,
                "lojas": ["*"]
            }
        }
        with users_file.open("w", encoding="utf-8") as f:
            json.dump(default_user, f, indent=4)

def get_user_data(username: str) -> dict:
    users_file = get_users_file()
    if not users_file.exists():
        return None
    try:
        with users_file.open("r", encoding="utf-8") as f:
            users = json.load(f)
            return users.get(username)
    except Exception:
        return None


def generate_auth_token(username: str) -> str:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    user_data = get_user_data(username)
    nivel = user_data.get("nivel", 1) if user_data else 1
    lojas = user_data.get("lojas", []) if user_data else []
    return s.dumps({"user": username, "nivel": nivel, "lojas": lojas}, salt="admin-auth")

def verify_auth_token(token: str, max_age=86400): # 1 dia
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = s.loads(token, salt="admin-auth", max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return data

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Autenticação requerida"}), 401
            
        token = auth_header.split(" ")[1]
        user_data = verify_auth_token(token)
        if not user_data or "user" not in user_data:
            return jsonify({"success": False, "error": "Token inválido ou expirado"}), 401
            
        return f(*args, **kwargs)
    return decorated

def require_admin_nivel(min_nivel: int):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method == "OPTIONS":
                return f(*args, **kwargs)
                
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"success": False, "error": "Autenticação requerida"}), 401
                
            token = auth_header.split(" ")[1]
            user_data = verify_auth_token(token)
            if not user_data or "user" not in user_data:
                return jsonify({"success": False, "error": "Token inválido ou expirado"}), 401
                
            if user_data.get("nivel", 1) < min_nivel:
                return jsonify({"success": False, "error": "Acesso negado: Nível de administrador insuficiente"}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


import os
BAPI = os.environ.get("BSTK_BAPI", "https://api.bistek.com.br")

# A validação local da API Bistek com o HEADERS removido a pedido do dev
# TOKEN_AD fica reservado para outros testes caso seja necessário depois
def get_ad_headers() -> dict:
    return {
        "Content-Type": "application/json",
    }

class Autenticado(BaseModel):
    sucesso: bool = False
    mensagem: str = "Nenhuma"
    status: int = 401


async def patch_bapi_autenticador(envio: dict) -> Autenticado:
    # O dev da API da Bistek não permite a injeção do HEADER de Bearer padrão
    # Este trecho envia EXATAMENTE os dados criptografados e lida com o token JWT que será assinado depois.
    async with ClientSession() as s:
        async with s.patch(f"{BAPI}/ad/autenticacao", json=envio, ssl=False) as r:
            retorno = {"ok": False}
            if r.status in(200, 400, 401):
                retorno = await r.json()
            return Autenticado(
                sucesso=retorno.get("ok") or False,
                mensagem=str(retorno.get("msg") or r.reason),
                status=r.status,
            )


def decode(d: Any = None) -> str:
    return urlsafe_b64encode(d or Fernet.generate_key()).decode("UTF-8")


def empacota(segredo: str, dado: dict) -> str:
    return decode(
        urlsafe_b64decode(
            Fernet(urlsafe_b64decode(segredo)).encrypt(
                json.dumps(dado).encode()
            )
        )
    )


async def realizar_login_ad(usuario: str, senha: str) -> Autenticado:
    if not usuario:
        return Autenticado(mensagem="Usuário não informado")
    if not senha:
        return Autenticado(mensagem="Senha não informada")

    try:
        segredo = [decode() for _ in range(2)]
        password = empacota(segredo[1], {"senha": senha})
        dado = empacota(segredo[0], {
            "login":usuario, "token": segredo[1], "pass": password
        })
        envio = {"data": dado, "secret": segredo[0]}
        return await patch_bapi_autenticador(envio)
    except Exception as e:
        print(f"[Erro Login AD] Falha na comunicação: {str(e)}")
        return Autenticado(mensagem="Informações inválidas ou usuário não cadastrado.")


def isWindows() -> bool:
    return platform.system() == "Windows"