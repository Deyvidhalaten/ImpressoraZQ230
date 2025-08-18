import fnmatch
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ..services.product_service import consulta_Base
from ..services.mapping_service import load_printer_map, save_printer_map
from ..services.printing_service import enviar_para_impressora_ip
from ..services.log_service import append_log
from ..services.templates_service import list_templates_by_mode, render_zpl, make_env
from ..constants import LOG_FILE

bp = Blueprint("main", __name__)
ZPL_ENV = None  # inicializado no app factory

@bp.record_once
def _setup(state):
    global ZPL_ENV
    DIRS = state.app.config["DIRS"]
    ZPL_ENV = make_env(DIRS["templates"])

@bp.route("/", methods=["GET", "POST"])
def index():
    mappings  = load_printer_map()
    client_ip = request.remote_addr

    loja_map = next((m for m in mappings if fnmatch.fnmatch(client_ip, m['pattern'])), None)
    if not loja_map:
        flash("❌ Loja não cadastrada — contate o administrador.", "error")
        return render_template("index.html", printers=[], available=[], modo="Floricultura")

    modo      = request.form.get("modo", "Floricultura")
    printers  = [p for p in mappings if p['loja'] == loja_map['loja']]
    available = [p for p in printers if modo in p['funcao']]

    def _render():
        DIRS = current_app.config["DIRS"]
        return render_template("index.html",
            printers=printers, available=available, modo=modo,
            templates_by_mode=list_templates_by_mode(DIRS["templates"])
        )

    if request.method == "POST":
        action = request.form.get("action", "print")
        sel_ip = request.form.get("printer_ip")
        if sel_ip and any(p['ip']==sel_ip for p in available):
            printer_ip = sel_ip
        elif available:
            printer_ip = available[0]['ip']
        else:
            flash(f"❌ Nenhuma impressora disponível para o modo {modo}", "error")
            return _render()

        if action == "load":
            ls   = loja_map['ls_flor'] if modo=="Floricultura" else loja_map['ls_flv']
            zpl  = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            sucesso = enviar_para_impressora_ip(zpl, printer_ip)
            flash(f"{'✅' if sucesso else '❌'} Carga {modo} {'enviada' if sucesso else 'falhou'} em {printer_ip}",
                  "success" if sucesso else "error")
            return _render()

        try:
            copies = max(1, min(int(request.form.get("copies","1")),100))
        except ValueError:
            copies = 1

        codigo_raw = request.form.get("codigo","").strip()
        from ..app import DB, DB_FLV  # evita ciclo de import
        db   = DB_FLV if modo=="FLV" else DB
        rec  = consulta_Base(codigo_raw, db)
        if not rec:
            flash("❌ Produto não encontrado", "error")
            return _render()

        tpl = request.form.get("template") or None
        ctx = {
            "modo": modo,
            "texto": rec['descricao'],
            "codprod": rec['codprod'],
            "ean": rec['ean'],
            "copies": copies,
            "ls": loja_map['ls_flor'] if modo=="Floricultura" else loja_map['ls_flv'],
            "data": datetime.now().strftime('%d/%m/%Y'),
            "validade": rec.get('validade'),
            "infnutri": rec.get('info_nutri', []),
        }
        zpl = render_zpl(ZPL_ENV, tpl, **ctx)
        sucesso = enviar_para_impressora_ip(zpl, printer_ip)
        if sucesso:
            append_log("print", client_ip, printer_ip,
                       f"ean={rec['ean']},codprod={rec['codprod']},copies={copies},modo={modo}")
            flash(f"✅ {copies} etiqueta(s) para {printer_ip}", "success")
        else:
            flash(f"❌ Falha de comunicação com {printer_ip}", "error")
        return redirect(url_for("main.index"))
    return _render()
