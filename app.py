import fnmatch
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
import sys
import os
import socket
import urllib3
import csv

from PIL import Image


from printer_zq230 import ZQ230Printer  #  Módulo de socket/ZPL
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
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
LOG_FILE = os.path.join(BASE_DIR, "logs.csv")

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

# --- Carrega base CSV Flor em memória ---
def load_db_Flor():
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

# --- Carrega base CSV FLV em memória ---
def load_db_FLV():
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
            raw   = row.get('funcao', '').strip()
            funcs = [x.strip() for x in raw.split(';') if x.strip()]

            maps.append({
                'loja':    row['loja'],
                'pattern': row['pattern'],
                'nome':    row.get('nome','').strip(),
                'ip':      row.get('ip',''),
                'funcao':  funcs,
                'ls_flor': int(row.get('ls_flor', 0)),
                'ls_flv':  int(row.get('ls_flv', 0)),
            })
    return maps

#acrescenta uma linha com data/hora, tipo de evento, IP, impressora (se houver) e detalhes.
def append_log(evento: str, ip: str = "", impressora: str = "", detalhes: str = ""):
    """
    Acrescenta uma linha em logs.csv com as colunas:
    timestamp,evento,ip,impressora,detalhes
    """
    # Garante que o arquivo exista; se não existir, cria e adiciona cabeçalho
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "evento", "ip", "impressora", "detalhes"])
    # Grava a nova linha
    ts = datetime.now().isoformat(sep=" ", timespec="seconds")
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, evento, ip, impressora, detalhes])
        
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

# --- Impressão via driver Zebra usando ImageWin ---

DB = load_db_Flor()
Y_OFFSET = 50  # fixo vertical

def gerar_zpl_templateFlor(texto: str, codprod: str, ean: str, copies:int , ls:int) -> str:
    
    return f"""
^XA 
^PRD^FS 
^LS{ls}^FS
^PW663^FS
^LT0
^LL250^FS 
^JMA^FS 
^BY2 
^FO100,020^A0N,40,20^FD{texto} ^FS 
^FO100,75^A0N,25,20^FD{codprod}^FS 
^FO100,105^BEN,50,Y,N^FD{ean}^FS 
^FO455,015^A0N,40,20^FD{texto}^FS 
^FO455,75^A0N,25,20^FD{codprod}^FS 
^FO450,105^BEN,50,Y,N^FD{ean}^FS 
^PQ{copies},0,1,N^FS 
^XZ
 """

def gerar_zpl_templateFLV(texto: str, infnutri: str, codprod: str, ean: str, validade:int, data:str, copies:int , ls:int) -> str:
        return f"""
^XA
^PRD^FS
^LS{ls}^FS
^LH0,0^FS
^LL100^FS
^JMA^FS
^BY2
^FO90,50^A0N,50,20^FD{texto} ^FS
^FO90,115^A0N,15,20^FD{infnutri} ^FS
^FO130,420^A0N,25,20^FD{codprod}-3^FS
^FO120,440^BEN,50,Y,N^FD{ean}^FS 
^FO90,540^A0N,40,30^FDValidade: {validade} Dias^FS
^FO90,605^A0N,40,30^FDProduzido: {data}^FS
^PQ{copies},0,1,N
^XZ
 """


