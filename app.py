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

# --- Carrega base CSV em memória ---
def load_db():
    db = {}
    if not os.path.exists(CSV_FILE):
        return db
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ean    = row['EAN-13'].strip()
            desc   = row['Descricao'].strip()
            codprod= row['Cod.Prod'].strip()
            # indexa pelos dois campos
            db[ean]     = {'ean': ean, 'descricao': desc, 'codprod': codprod}
            db[codprod] = {'ean': ean, 'descricao': desc, 'codprod': codprod}
    return db

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
    chave_base = codigo.split('-', 1)[0]
    if not chave_base.isdigit() or not (4 <= len(chave_base) <= 13):
        return False

    if len(chave_base) == 13:
        # EAN-13 precisa bater exatamente
        return chave_base in DB
    else:
        # qualquer Cod.Prod que comece pelo prefixo
        return any(
            v['codprod'].startswith(chave_base)
            for v in DB.values()
        )


def lookup_csv(codigo: str):
    # retorna (descricao, codprod, ean13)
    chave = codigo.split('-', 1)[0]
    print(chave)
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # busca exata por EAN-13
            if len(chave) == 13 and row.get('EAN-13') == chave:
                return row.get('Descricao',''), row.get('Cod.Prod',''), row.get('EAN-13','')
            # busca por código reduzido
            print("Chave 1: "+chave+" Chave 2: "+row.get)
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

# --- Compor imagem final com texto acima ---
def compose_label(barcode_path: str, descricao: str, codprod: str) -> str:
    # Carrega o código de barras
    img = Image.open(barcode_path)
    largura, altura = img.size

    # Espaço extra no topo para texto
    padding_top = 40
    nova = Image.new("RGB", (largura, altura + padding_top), "white")
    draw = ImageDraw.Draw(nova)
    font = ImageFont.truetype("arial.ttf", 14)

    # 1) Desenha a descrição no topo
    bbox = draw.textbbox((0, 0), descricao, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (largura - text_w) // 2
    y = 5
    draw.text((x, y), descricao, fill="black", font=font)

    # 2) Desenha o código do produto logo abaixo
    cod_text = f"Código: {codprod}"
    bbox2 = draw.textbbox((0, 0), cod_text, font=font)
    c_w = bbox2[2] - bbox2[0]
    c_h = bbox2[3] - bbox2[1]
    x2 = (largura - c_w) // 2
    y2 = y + text_h + 5
    draw.text((x2, y2), cod_text, fill="black", font=font)

    # 3) Cola o código de barras abaixo do texto
    nova.paste(img, (0, padding_top))

    # Salva e retorna o caminho da imagem composta
    out_path = barcode_path.replace(".png", "_label.png")
    nova.save(out_path)
    return out_path

# --- Imprime via GDI sem reset ---
def print_image_via_driver(image_path: str, x_offset: int, printer_name: str = None):
    if printer_name is None:
        printer_name = win32print.GetDefaultPrinter()
    # reaplica noreset antes
    disable_reset_and_set_ls(x_offset if x_offset >= 0 else -x_offset, printer_name)
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    # move a origem
    hDC.SetViewportOrg((x_offset, Y_OFFSET))
    img = Image.open(image_path)
    w, h = img.size
    hDC.StartDoc("Etiqueta")
    hDC.StartPage()
    dib = ImageWin.Dib(img)
    dib.draw(hDC.GetHandleOutput(), (0, 0, w, h))
    hDC.EndPage()
    hDC.EndDoc()
    # reaplica noreset depois
    disable_reset_and_set_ls(x_offset if x_offset >= 0 else -x_offset, printer_name)

DB = load_db()
Y_OFFSET = 50  # fixo vertical
# --- Rota principal ---
@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        codigo = request.form.get("codigo","").strip()
        modo   = request.form.get("modo","Floricultura")
        action = request.form.get("action","print")

        if action == "load":
            ls = LS_FLOR_VALUE if modo=="Floricultura" else LS_FLV_VALUE
            disable_reset_and_set_ls(ls)
            flash(f"✅ Carga '{modo}' (LS={ls}) enviada!","success")
            return redirect(url_for("index"))

        if action == "print":
            if modo=="FLV":
                flash("❌ Impressão desabilitada em modo FLV","error")
            else:
                if not validou_codigo(codigo):
                    flash("❌ Produto não encontrado","error")
                else:
                    chave_base = codigo.split('-', 1)[0]
                    # lookup com startswith
                    if len(chave_base) == 13:
                        rec = DB.get(chave_base)
                    else:
                        rec = next(
                            (v for v in DB.values() if v['codprod'].startswith(chave_base)),
                            None
                        )

                    if not rec:
                        flash("❌ Produto não encontrado","error")
                    else:
                        raw = gerar_barcode_bwip(rec['ean'])
                        comp = compose_label(raw, rec['descricao'], rec['codprod'])
                        xoff = abs(LS_FLOR_VALUE)
                        try:
                            print_image_via_driver(comp, xoff)
                            flash("✅ Impressão enviada com sucesso!","success")
                        except Exception as e:
                            flash(f"❌ Erro ao imprimir: {e}","error")
                        finally:
                            for path in (raw, comp):
                                if path and os.path.exists(path):
                                    os.remove(path)
            return redirect(url_for("index"))

    return render_template("index.html")

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
