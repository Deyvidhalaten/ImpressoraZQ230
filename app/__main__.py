import os, sys, ssl, urllib3
from flask import Flask
from PIL import ImageFont

from app.constants import BASE_DIR, SECRET_KEY, PERMANENT_SESSION_LIFETIME
from app.bootstrap import init_data_layout, setup_logging
from app.services.log_service import append_log
from app.services.product_service import load_db_flor_from, load_db_flv_from
from app.services.mapping_service import load_printer_map_from
from app.routes.main import bp as main_bp
from app.routes.admin import bp as admin_bp
from jinja2 import Environment, FileSystemLoader

# SSL / Warnings
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Paths de templates/estáticos + base para seeds ---
if getattr(sys, "frozen", False):
    # Executável
    EXE_DIR = os.path.dirname(sys.executable)
    TEMPLATE_DIR = os.path.join(EXE_DIR, "app", "templates")
    STATIC_DIR   = os.path.join(EXE_DIR, "app", "static")
    REPO_BASE    = os.path.join(EXE_DIR, "app")  # onde ficam zpl_templates/seeds no build
else:
    # Dev
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
    STATIC_DIR   = os.path.join(BASE_DIR, "static")
    REPO_BASE    = BASE_DIR

# --- ProgramData + semeadura de seeds/templates ---
DIRS = init_data_layout(REPO_BASE)
setup_logging(DIRS["logs"])  # logger -> ProgramData\logs\app.log

# --- Flask app ---
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME

# Disponibiliza ProgramData e bases às rotas
app.config["DIRS"]   = DIRS
app.config["DB"]     = load_db_flor_from(DIRS["data"])
app.config["DB_FLV"] = load_db_flv_from(DIRS["data"])
zpl_templates_dir = DIRS["templates"]  # ProgramData\BistekPrinter\zpl_templates
app.config["ZPL_ENV"] = Environment(
    loader=FileSystemLoader(zpl_templates_dir),
    autoescape=False,  # desativa escape (ZPL é puro texto)
    trim_blocks=True,
    lstrip_blocks=True
)

# Fonte (fallback)
windows_font = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")
try:
    _ = ImageFont.truetype(windows_font, size=14)
except Exception:
    _ = ImageFont.load_default()

# (Opcional) força leitura inicial de printers.csv só pra validar
_ = load_printer_map_from(DIRS["data"])

# Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)

# Handler simples pra logar 500 com stack
@app.errorhandler(500)
def _err500(e):
    app.logger.exception("Erro 500 na requisição")
    return "Erro interno. Consulte o log em ProgramData\\BistekPrinter\\logs\\app.log", 500

if __name__ == "__main__":
    append_log("startup")
    try:
        app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
    finally:
        append_log("admin.shutdown")