@app.route("/", methods=["GET", "POST"])
def index():
    mappings  = load_printer_map()
    client_ip = request.remote_addr

    # 1) Encontra o mapeamento da loja
    loja_map = next((m for m in mappings if fnmatch.fnmatch(client_ip, m['pattern'])), None)
    if not loja_map:
        flash("❌ Loja não cadastrada — contate o administrador.", "error")
        return render_template("index.html", printers=[])

    # 2) Determina o modo e lista as impressoras habilitadas
    modo     = request.form.get("modo", "Floricultura") 
    if modo == "Floricultura":
        tipoZPL_FLV_FLOR = 1
    else:
        tipoZPL_FLV_FLOR = 0

    printers = [
       m for m in mappings
       if m['loja'] == loja_map['loja']
    ]

    # 3) Processa POST
    if request.method == "POST":
        action     = request.form.get("action", "print")
        sel_ip     = request.form.get("printer_ip")
        printer_ip = sel_ip or loja_map.get('ip')

        # --- Carga de LS via ZPL ---
        if action == "load":
            ls  = loja_map['ls_flor'] if modo == "Floricultura" else loja_map['ls_flv']
            zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            sucesso = enviar_para_impressora_ip(zpl, printer_ip)
            flash(
                f"{'✅' if sucesso else '❌'} Carga '{modo}' (LS={ls}) {'enviada' if sucesso else 'falhou'} em {printer_ip}",
                "success" if sucesso else "error"
            )
            return render_template("index.html", printers=printers)

        # --- Impressão via ZPL ---
        if action == "print":
            # valida número de cópias
            try:
                copies = max(1, min(int(request.form.get("copies", "1")), 100))
            except ValueError:
                copies = 1

            codigo = request.form.get("codigo", "").strip()
            if not validou_codigo(codigo):
                flash("❌ Código inválido ou não encontrado", "error")
                return render_template("index.html", printers=printers)

            chave = codigo.split("-", 1)[0]
            rec = (
                DB.get(chave)
                if len(chave) == 13
                else next((v for v in DB.values() if v['codprod'].startswith(chave)), None)
            )
            if not rec:
                flash("❌ Produto não encontrado", "error")
                return render_template("index.html", printers=printers)
            
            if modo not in loja_map['funcao']:
                flash(f"❌ Impressora selecionada não suporta o modo {modo}", "error")
                return render_template("index.html", printers=printers)
            
            if tipoZPL_FLV_FLOR == 1:
                ls = loja_map['ls_flor'] if modo == "Floricultura" else loja_map['ls_flv']
                zpl = gerar_zpl_templateFlor(
                    texto   = rec['descricao'],
                    codprod = rec['codprod'],
                    ean     = rec['ean'],
                    copies  = copies,
                    ls      = loja_map['ls_flor'] if modo=="Floricultura" else loja_map['ls_flv'])
            else:
                ls = loja_map['ls_flv'] if modo == "FLV" else loja_map['ls_flor']
                zpl = gerar_zpl_templateFLV(
                    infnutri   = rec['infnutri'],
                    codprod = rec['codprod'],
                    ean     = rec['ean'],
                    validade     = rec['Validade'],
                    data = datetime.now().isoformat(sep=" ", timespec="day"),
                    copies  = copies,
                    ls = loja_map['ls_flv'] if modo=="FLV" else loja_map['ls_flor'])

            try:
                sucesso = enviar_para_impressora_ip(zpl, printer_ip)
                if sucesso:
                    append_log(
                        evento="print",
                        ip=client_ip,
                        impressora=printer_ip,
                        detalhes=f"ean={rec['ean']}, codprod={rec['codprod']}, copies={copies}, modo={modo}"
                    )
                    flash(f"✅ {copies} etiqueta(s) enviada(s) para {printer_ip}", "success")
                else:
                    flash(f"❌ Falha de comunicação com {printer_ip}", "error")
            except Exception as e:
                append_log(
                    evento="print_error",
                    ip=client_ip,
                    impressora=printer_ip,
                    detalhes=f"erro={e}"
                )
                flash(f"❌ Erro ao imprimir em {printer_ip}: {e}", "error")

            return render_template("index.html", printers=printers)

    # 4) GET ou sem ação: exibe formulário
    return render_template("index.html", printers=printers)

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
    # Ordena por loja crescente
    mappings.sort(key=lambda m: int(m['loja'] or 0))

    if request.method == "POST":
        action_type = request.form.get("action", "save")  # “save” por padrão ou “delete”
        
        if action_type == "delete":
            pattern_to_delete = request.form.get("pattern")
            ip_to_delete      = request.form.get("ip")
            # busca o mapeamento exato antes de remover, para log
            m_antigo = next(
              (m for m in mappings
              if m["pattern"] == pattern_to_delete
              and m["ip"]      == ip_to_delete),
              None
            )
            if m_antigo:
                # remove somente essa entrada (mesmo padrão + mesmo IP)
                mappings = [
                     m for m in mappings
                     if not (m["pattern"] == pattern_to_delete and m["ip"] == ip_to_delete) 
                ]
                save_printer_map(mappings)
                append_log(
                    evento="mapping_delete",
                    ip=request.remote_addr,
                    impressora=m_antigo.get("nome", m_antigo.get("ip","")),
                    detalhes=f"loja={m_antigo['loja']}, ip={ip_to_delete}"
                )
                flash(f"🗑️ Impressora {ip_to_delete} excluída com sucesso!", "success")
            else:
                flash("❌ Impressora não encontrada para exclusão.", "error")
            return redirect(url_for("printers"))

        # —— Adicionar ou editar mapeamento ——
        loja   = request.form.get('loja','').strip()
        funcao_list = request.form.getlist("funcao")
        nome = request.form.get('nome','').strip()
        ip = request.form.get('ip','').strip()
        ls_flor = request.form.get('ls_flor','').strip()
        ls_flv  = request.form.get('ls_flv','').strip()

        # Validação mínima
        if not loja.isdigit() :
            flash("❌ Loja e driver são obrigatórios", "error")
            return redirect(url_for('printers'))
        # Validações
        if not loja.isdigit() or not funcao_list:
            flash("❌ Loja e pelo menos uma Função são obrigatórios", "error")
            return redirect(url_for('printers'))
        try:
            ls_flor_val = int(ls_flor)
            ls_flv_val  = int(ls_flv)
            ip_str = str(ip)
        except ValueError:
            flash("❌ Valores de LS inválidos", "error")
            return redirect(url_for('printers'))

        pattern = f"10.{int(loja)}.*"  # armazenamos “10.<loja>.*” para coincidir com qualquer “10.X.”
        updated = False

        for m in mappings:
            if m['loja'] == loja and m['ip'] == ip_str:
                # antes de alterar, guardo estado antigo
                m_antigo = m.copy()
                m['nome'] = nome
                m['funcao']  = funcao_list
                m['ip'] = ip_str
                m['ls_flor'] = ls_flor_val
                m['ls_flv']  = ls_flv_val
                updated = True
                # grava log de edição
                append_log(
                    evento="mapping_update",
                    ip=request.remote_addr,
                    detalhes=(
                        f"loja={loja}, "
                        f"old_ls_flor={m_antigo['ls_flor']}, new_ls_flor={ls_flor_val}, "
                        f"old_ls_flv={m_antigo['ls_flv']}, new_ls_flv={ls_flv_val}"
                    )
                )
                break

        if not updated:
            novo = {
                'loja':    loja,
                'pattern': pattern,
                'nome':    nome,
                'ip':      ip_str,
                'funcao':  funcao_list,
                'ls_flor': ls_flor_val,
                'ls_flv':  ls_flv_val
            }
            mappings.append(novo)
        append_log(
           evento="mapping_add",
           ip=request.remote_addr,
           detalhes=(
              f"loja={loja}, "
              f"ls_flor={ls_flor_val}, ls_flv={ls_flv_val}"
        ))

        save_printer_map(mappings)
        flash("✅ Mapeamento salvo com sucesso!", "success")
        return redirect(url_for('printers'))

    # GET: renderiza a página normalmente
    return render_template("printers.html", mappings=mappings)


