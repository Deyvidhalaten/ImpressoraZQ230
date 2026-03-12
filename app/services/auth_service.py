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

def get_users_file() -> Path:
    return current_app.config["DIRS"]["data"] / "users.json"

def init_users_file(data_dir: Path):
    users_file = data_dir / "users.json"
    if not users_file.exists():
        users_file.parent.mkdir(parents=True, exist_ok=True)
        # default user: admin, senha: 123
        # Mudar isso na UI mais tarde
        default_user = {
            "deyvid.silva": "2"
        }
        with users_file.open("w", encoding="utf-8") as f:
            json.dump(default_user, f, indent=4)

def check_login(username, password) -> bool:
    users_file = get_users_file()
    if not users_file.exists():
        return False
    try:
        with users_file.open("r", encoding="utf-8") as f:
            users = json.load(f)
    except Exception:
        return False
        
    hashed_pwd = users.get(username)
    if not hashed_pwd:
        return False
        
    return check_password_hash(hashed_pwd, password)

def generate_auth_token(username: str) -> str:
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps({"user": username}, salt="admin-auth")

def verify_auth_token(token: str, max_age=86400): # 1 dia
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = s.loads(token, salt="admin-auth", max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
    return data["user"]

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Autenticação requerida"}), 401
            
        token = auth_header.split(" ")[1]
        user = verify_auth_token(token)
        if not user:
            return jsonify({"success": False, "error": "Token inválido ou expirado"}), 401
            
        return f(*args, **kwargs)
    return decorated


BAPI = "https://api.bistek.com.br" # environ["BSTK_BAPI"]
TOKEN = "eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJIUzI1NiJ9.eyJ1c3VhcmlvIjogImRleXZpZC5zaWx2YSIsICJzZW5oYSI6ICI1Rm4wTipOUCIsICJ0aW1lb3V0IjogMjA4ODY4MTcxMi44Mjk2NTR9.nSqkYEARLEVhKxmnNIPWnoskS-FwN5JqkCYTIAN-Nlk=" # environ["TOKEN_AD"]
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

class Autenticado(BaseModel):
    sucesso: bool = False
    mensagem: str = "Nenhuma"
    status: int = 401


async def patch_bapi_autenticador(envio: dict) -> Autenticado:
    if not TOKEN:
        return Autenticado(mensagem="Token não informado")

    async with ClientSession(headers=HEADERS) as s:
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
        return Autenticado(mensagem=str(e))


def isWindows() -> bool:
    return platform.system() == "Windows"