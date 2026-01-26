import fnmatch
from datetime import datetime
import os
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, session
)

from app.services.mapping_service import load_printer_map_from
from app.services.product_service import consulta_Base
from app.services.printing_service import enviar_para_impressora_ip
from app.services.templates_service import list_templates_by_mode, render_zpl
from app.services.log_service import append_log, log_audit, log_error
from app.services.trace_service import start_trace, get_trace

bp = Blueprint("main", __name__)


# ------------------------------------------------------------
# RENDER BÁSICO
# ------------------------------------------------------------
def _render_basic(DIRS):
    return render_template(
        "index.html",
        printers=[], available=[], modo=None,
        modos_disponiveis=[], modos_mapeados={},
        templates_by_mode=list_templates_by_mode(DIRS["templates"])
    )


# ------------------------------------------------------------
# RENDER COMPLETO
# ------------------------------------------------------------
def _render_full(DIRS, printers, available, modo, modos_disponiveis, modos_mapeados):
    return render_template(
        "index.html",
        printers=printers,
        available=available,
        modo=modo,
        modos_disponiveis=modos_disponiveis,
        modos_mapeados=modos_mapeados,
        templates_by_mode=list_templates_by_mode(DIRS["templates"])
    )


# ------------------------------------------------------------
# DESCOBRE MODOS POSSÍVEIS
# ------------------------------------------------------------
def _descobrir_modos(DIRS, printers):
    templates_dir = DIRS["templates"]

    valid_modes = {
        os.path.splitext(f)[0].split("_")[0].lower()
        for f in os.listdir(templates_dir)
        if f.endswith(".zpl.j2")
    }

    modos_mapeados = {}
    for p in printers:
        for m in p.get("funcao", []):
            chave = m.lower().strip()
            if chave in valid_modes:
                modos_mapeados[chave] = " ".join(x.capitalize() for x in chave.split("_"))

    modos_disponiveis = [
        (k, modos_mapeados[k]) for k in sorted(modos_mapeados.keys())
    ]

    return modos_disponiveis, modos_mapeados


# ------------------------------------------------------------
# ROTA PRINCIPAL
# ------------------------------------------------------------
@bp.route("/", methods=["GET", "POST"])
def index():

    DIRS = current_app.config["DIRS"]
    data_dir = DIRS["data"]

    mappings = load_printer_map_from(data_dir)
    client_ip = request.remote_addr

    # --------------- Identificação da Loja ---------------
    loja_map = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
    if not loja_map:
        flash("❌ Loja não cadastrada — contate o administrador.", "error")
        return _render_basic(DIRS)

    printers = [p for p in mappings if p["loja"] == loja_map["loja"]]
    if not printers:
        flash("❌ Nenhuma impressora configurada para esta loja.", "error")
        return _render_basic(DIRS)

    modos_disponiveis, modos_mapeados = _descobrir_modos(DIRS, printers)

    modo = (
        request.form.get("modo")
        or session.get("ultimo_modo")
        or (modos_disponiveis[0][0] if modos_disponiveis else None)
    )
    session["ultimo_modo"] = modo

    available = [p for p in printers if modo in p["funcao"]]

    # ------------------------------------------------------------
    # GET → Tela normal
    # ------------------------------------------------------------
    if request.method == "GET":
        return _render_full(DIRS, printers, available, modo, modos_disponiveis, modos_mapeados)

    # ------------------------------------------------------------
    # POST → Inicia Trace
    # ------------------------------------------------------------
    trace = start_trace("impressao")
    trace.add("inicio", ip=client_ip, modo=modo)

    action = request.form.get("action", "print")
    sel_ip = request.form.get("printer_ip")

    # Escolha da impressora
    if sel_ip and any(p["ip"] == sel_ip for p in available):
        printer_ip = sel_ip
    elif available:
        printer_ip = available[0]["ip"]
    else:
        trace.add("nenhuma_impressora_compativel")
        dados = trace.finish("falha")
        log_audit("impressao_falha", trace=dados)

        flash(f"❌ Nenhuma impressora disponível para {modo}", "error")
        return _render_full(DIRS, printers, available, modo, modos_disponiveis, modos_mapeados)

    # ------------------------------------------------------------
    # AÇÃO LOAD
    # ------------------------------------------------------------
    if action == "load":
        modo_lower = modo.lower()
        ls = loja_map["ls_flor"] if modo_lower == "floricultura" else loja_map["ls_flv"]

        trace.add("load_cmd", ip=printer_ip, ls=ls)

        zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
        sucesso = enviar_para_impressora_ip(zpl, printer_ip)

        dados = trace.finish("sucesso" if sucesso else "falha")
        log_audit("load", trace=dados)

        flash("Comando enviado" if sucesso else "Falha no envio", "success" if sucesso else "error")
        return _render_full(DIRS, printers, available, modo, modos_disponiveis, modos_mapeados)

    # ------------------------------------------------------------
    # IMPRESSÃO NORMAL
    # ------------------------------------------------------------
    try:
        copies = max(1, min(int(request.form.get("copies", "1")), 100))
    except:
        copies = 1

    codigo_raw = request.form.get("codigo", "").strip()
    db = current_app.config["DB_FLV"] if modo.lower() == "flv" else current_app.config["DB"]

    trace.add("consulta_db", codigo=codigo_raw)

    try:
        rec = consulta_Base(codigo_raw, db)
        trace.add("consulta_db_result", found=bool(rec))
    except Exception as e:
        trace.add("consulta_db_erro", erro=str(e))
        log_error("Erro DB", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        raise

    if not rec:
        trace.add("produto_nao_encontrado", codigo=codigo_raw)
        dados = trace.finish("falha")
        log_audit("impressao_falha", trace=dados)
        flash("❌ Produto não encontrado", "error")
        return _render_full(DIRS, printers, available, modo, modos_disponiveis, modos_mapeados)

    # ------------------------------------------------------------
    # RENDER ZPL
    # ------------------------------------------------------------
    tpl = f"{modo.lower()}_default.zpl.j2"
    ctx = {
        "modo": modo,
        "texto": rec["descricao"][:27],
        "codprod": rec["codprod"],
        "ean": rec["ean"],
        "copies": copies,
        "ls": loja_map["ls_flor"] if modo.lower() == "floricultura" else loja_map["ls_flv"],
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validade": rec.get("validade"),
        "nutri": rec.get("nutri"),
    }

    trace.add("render_zpl_start", template=tpl)

    try:
        zpl = render_zpl(current_app.config["ZPL_ENV"], tpl, **ctx)
        trace.add("render_zpl_success", length=len(zpl))
    except Exception as e:
        trace.add("render_zpl_erro", erro=str(e))
        log_error("Erro render ZPL", erro=str(e))
        dados = trace.finish("erro")
        log_audit("impressao_falha", trace=dados)
        raise

    # ENVIO À IMPRESSORA
    trace.add("send_to_printer", ip=printer_ip)
    sucesso = enviar_para_impressora_ip(zpl, printer_ip)

    if sucesso:
        trace.add("print_success", copies=copies)
    if not sucesso:
        trace.add("print_failed", ip=printer_ip)

    #Finaliza trace
    dados = trace.finish("sucesso" if sucesso else "falha")

    #Auditoria
    log_audit("impressao" if sucesso else "impressao_falha", trace=dados)

    #Feedback do usuario
    flash(
        f"✅ {copies} etiqueta(s) enviadas para {printer_ip}"
        if sucesso else f"❌ Falha ao enviar para {printer_ip}",
        "success" if sucesso else "error"
    )

    return redirect(url_for("main.index"))
