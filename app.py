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
PRINTER_NAME = "ZDesigner ZD230-203dpi ZPL"

def print_image_via_driver(image_path: str, x_offset: int, printer_name: str = None):
    """
    1) Desabilita o reset do driver e reaplica o LS via ZPL (preserva margem)
    2) Imprime o PNG via GDI já deslocado (x_offset, Y_OFFSET)
    """
    # 1) escolhe a impressora
    if printer_name is None:
        # usa padrão do Windows, ou nosso nome fixo
        printer_name = win32print.GetDefaultPrinter() or "ZDesigner ZD230-203dpi ZPL"
    print(f"[DEBUG] Usando impressora: '{printer_name}'")
    
    # 2) antes de desenhar via GDI, manda PJL+ZPL pra desabilitar o reset
    #    e manter o LS (em dots) conforme a configuração atual
    ls = x_offset  # já veio como abs(LS_FLOR_VALUE) ou abs(LS_FLV_VALUE)
    disable_reset_and_set_ls(ls_value=ls, printer_name=printer_name)

    # 3) abre o contexto de impressão GDI
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)

    # 4) move o ponto de origem para aplicar os offsets
    hDC.SetViewportOrg((x_offset, Y_OFFSET))

    # 5) carrega e imprime a imagem
    img = Image.open(image_path)
    w, h = img.size

    hDC.StartDoc("Etiqueta")
    hDC.StartPage()
    dib = ImageWin.Dib(img)
    dib.draw(hDC.GetHandleOutput(), (0, 0, w, h))
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

def print_raw_zpl(zpl_bytes: bytes, printer_name: str = None):
    """
    Envia bytes RAW (PJL+ZPL) diretamente para a fila, sem passar
    pelo GDI, portanto o driver não injeta nenhum reset.
    """
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()
    h = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(h, 1, ("RAW_ZPL", None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, zpl_bytes)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)

def load_ls(modo: str):
    """
    Reenvia a carga de LS (margem esquerda) exata que o botão 'Enviar Carga' usa,
    garantindo que a impressora volte ao LS configurado antes de cada impressão.
    """
    ls = LS_FLOR_VALUE if modo == 'Floricultura' else LS_FLV_VALUE
    zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
    ok = enviar_para_impressora(zpl)
    if not ok:
        flash(f"❌ Falha ao recarregar LS antes da impressão (LS={ls})", "error")
    else:
        flash(f"🔄 LS recarregado (LS={ls}) antes da impressão", "info")

def disable_reset_and_set_ls(ls_value: int, printer_name: str = None):
    """
    1) Envia um bloco PJL que desliga o reset automático do driver (SET RESET=OFF)
    2) Em seguida envia um bloco ZPL para aplicar ^MD30 e o ^LS desejado
    Tudo em um único job RAW, de forma que o driver preserve o LS.
    """
    # PJL para desabilitar reset automático
    pjl = b'\x1b%-12345X@PJL SET RESET=OFF\r\n\x1b%-12345X\r\n'
    # ZPL para atualizar a margem esquerda (LS) permanentemente
    zpl = f"^XA^MD30^LS{ls_value}^XZ\r\n".encode("ascii")
    # Junta PJL + ZPL e envia
    print_raw_zpl(pjl + zpl, printer_name)

# --- Rota principal ---
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == 'POST':
        codigo = request.form.get('codigo','').strip()
        modo   = request.form.get('modo','Floricultura')
        action = request.form.get('action','print')

        if action == 'load':
            # seu código existente para o botão "Enviar Carga"
            ls = LS_FLOR_VALUE if modo=='Floricultura' else LS_FLV_VALUE
            zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            ok = enviar_para_impressora(zpl)
            flash(f"✅ Carga '{modo}' (LS={ls}) enviada!", 'success' if ok else 'error')
            return redirect(url_for('index'))

        if action == 'print':
            if not validou_codigo(codigo):
                flash("❌ Código não encontrado na base.", 'error')
                return redirect(url_for('index'))

            # busca e compõe
            desc, codp, ean = lookup_csv(codigo)
            png_path = compose_label(ean, desc, codp)
            x_off = abs(LS_FLOR_VALUE) if modo=='Floricultura' else abs(LS_FLV_VALUE)

            try:
                # 1) recarrega o LS
                load_ls(modo)

                # 2) agora imprime via driver
                print_image_via_driver(png_path, x_off, printer_name=None)
                flash("✅ Impressão enviada com sucesso!", 'success')

            except Exception as e:
                flash(f"❌ Erro ao imprimir: {e}", 'error')

            finally:
                if png_path and os.path.exists(png_path):
                    os.remove(png_path)

            return redirect(url_for('index'))

    return render_template('index.html')

def send_ls_config(modo: str):
    """Envia o ^LS configurado na impressora para preservar a margem."""
    ls = LS_FLOR_VALUE if modo == 'Floricultura' else LS_FLV_VALUE
    disable_reset_and_set_ls(ls, printer_name=PRINTER_NAME)
    flash(f"🔄 Margem (LS={ls}) reenviada antes da impressão", "info")

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
        novo_ip = request.form.get('ip','').strip()
        ls_f    = request.form.get('ls_flor','')
        ls_v    = request.form.get('ls_flv','')

        # Atualiza variáveis globais
        if novo_ip:
            IP_IMPRESSORA = novo_ip
        try:
            LS_FLOR_VALUE = int(ls_f)
            LS_FLV_VALUE  = int(ls_v)
        except ValueError:
            flash("❌ Valores inválidos para LS", "error")
            return redirect(url_for('settings'))

        # Salva no disco e recarrega em memória
        try:
            save_config()
            load_config()
            flash("✅ Configurações salvas com sucesso!", "success")
        except Exception as e:
            flash(f"❌ Falha ao salvar configurações: {e}", "error")

        return redirect(url_for('settings'))

    return render_template(
        "settings.html",
        ip_impressora=IP_IMPRESSORA,
        ls_flor=LS_FLOR_VALUE,
        ls_flv=LS_FLV_VALUE
    )

if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
