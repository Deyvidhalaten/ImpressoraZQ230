import sys
import os
import socket
import tempfile
import urllib3
import requests
import csv

import win32print  # type: ignore
import win32ui     # type: ignore

from datetime import timedelta
from PIL import Image, ImageWin, ImageDraw, ImageFont
from flask import (
    Flask, render_template, request, redirect,
    flash, session, url_for
)

# --- CONFIGURAÇÃO DE PERSISTÊNCIA ---
BASE_DIR     = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
CONFIG_FILE  = os.path.join(BASE_DIR, 'config.txt')
CSV_FILE     = os.path.join(BASE_DIR, 'baseFloricultura.csv')

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

# Desativa warnings de SSL
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

# --- Validadores e lookup CSV ---
def validou_codigo(codigo: str) -> bool:
    if not codigo.isdigit():
        return False
    if len(codigo) < 4 or len(codigo) > 13:
        return False
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(codigo) == 13 and row.get('EAN-13') == codigo:
                return True
            if len(codigo) < 13 and row.get('Cod.Prod') == codigo:
                return True
    return False


def lookup_csv(chave: str):
    # retorna (descricao, codprod, ean13)
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(chave) == 13 and row.get('EAN-13') == chave:
                return row.get('Descricao',''), row.get('Cod.Prod',''), row.get('EAN-13','')
            if len(chave) < 13 and row.get('Cod.Prod') == chave:
                return row.get('Descricao',''), row.get('Cod.Prod',''), row.get('EAN-13','')
    return '', '', ''

def gerar_barcode_bwip(ean: str) -> str:
    url = (
        "https://bwipjs-api.metafloor.com/"
        f"?bcid=ean13&text={ean}"
        "&scale=2&height=15&includetext=true&backgroundcolor=FFFFFF"
    )
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    resp = requests.get(url, verify=False)
    resp.raise_for_status()
    with open(tmp.name, "wb") as f:
        f.write(resp.content)
    return tmp.name

# --- Montagem de etiqueta com texto ---
def compose_label(ean: str, descricao: str, codprod: str) -> str:
    # gera o PNG do barcode
    barcode_png = gerar_barcode_bwip(ean)

    # abre o PNG e cria uma nova imagem um pouco maior para o texto em cima
    barcode = Image.open(barcode_png)
    w, h = barcode.size
    top_margin = 40  # altura reservada para nome+subcódigo
    label = Image.new("RGB", (w, h + top_margin), "white")
    label.paste(barcode, (0, top_margin))

    draw = ImageDraw.Draw(label)
    font = ImageFont.truetype("arial.ttf", size=14)  # ou outro .ttf disponível

    # mede o tamanho do texto da descrição
    box = draw.textbbox((0, 0), descricao, font=font)  
    text_w = box[2] - box[0]
    text_h = box[3] - box[1]
    # centraliza horizontalmente
    x_desc = (w - text_w) // 2
    y_desc = 5
    draw.text((x_desc, y_desc), descricao, font=font, fill="black")

    # faz o mesmo para o código de produto, logo abaixo da descrição
    box2 = draw.textbbox((0, 0), codprod, font=font)
    cp_w = box2[2] - box2[0]
    x_cp = (w - cp_w) // 2
    y_cp = y_desc + text_h + 2
    draw.text((x_cp, y_cp), codprod, font=font, fill="black")

    # salva e retorna caminho
    out = barcode_png.replace(".png", "_label.png")
    label.save(out)
    return out

# --- Impressão via driver Zebra usando ImageWin ---
Y_OFFSET = 50

def print_image_via_driver(image_path: str, x_offset: int, printer_name: str=None):
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()
    # abre DC
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    # move origem
    hDC.SetViewportOrg((x_offset, Y_OFFSET))
    # carrega e imprime
    img = Image.open(image_path)
    w, h = img.size
    hDC.StartDoc("Etiqueta")
    hDC.StartPage()
    dib = ImageWin.Dib(img)
    dib.draw(hDC.GetHandleOutput(), (0,0, w, h))
    hDC.EndPage()
    hDC.EndDoc()

# --- Envio legado ZPL ---
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
    if request.method == 'POST':
        codigo = request.form.get('codigo','').strip()
        modo   = request.form.get('modo','Floricultura')
        action = request.form.get('action','print')

        if action == 'load':
            ls = LS_FLOR_VALUE if modo=='Floricultura' else LS_FLV_VALUE
            zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            ok = enviar_para_impressora(zpl)
            flash(f"✅ Carga '{modo}' (LS={ls}) enviada!", 'success')
            return redirect(url_for('index'))

        if action == 'print':
            if not validou_codigo(codigo):
                flash("❌ Código não encontrado na base.", 'error')
                return redirect(url_for('index'))
            desc, codp, ean = lookup_csv(codigo)
            png_path = compose_label(ean, desc, codp)
            x_off = abs(LS_FLOR_VALUE) if modo=='Floricultura' else abs(LS_FLV_VALUE)
            try:
                print_image_via_driver(png_path, x_off)
                flash("✅ Impressão enviada com sucesso!", 'success')
            except Exception as e:
                flash(f"❌ Erro ao imprimir via driver: {e}", 'error')
            finally:
                if os.path.exists(png_path): os.remove(png_path)
            return redirect(url_for('index'))

    return render_template('index.html')

# --- Login / Logout / Settings ---
@app.route("/login", methods=["GET","POST"])
def login():
    next_page = request.args.get('next', url_for('settings'))
    if request.method == "POST":
        if request.form.get('username') == USUARIO and request.form.get('password') == SENHA:
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
        ip = request.form.get('ip','').strip()
        ls_f = request.form.get('ls_flor','')
        ls_v = request.form.get('ls_flv','')
        if ip: IP_IMPRESSORA = ip
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
