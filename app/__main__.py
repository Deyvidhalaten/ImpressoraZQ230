import asyncio
import os, sys, ssl, urllib3
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from PIL import ImageFont
from dotenv import load_dotenv

# --- SERVIÇOS DE SEGURANÇA E INFRA ---
from app.services.security_service import SecurityService
from app.constants import BASE_DIR, SECRET_KEY, PERMANENT_SESSION_LIFETIME
from app.bootstrap import init_data_layout
from app.repositories.filial_repository import FilialRepository
from app.services.filial_service import FilialService
from app.services.logging_setup import setup_logging
from app.services.log_service import init_loggers, log_exception
from app.services.templates_service import criar_ambiente_zpl
from app.services.auth_service import init_users_file
from app.repositories.printer_repository import load_printer_map_from
from app.services.product_service import ProductService
from werkzeug.middleware.proxy_fix import ProxyFix

# Blueprints
from app.controllers.auth_controller import bp as auth_bp
from app.controllers.context_controller import bp as context_bp
from app.controllers.print_controller import bp as print_bp
from app.controllers.admin_controller import bp as admin_bp
from app.controllers.stats_controller import bp as stats_bp

# SSL / Warnings
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. INICIALIZA O SERVIÇO DE SEGURANÇA
security = SecurityService()

# --- MODO SETUP: CONFIGURAÇÃO INICIAL (python -m app --setup) ---
if "--setup" in sys.argv:
    print("\n" + "="*60)
    print("🔒 BISTEK PRINTER - CONFIGURAÇÃO DE AMBIENTE SEGURO")
    print("="*60)
    
    if security.lock_vault_folder():
        print("✅ Cofre de chaves trancado.")

    url_bapi = "https://api.bistek.com.br"
    security.update_env_file("BSTK_BAPI", url_bapi)
    
    # --- AJUSTE AQUI: Tenta pegar o token do comando primeiro ---
    token_puro = None
    if "--token" in sys.argv:
        try:
            # Pega o próximo item após o "--token"
            idx = sys.argv.index("--token")
            token_puro = sys.argv[idx + 1]
        except (ValueError, IndexError):
            pass

    # Se não veio via argumento, tenta o input (só funcionará se base=None no setup.py)
    if not token_puro:
        try:
            token_puro = input("\nDigite o TOKEN AD de Produção: ").strip()
        except EOFError:
            print("\n❌ Erro: Não foi possível ler o input. Use o parâmetro --token.")
            sys.exit(1)
    
    if token_puro:
        token_crip = security.encrypt_data(token_puro)
        security.update_env_file("TOKEN_AD", token_crip)
        print("\n✅ Token configurado com sucesso!")
    
    sys.exit(0)

# --- MODO SERVIDOR: EXECUÇÃO NORMAL ---

# Define a base do repositório (Frozen para executável, BASE_DIR para Dev)
if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(sys.executable)
    REPO_BASE = os.path.join(EXE_DIR, "app")
else:
    REPO_BASE = BASE_DIR

# 2. INICIALIZAÇÃO DE DIRETÓRIOS E LOGS
DIRS = init_data_layout(REPO_BASE)
init_users_file(DIRS["data"])
loggers = setup_logging(DIRS["logs"])

init_loggers(
    audit=loggers["audit"],
    error=loggers["error"],
    audit_jsonl=DIRS["logs"] / "audit.jsonl",
    stats_csv=DIRS["logs"] / "stats.csv"
)

# 3. CARGA DE CONFIGURAÇÕES (IGNORA A RAIZ DO PROJETO)
# override=True garante que usemos apenas o arquivo da pasta 'config'
load_dotenv(dotenv_path=security.env_path, override=True)
bapi_url = os.getenv("BSTK_BAPI")
token_sujo = os.getenv("TOKEN_AD")

# Descriptografia para a memória RAM
token_ad = security.decrypt_data(token_sujo)


