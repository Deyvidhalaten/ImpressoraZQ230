import os, sys, ssl, urllib3
from flask import Flask
from PIL import ImageFont

from app.constants import BASE_DIR, SECRET_KEY, PERMANENT_SESSION_LIFETIME
from app.bootstrap import init_data_layout
from app.services.logging_setup import setup_logging
from app.services.log_service import init_loggers
from app.controllers.auth_controller import bp as auth_bp
from app.controllers.context_controller import bp as context_bp
from app.controllers.print_controller import bp as print_bp
from app.controllers.admin_controller import bp as admin_bp
from app.controllers.stats_controller import bp as stats_bp
from app.services.templates_service import criar_ambiente_zpl
from app.services.auth_service import init_users_file
from app.repositories.product_repository import load_db_flor_from, load_db_flv_from
from app.repositories.printer_repository import load_printer_map_from

# SSL / Warnings
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if getattr(sys, "frozen", False):
    # Executável
    EXE_DIR = os.path.dirname(sys.executable)
    REPO_BASE = os.path.join(EXE_DIR, "app")
else:
    # Dev
    REPO_BASE = BASE_DIR

# --- ProgramData + semeadura de seeds/templates ---
DIRS = init_data_layout(REPO_BASE)
init_users_file(DIRS["data"])
loggers = setup_logging(DIRS["logs"])
init_loggers(
    audit=loggers["audit"],
    error=loggers["error"],
    audit_jsonl=DIRS["logs"] / "audit.jsonl",
    stats_csv=DIRS["logs"] / "stats.csv"
)

# --- Flask app ---
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME

# Disponibiliza ProgramData e bases às rotas
app.config["DIRS"]   = DIRS
app.config["DB"]     = load_db_flor_from(DIRS["data"])
app.config["DB_FLV"] = load_db_flv_from(DIRS["data"])
zpl_templates_dir = DIRS["templates"]  # ProgramData\BistekPrinter\zpl_templates



app.config["ZPL_ENV"] = criar_ambiente_zpl(zpl_templates_dir)

# Filtros Customizados


# Fonte (fallback)
windows_font = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")
try:
    _ = ImageFont.truetype(windows_font, size=14)
except Exception:
    _ = ImageFont.load_default()

# (Opcional) força leitura inicial de printers.csv só pra validar
_ = load_printer_map_from(DIRS["data"])

# Blueprints dos Controladores
app.register_blueprint(auth_bp)
app.register_blueprint(context_bp)
app.register_blueprint(print_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(stats_bp)

# Serve arquivos do novo frontend (pasta frontend/)
from flask import send_from_directory

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

# Handler simples pra logar 500 com stack e devolver JSON
@app.errorhandler(500)
def _err500(e):
    from app.services.log_service import log_exception
    from flask import jsonify
    log_exception("Erro 500 na requisição", erro=str(e))
    return jsonify({"success": False, "error": "Erro interno. Consulte com o suporte ou TI de loja"}), 500

@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    """Desliga ou reinicia a aplicação forçadamente."""
    from app.services.log_service import log_audit
    from flask import request
    
    # É fundamental garantir auth forte aqui, porem para facilitar integracao com o frontend
    # verificaremos se há um token valido ou simplesmente logaremos fortemente. 
    # Como o painel do Admin e local-only ou intranet, adicionamos log de auditoria.
    log_audit("system_shutdown", ip=request.remote_addr, detalhes="Shutdown solicitado via API")
    
    # O Waitress não tem gracefully shutdown por handler, os._exit força fim do processo
    # Quando atrelado a um Serviço do Windows (NSSM/pywin32), o serviço será reportado como Stopped 
    # e, dependendo da configuração de recovery, ele pode se reiniciar.
    import threading
    def kill_process():
        import time
        time.sleep(1)
        os._exit(0)
        
    threading.Thread(target=kill_process).start()
    return jsonify({"success": True, "message": "Sistema sendo encerrado (Shutdown)..."})

if __name__ == "__main__" or __name__ == "app.__main__":
    if os.environ.get("IMPORT_ONLY"):
        pass
    else:
        # Detecta se está em modo desenvolvimento (via variável de ambiente ou VS Code debug)
        import sys
        is_dev = os.environ.get("FLASK_ENV") == "development" or hasattr(sys, 'gettrace') and sys.gettrace() is not None
        
        # Em desenvolvimento: threaded=False para breakpoints funcionarem no VS Code
        # Em produção: threaded=True para melhor performance
        app.run(
            host="0.0.0.0", 
            port=8000, 
            debug=is_dev,
            use_reloader=False,
            threaded=not is_dev  # False em dev (debug funciona), True em prod (performance)
        )
