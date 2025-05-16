import sys
import os
import socket
import tempfile
import urllib3
import requests

import win32print  # type: ignore
import win32ui     # type: ignore

from datetime import timedelta
from PIL import Image, ImageWin
from flask import (
    Flask, render_template, request, redirect,
    flash, session, url_for
)

# --- CONFIGURAÇÃO DE PERSISTÊNCIA ---
BASE_DIR     = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
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
            if '=' not in line: continue
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

# Desativa warnings de SSL caso use bwip-js em algum ponto
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Shutdown server ---
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
    flash("❌ Senha inválida para encerramento", "error")
    return redirect(url_for('settings'))

# --- Geração via Google Charts ---
'''def gerar_barcode_google(ean: str) -> str:
    """
    Baixa o PNG do Google Charts para EAN-13 e retorna o caminho local.
    """
    url = (
        "https://chart.googleapis.com/chart"
        f"?cht=ean13&chs=200x100&chld=M|0|0|0&chl={ean}"
    )
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    resp = requests.get(url)
    resp.raise_for_status()
    with open(tmp.name, "wb") as f:
        f.write(resp.content)
    return tmp.name'''

# --- Impressão via driver Zebra usando ImageWin ---
Y_OFFSET = 100  # ajuste esse valor conforme necessário

def print_image_via_driver(image_path: str, printer_name: str=None):
    """
    Imprime um PNG via driver Zebra, desenhando no tamanho real da imagem
    mas deslocado Y_OFFSET pixels para baixo.
    """
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()
    print(f"[DEBUG] Enviando para impressora: '{printer_name}'")

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)

    img = Image.open(image_path)
    w, h = img.size
    print(f"[DEBUG] Imagem tamanho: {w}×{h}, Y_OFFSET={Y_OFFSET}")

    if w <= 0 or h <= 0:
        raise RuntimeError(f"Imagem inválida: largura={w}, altura={h}")

    hDC.StartDoc("Impressão de Código de Barras")
    hDC.StartPage()

    # desenha no canto (0, Y_OFFSET), mantendo w×h pixels
    dib = ImageWin.Dib(img)
    dib.draw(
        hDC.GetHandleOutput(),
        (0, Y_OFFSET, w, Y_OFFSET + h)
    )

    hDC.EndPage()
    hDC.EndDoc()

# --- Envio legado de ZPL para carga de LS via socket ---
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
            ls  = LS_FLOR_VALUE if modo == "Floricultura" else LS_FLV_VALUE
            zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            ok  = enviar_para_impressora(zpl)
            flash(
                f"✅ Carga '{modo}' (LS={ls}) enviada!" if ok
                else f"❌ Falha ao enviar carga '{modo}'",
                "success" if ok else "error"
            )
            return redirect(url_for('index'))

        if action == "print":
            if modo == "FLV":
                flash("❌ Impressão desabilitada em modo FLV", "error")
            else:
                if not (codigo.isdigit() and len(codigo) in (12,13)):
                    flash("❌ Código inválido", "error")
                else:
                    png_path = None
                    try:
                        png_path = gerar_barcode_bwip(codigo)
                        print_image_via_driver(png_path,
                            printer_name="ZDesigner ZD230-203dpi ZPL")
                        flash("✅ Impressão enviada com sucesso!", "success")
                    except Exception as e:
                        flash(f"❌ Erro ao imprimir via driver: {e}", "error")
                    finally:
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
            session.permanent    = True
            session['logged_in']= True
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

def gerar_barcode_bwip(ean: str) -> str:
    """
    Baixa do BWIP-JS um PNG EAN-13 e retorna o caminho local do arquivo.
    """
    # montamos a URL com scale menor para não ficar gigante
    url = (
        "https://bwipjs-api.metafloor.com/"
        f"?bcid=ean13&text={ean}"
        "&scale=2"            # módulo pequeno
        "&height=15"          # altura em mm
        "&includetext=true"   # texto abaixo do código
        "&backgroundcolor=FFFFFF"
    )

    # cria um temp file .png
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()

    # desabilita verificação SSL (caso seja necessário na sua rede)
    resp = requests.get(url, verify=False)  
    resp.raise_for_status()

    with open(tmp.name, "wb") as f:
        f.write(resp.content)

    return tmp.name

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
