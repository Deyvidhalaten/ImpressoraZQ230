import sys
import os
import socket
import tempfile
import urllib3
import win32print  # type: ignore
import win32ui     # type: ignore
import win32con    # type: ignore

from io import BytesIO
from datetime import timedelta
from PIL import Image, ImageWin
from barcode import EAN13
from barcode.writer import ImageWriter
from flask import (
    Flask, render_template, request, redirect,
    flash, session, url_for
)

# --- CONFIGURAÇÃO DE PERSISTÊNCIA ---
BASE_DIR     = (os.path.dirname(sys.executable)
                if getattr(sys, 'frozen', False)
                else os.path.dirname(__file__))
CONFIG_FILE  = os.path.join(BASE_DIR, 'config.txt')

DEFAULT_IP       = "10.17.30.119"
DEFAULT_PORTA    = 9100
DEFAULT_LS_FLOR  = -40
DEFAULT_LS_FLV   = -20

SHUTDOWN_PASSWORD = "admin"
USUARIO           = "admin"
SENHA             = "1234"

IP_IMPRESSORA    = DEFAULT_IP
PORTA_IMPRESSORA = DEFAULT_PORTA
LS_FLOR_VALUE    = DEFAULT_LS_FLOR
LS_FLV_VALUE     = DEFAULT_LS_FLV

def load_config():
    global IP_IMPRESSORA, LS_FLOR_VALUE, LS_FLV_VALUE
    if not os.path.exists(CONFIG_FILE):
        return
    with open(CONFIG_FILE, 'r') as f:
        for line in f:
            if '=' not in line:
                continue
            key, val = line.strip().split('=', 1)
            if key == 'IP_IMPRESSORA':
                IP_IMPRESSORA = val
            elif key == 'LS_FLOR_VALUE':
                try: LS_FLOR_VALUE = int(val)
                except: pass
            elif key == 'LS_FLV_VALUE':
                try: LS_FLV_VALUE = int(val)
                except: pass

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        f.write(f"IP_IMPRESSORA={IP_IMPRESSORA}\n")
        f.write(f"LS_FLOR_VALUE={LS_FLOR_VALUE}\n")
        f.write(f"LS_FLV_VALUE={LS_FLV_VALUE}\n")

load_config()

# --- FLASK APP ---
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = 'chave-secreta'
app.permanent_session_lifetime = timedelta(minutes=5)

# Desativa warnings SSL (se você for usar bwip-js em algum ponto)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Shutdown ---
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    else:
        os._exit(0)

@app.route("/shutdown", methods=["POST"])
def shutdown():
    pwd = request.form.get('shutdown_password', '')
    if pwd == SHUTDOWN_PASSWORD:
        flash("✅ Sistema encerrando...", "success")
        shutdown_server()
        return "Servidor desligado"
    else:
        flash("❌ Senha inválida para encerramento", "error")
        return redirect(url_for('settings'))

# --- Geração de barcode e resize 50% ---
def gerar_barcode_imagem(ean: str, base_path: str) -> str:
    """
    Gera um PNG menor do EAN-13:
    - DPI moderado
    - Barras bem finas e baixas
    - Sem resize posterior
    """
    # Cria o objeto EAN13 (sem checksum extra)
    barcode = EAN13(ean, writer=ImageWriter(), no_checksum=True)

    # Parâmetros ajustados para um barcode muito menor
    opts = {
        'dpi'           : 200,   # resolução intermediária
        'module_width'  : 0.08,  # traço super fino (em mm)
        'module_height' : 8,     # altura em mm
        'quiet_zone'    : 0.5,   # margem bem pequena
        'write_text'    : False, # sem texto embutido
    }

    # .save() retorna o caminho completo com .png
    generated = barcode.save(base_path, opts)
    return generated


# --- Impressão via driver Zebra (ImageWin) ---
def print_image_via_driver(image_path: str, printer_name: str=None):
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)

    area = (
        hDC.GetDeviceCaps(win32con.HORZRES),
        hDC.GetDeviceCaps(win32con.VERTRES),
    )

    hDC.StartDoc(image_path)
    hDC.StartPage()

    img = Image.open(image_path)
    dib = ImageWin.Dib(img)
    dib.draw(hDC.GetHandleOutput(), (0, 0, area[0], area[1]))

    hDC.EndPage()
    hDC.EndDoc()

# --- Envio legado via socket (carga LS) ---
def enviar_para_impressora(zpl: str) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((IP_IMPRESSORA, PORTA_IMPRESSORA))
            s.sendall(zpl.encode('latin1'))
        return True
    except Exception as e:
        print("Erro ao enviar ZPL:", e)
        return False

# --- Rota principal ---
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        codigo = request.form.get('codigo','').strip()
        modo   = request.form.get('modo','Floricultura')
        action = request.form.get('action','print')

        if action == "load":
            # … seu código de carga via socket …
            return redirect(url_for('index'))

        if action == "print":
            if modo == "FLV":
                flash("❌ Impressão desabilitada em modo FLV", "error")
            else:
                if not (codigo.isdigit() and len(codigo) in (12,13)):
                    flash("❌ Código inválido", "error")
                else:
                    # Defina png_path antes do try
                    png_path = None
                    # Cria um arquivo temporário *sem* extensão
                    tmp = tempfile.NamedTemporaryFile(delete=False)
                    base = tmp.name
                    tmp.close()

                    try:
                        # 1) Gera o PNG e captura o nome real (com .png)
                        png_path = gerar_barcode_imagem(codigo, base)
                        # 2) Imprime via driver
                        print_image_via_driver(
                            png_path,
                            printer_name="ZDesigner ZD220-203dpi ZPL"
                        )
                        flash("✅ Impressão via driver enviada com sucesso!", "success")
                    except Exception as e:
                        flash(f"❌ Erro ao imprimir via driver: {e}", "error")
                    finally:
                        # Limpa apenas se png_path foi definido
                        if png_path and os.path.exists(png_path):
                            os.remove(png_path)

            return redirect(url_for('index'))

    return render_template("index.html")

# --- Login / Logout / Settings ---
@app.route("/login", methods=["GET","POST"])
def login():
    next_page = request.args.get('next', url_for('settings'))
    if request.method == "POST":
        if (request.form.get('username') == USUARIO and
            request.form.get('password') == SENHA):
            session.permanent     = True
            session['logged_in']  = True
            flash("✅ Login bem-sucedido!", "success")
            return redirect(next_page)
        flash("❌ Credenciais inválidas!", "error")
        return redirect(url_for('login', next=next_page))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logout realizado!", "success")
    return redirect(url_for('index'))

@app.route("/settings", methods=["GET","POST"])
def settings():
    global IP_IMPRESSORA, LS_FLOR_VALUE, LS_FLV_VALUE
    if not session.get('logged_in'):
        return redirect(url_for('login', next=url_for('settings')))

    if request.method == "POST":
        novo_ip = request.form.get('ip','').strip()
        ls_f    = request.form.get('ls_flor','')
        ls_v    = request.form.get('ls_flv','')

        if novo_ip:
            IP_IMPRESSORA = novo_ip
        try:
            LS_FLOR_VALUE = int(ls_f)
            LS_FLV_VALUE  = int(ls_v)
            save_config()
            flash("✅ Configurações salvas com sucesso!", "success")
        except ValueError:
            flash("❌ Valores inválidos para LS", "error")

        return redirect(url_for('settings'))

    return render_template(
        "settings.html",
        ip_impressora=IP_IMPRESSORA,
        ls_flor=LS_FLOR_VALUE,
        ls_flv=LS_FLV_VALUE
    )

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