def save_printer_map(mappings):
    fieldnames = ['loja','pattern','nome','funcao','ip','ls_flor','ls_flv']
    with open(PRINTERS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in mappings:
            funcs = m.get('funcao') or []
            writer.writerow({
                'loja':    m.get('loja',''),
                'pattern': m.get('pattern',''),
                'nome':    m.get('nome',''),
                'funcao':  ';'.join(funcs),
                'ip':      m.get('ip',''),
                'ls_flor': m.get('ls_flor',0),
                'ls_flv':  m.get('ls_flv',0),
            })

@app.route("/logs")
def logs():
    # Lê todo o CSV de logs e passa para o template
    linhas = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                linhas.append(row)
    return render_template("logs.html", logs=linhas)

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logout realizado!", "success")
    return redirect(url_for('index'))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    # 1) só pode quem estiver logado
    if not session.get("logged_in"):
        return redirect(url_for("login", next=url_for("settings")))

    # 2) carrega todos os mapeamentos
    mappings   = load_printer_map()
    client_ip  = request.remote_addr
    # 3) encontra o registro da loja correspondente ao IP
    loja_map = next(
        (m for m in mappings if client_ip.startswith(f"10.{m['loja']}.")),
        None
    )

    if request.method == "POST":
        # 4) pega os novos valores enviados
        try:
            novo_ls_flor = int(request.form["ls_flor"])
            novo_ls_flv  = int(request.form["ls_flv"])
        except (KeyError, ValueError):
            flash("❌ Valores inválidos para LS", "error")
            return redirect(url_for("settings"))

        if loja_map:
            # 5) atualiza apenas esse registro
            loja_map["ls_flor"] = novo_ls_flor
            loja_map["ls_flv"]  = novo_ls_flv
            # 6) grava tudo de volta
            save_printer_map(mappings)
            flash("✅ LS atualizados com sucesso!", "success")
        else:
            flash("❌ Sua loja não está cadastrada para ajustes de margem.", "error")

        return redirect(url_for("settings"))

    # GET: pré-preenche o formulário com o que veio do CSV (ou defaults)
    if loja_map:
        ls_flor = loja_map.get("ls_flor", DEFAULT_LS_FLOR)
        ls_flv  = loja_map.get("ls_flv",  DEFAULT_LS_FLV)
    else:
        ls_flor = DEFAULT_LS_FLOR
        ls_flv  = DEFAULT_LS_FLV

    return render_template(
        "settings.html",
        ls_flor=ls_flor,
        ls_flv=ls_flv
    )

if __name__ == "__main__":
    append_log(evento="startup")
    try:
    # host='0.0.0.0' faz o Flask aceitar conexões de qualquer IP da sua LAN
      app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
    finally:
        append_log(evento="shutdown")
    