# Verifica se está rodando em Modo Teste Local
is_test_mode = True
try:
    if (DIRS["config"] / "settings.json").exists():
        import json
        with open(DIRS["config"] / "settings.json", "r", encoding="utf-8") as f:
            st = json.load(f)
            is_test_mode = bool(st.get("is_test_mode", 0))
except Exception:
    pass

if (not token_ad or not bapi_url) and not is_test_mode:
    print("\n" + "!"*60)
    print("ERRO CRÍTICO: Configurações de Token ou API ausentes no AppData.")
    print("Por favor, execute o comando: python -m app --setup")
    print("!"*60 + "\n")
    sys.exit(1)
elif (not token_ad or not bapi_url) and is_test_mode:
    print("\n" + "!"*60)
    print("AVISO: Faltam tokens de API, mas o sistema subirá em MODO TESTE (is_test_mode=1)")
    print("As consultas online vão falhar e usarão respostas Dummy (Ex: Loja 17).")
    print("!"*60 + "\n")

# --- FLASK APP SETUP ---
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME
app.config["DIRS"] = DIRS
app.config["ZPL_ENV"] = criar_ambiente_zpl(DIRS["templates"])
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
# 4. INSTANCIAÇÃO DOS SERVIÇOS COM DADOS PROTEGIDOS
filial_repo = FilialRepository(base_url=bapi_url, token=token_ad)
servico_filiais = FilialService(filial_repo)
servico_produtos = ProductService(client_api=bapi_url, token=token_ad)
app.config['TOKEN_AD'] = token_ad
app.config['BSTK_BAPI'] = bapi_url
filial_repo = FilialRepository(base_url=bapi_url, token=token_ad)
app.config['PRODUCT_SERVICE'] = ProductService(client_api=bapi_url, token=token_ad)
app.config['FILIAL_SERVICE_INSTANCIA'] = servico_filiais

# Sincronização inicial de filiais
print("🔄 Sincronizando rede de filiais...")
try:
    sucesso_sync = asyncio.run(servico_filiais.sincronizar_rede())
    if sucesso_sync:
        print(f"✅ Sucesso! {len(servico_filiais.mapa_ip_filial)} filiais carregadas.")
    else:
        print("⚠️  Aviso: Operando com base de filiais local/offline.")
except Exception as e:
    print(f"❌ Falha crítica na sincronização: {e}")

# Fonte e Impressoras
windows_font = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")
try:
    _ = ImageFont.truetype(windows_font, size=14)
except:
    _ = ImageFont.load_default()

# Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(context_bp)
app.register_blueprint(print_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(stats_bp)

# --- SERVIDOR DE FRONTEND ---
if getattr(sys, "frozen", False):
    FRONTEND_DIR = os.path.join(os.path.dirname(sys.executable), "frontend")
else:
    FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

@app.route("/frontend/<path:filename>")
def serve_frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route("/frontend/")
def serve_frontend_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

# Error Handler
@app.errorhandler(500)
def _err500(e):
    log_exception("Erro 500 Interno", erro=str(e))
    return jsonify({"success": False, "error": "Erro interno no servidor"}), 500

@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    from flask import request
    from app.services.log_service import log_audit
    log_audit("system_shutdown", ip=request.remote_addr, detalhes="Shutdown via API")
    import threading
    def kill():
        import time
        time.sleep(1); os._exit(0)
    threading.Thread(target=kill).start()
    return jsonify({"success": True, "message": "Encerrando sistema..."})

# --- EXECUÇÃO ---
if __name__ == "__main__" or __name__ == "app.__main__":
    if not os.environ.get("IMPORT_ONLY"):
        is_dev = os.environ.get("FLASK_ENV") == "development" or hasattr(sys, 'gettrace') and sys.gettrace() is not None
        
        print(f"🚀 BistekPrinter rodando em {'MODO DEBUG' if is_dev else 'MODO PRODUÇÃO'}")
        app.run(
            host="0.0.0.0", 
            port=8000, 
            debug=is_dev,
            use_reloader=False,
            threaded=not is_dev
        )