import json
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app, request, jsonify
from functools import wraps

def get_users_file() -> Path:
    return current_app.config["DIRS"]["data"] / "users.json"

def init_users_file(data_dir: Path):
    users_file = data_dir / "users.json"
    if not users_file.exists():
        users_file.parent.mkdir(parents=True, exist_ok=True)
        # default user: admin, senha: 123
        # Mudar isso na UI mais tarde
        default_user = {
            "admin": generate_password_hash("123")
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
