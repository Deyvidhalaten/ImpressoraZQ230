import os, sys, ssl, urllib3
from flask import Flask
from PIL import Image, ImageFont
from .constants import BASE_DIR, SECRET_KEY, PERMANENT_SESSION_LIFETIME
from .bootstrap import init_data_layout, setup_logging
from .services.log_service import append_log
from .bootstrap import init_data_layout
from .services.product_service import load_db_flor_from, load_db_flv_from, consulta_Base
from .services.mapping_service import load_printer_map_from, save_printer_map_to
from .routes.main import bp as main_bp
from .routes.admin import bp as admin_bp

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ProgramData layout (e seed de templates)
DIRS = init_data_layout(BASE_DIR)
setup_logging(DIRS["logs"])

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"),
                     static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME
app.config["DIRS"] = DIRS

# Fonte (igual antes, se você realmente precisa disso aqui)
windows_font = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
try:
    font = ImageFont.truetype(windows_font, size=14)
except Exception:
    font = ImageFont.load_default()

DIRS = init_data_layout(BASE_DIR)          # => DIRS["data"], DIRS["templates"], etc.
app.config["DIRS"] = DIRS

# Bases (mantenho globais para uso na main route)
DB     = load_db_flor_from(DIRS["data"])
DB_FLV = load_db_flv_from(DIRS["data"])

# Onde antes lia printers.csv:
mappings = load_printer_map_from(DIRS["data"])

# e para salvar:
save_printer_map_to(DIRS["data"], mappings)

# Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    append_log("startup")
    try:
        app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
    finally:
        append_log("shutdown")
