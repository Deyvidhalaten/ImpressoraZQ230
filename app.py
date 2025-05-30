import ssl
ssl._create_default_https_context = ssl._create_unverified_context
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

windows_font = os.path.join(os.environ['WINDIR'], 'Fonts', 'arial.ttf')
# e quando for instanciar:
font = ImageFont.truetype(windows_font, size=14)

# --- CONFIGURAÇÃO DE PERSISTÊNCIA ---
BASE_DIR     = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
CONFIG_FILE  = os.path.join(BASE_DIR, 'config.txt')
CSV_FILE     = os.path.join(BASE_DIR, 'baseFloricultura.csv')
PRINTERS_CSV = os.path.join(BASE_DIR, 'printers.csv')

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

def load_printer_map():
    maps = []
    if not os.path.exists(PRINTERS_CSV):
        return maps
    with open(PRINTERS_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            maps.append({
                'loja':    row['loja'],
                'pattern': row['pattern'],
                'driver':  row['driver'],
                'funcao':  row.get('funcao',''),
                'ip':      row.get('ip',''),
                'ls_flor': int(row.get('ls_flor', 0)),
                'ls_flv':  int(row.get('ls_flv', 0)),
            })
    return maps


load_printer_map()

def get_loja_map():
    client_ip = request.remote_addr
    for m in load_printer_map():
        if client_ip.startswith(m['pattern'].rstrip('*')):
            return m
    return None

def get_mapping_for_ip(client_ip, mappings):
    """Retorna o mapeamento cuja pattern case com o client_ip."""
    for m in mappings:
        prefix = m['pattern'].rstrip('*')
        if client_ip.startswith(prefix):
            return m
    return None

def enviar_para_impressora_ip(zpl: str, ip: str, porta: int = PORTA_IMPRESSORA) -> bool:
    """Envia diretamente via socket ZPL ao IP/porta informados."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, porta))
            s.sendall(zpl.encode('latin1'))
        return True
    except Exception as e:
        print("Erro ao enviar ZPL por IP:", e)
        return False
    
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

def resolve_printer_name(requested_name: str) -> str:
    """
    Varre as impressoras locais/conectadas e retorna o nome
    completo da primeira que contenha requested_name (case-insensitive).
    """
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    for _, _, name, _ in win32print.EnumPrinters(flags):
        if requested_name.lower() in name.lower():
            return name
    raise RuntimeError(f"Impressora não encontrada: '{requested_name}'")

# --- Impressão via driver Zebra usando ImageWin ---
Y_OFFSET = 50
PRINTER_NAME = "ZDesigner ZD230-203dpi ZPL"

def print_image_via_driver(image_path: str, x_offset: int, printer_name: str):
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
    #    e manter o LS (em dots) 
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

def get_driver_for_ip(client_ip: str, mappings: list[dict]) -> str:
    """
    percorre mappings (vindo de load_printer_map())
    e retorna o primeiro 'driver' cujo 'pattern' case com client_ip.
    Ex: pattern="10.17*" casa com client_ip="10.17.30.5".
    """
    for m in mappings:
        prefix = m['pattern'].rstrip('*')
        if client_ip.startswith(prefix):
            return m['driver']
    # fallback para a impressora padrão
    return win32print.GetDefaultPrinter()

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

def compose_double_label(label_path: str, gap: int = 140) -> str:
    img = Image.open(label_path)
    w, h = img.size

    # canvas com largura = 2×w + gap
    canvas = Image.new("RGB", (2*w + gap, h), "white")
    # primeira etiqueta colada à esquerda
    canvas.paste(img, (0, 0))
    # segunda etiqueta colada após w + gap pixels
    canvas.paste(img, (w + gap, 0))

    out_path = label_path.replace("_label.png", f"_double_{gap}px_gap.png")
    canvas.save(out_path)
    return out_path

DB = load_db()
Y_OFFSET = 50  # fixo vertical

# --- Rota principal ---
@app.route("/", methods=["GET","POST"])
def index():
    # Carrega todos os mapeamentos do CSV
    mappings = load_printer_map()
    client_ip = request.remote_addr
    # Encontra o mapeamento que casa com o IP do cliente
    mapping = get_mapping_for_ip(client_ip, mappings) or {}

    # Se não achar, cai em defaults
    driver_for_request = mapping.get('driver') or win32print.GetDefaultPrinter()
    printer_ip         = mapping.get('printer_ip') or IP_IMPRESSORA
    ls_flor_mapped     = mapping.get('ls_flor', LS_FLOR_VALUE)
    ls_flv_mapped      = mapping.get('ls_flv',  LS_FLV_VALUE)

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        modo   = request.form.get("modo",   "Floricultura")
        action = request.form.get("action", "print")
        
        # --- Ação de "Enviar Carga" (LS ZPL) ---
        if action == "load":
            loja_map = get_loja_map()
            if loja_map is None:
                flash("❌ Sua loja não está cadastrada. Acesse “Impressoras” para adicioná-la.", "error")
                return redirect(url_for("index"))
            
            ls = ls_flor_mapped if modo == "Floricultura" else ls_flv_mapped
            zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            ok  = enviar_para_impressora_ip(zpl, printer_ip)
            if ok:
                flash(f"✅ Carga '{modo}' (LS={ls}) enviada para {printer_ip}!", "success")
            else:
                flash(f"❌ Falha ao enviar carga para {printer_ip}", "error")
            return redirect(url_for("index"))

        # --- Ação de "Imprimir" via driver Windows/GDI ---
        if action == "print":
            if loja_map is None:
              flash("❌ Sua loja não está cadastrada. Acesse “Impressoras” para adicioná-la.", "error")
              return redirect(url_for("index"))
            # lê e valida número de cópias
            try:
                copies = int(request.form.get("copies", "1"))
            except ValueError:
                copies = 1
            copies = max(1, min(copies, 100))

            if modo == "FLV":
                flash("❌ Impressão desabilitada em modo FLV", "error")
                return redirect(url_for("index"))

            if not validou_codigo(codigo):
                flash("❌ Produto não encontrado", "error")
                return redirect(url_for("index"))

            # busca no DB
            chave_base = codigo.split("-", 1)[0]
            if len(chave_base) == 13:
                rec = DB.get(chave_base)
            else:
                rec = next(
                    (v for v in DB.values() if v['codprod'].startswith(chave_base)),
                    None
                )
            if not rec:
                flash("❌ Produto não encontrado", "error")
                return redirect(url_for("index"))

            # gera imagens
            raw    = gerar_barcode_bwip(rec['ean'])
            single = compose_label(raw, rec['descricao'], rec['codprod'])
            double = compose_double_label(single)

            # escolhe LS para deslocamento
            ls = ls_flor_mapped if modo == "Floricultura" else ls_flv_mapped
            xoff = abs(ls)

            try:
                # reaplica LS no driver antes de imprimir
                disable_reset_and_set_ls(ls_value=ls, printer_name=driver_for_request)

                # imprime as cópias
                for _ in range(copies):
                    print_image_via_driver(double, xoff, printer_name=driver_for_request)

                flash(f"✅ {copies} cópia(s) impressa(s) via driver '{driver_for_request}'", "success")
            except Exception as e:
                flash(f"❌ Erro ao imprimir: {e}", "error")
            finally:
                # limpa arquivos temporários
                for path in (raw, single, double):
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

@app.route("/printers", methods=["GET","POST"])
def printers():
    mappings = load_printer_map()
    mappings.sort(key=lambda m: int(m['loja'] or 0))

    if request.method == "POST":
        # DELETE
        if request.form.get("action") == "delete":
            pattern = request.form["pattern"]
            mappings = [m for m in mappings if m["pattern"] != pattern]
            save_printer_map(mappings)
            flash("🗑️ Mapeamento excluído!", "success")
            return redirect(url_for("printers"))

        # ADD / EDIT
        loja   = request.form['loja'].strip()
        driver = request.form['driver'].strip()
        funcao = request.form.get('funcao','').strip()
        ip     = request.form['ip'].strip()
        ls_f   = int(request.form.get('ls_flor', 0))
        ls_v   = int(request.form.get('ls_flv', 0))

        pattern = f"10.{int(loja)}*"
        updated = False
        for m in mappings:
            if m['pattern'] == pattern:
                m.update(driver=driver, funcao=funcao, ip=ip, ls_flor=ls_f, ls_flv=ls_v)
                updated = True
                break
        if not updated:
            mappings.append({
                'loja':    loja,
                'pattern': pattern,
                'driver':  driver,
                'funcao':  funcao,
                'ip':      ip,
                'ls_flor': ls_f,
                'ls_flv':  ls_v,
            })

        save_printer_map(mappings)
        flash("✅ Mapeamento salvo!", "success")
        return redirect(url_for("printers"))

    return render_template("printers.html", mappings=mappings)

def save_printer_map(mappings):
    fieldnames = ['loja','pattern','driver','funcao','ip','ls_flor','ls_flv']
    with open(PRINTERS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in mappings:
            writer.writerow({
                'loja':    m['loja'],
                'pattern': m['pattern'],
                'driver':  m['driver'],
                'funcao':  m.get('funcao',''),
                'ip':      m.get('ip',''),
                'ls_flor': m.get('ls_flor',0),
                'ls_flv':  m.get('ls_flv',0),
            })

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logout realizado!", "success")
    return redirect(url_for('index'))

@app.route("/settings", methods=["GET","POST"])
def settings():
    global LS_FLOR_VALUE, LS_FLV_VALUE

    if request.method == "POST":
        # pega os novos valores de LS direto do form
        ls_f = request.form.get('ls_flor','').strip()
        ls_v = request.form.get('ls_flv','').strip()

        try:
            LS_FLOR_VALUE = int(ls_f)
            LS_FLV_VALUE  = int(ls_v)
            save_printer_map(load_printer_map())  # ou save_config() se mantiver config.txt
            flash("✅ LS atualizados com sucesso!", "success")
        except ValueError:
            flash("❌ Valores inválidos para LS", "error")
        return redirect(url_for('settings'))

    # Renderiza o form mostrando os LS que estão no CSV
    return render_template(
        "settings.html",
        ls_flor=LS_FLOR_VALUE,
        ls_flv=LS_FLV_VALUE
    )

if __name__ == "__main__":
    # host='0.0.0.0' faz o Flask aceitar conexões de qualquer IP da sua LAN
    app.run(host="10.4.30.2", port=8000, debug=False, use_reloader=False)
