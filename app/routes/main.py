import fnmatch
from datetime import datetime
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session

from app.services.mapping_service import load_printer_map_from
from app.services.product_service import consulta_Base
from app.services.printing_service import enviar_para_impressora_ip
from app.services.log_service import append_log
from app.services.templates_service import list_templates_by_mode, render_zpl

bp = Blueprint("main", __name__)

@bp.route("/", methods=["GET", "POST"])
def index():
    DIRS = current_app.config["DIRS"]
    data_dir = DIRS["data"]
    templates_dir = DIRS["templates"]

    mappings = load_printer_map_from(data_dir)
    client_ip = request.remote_addr

    # 🔹 Identifica a loja com base no IP
    loja_map = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
    if not loja_map:
        flash("❌ Loja não cadastrada — contate o administrador.", "error")
        return render_template(
            "index.html",
            printers=[], available=[], modo=None,
            modos_disponiveis=[],
            templates_by_mode=list_templates_by_mode(DIRS["templates"])
        )

    # 🔹 Filtra impressoras da loja atual
    printers = [p for p in mappings if p['loja'] == loja_map['loja']]

    if not printers:
        flash("❌ Nenhuma impressora encontrada para esta loja.", "error")
        return render_template(
            "index.html",
            printers=[], available=[], modo=None,
            modos_disponiveis=[],
            templates_by_mode=list_templates_by_mode(DIRS["templates"])
        )
    
    # --- Obtém todos os modos válidos a partir dos templates ---
    templates_dir = DIRS["templates"]

    # --- Modos válidos encontrados nos templates ---
    valid_modes = {
           os.path.splitext(f)[0].split("_")[0].lower()
           for f in os.listdir(templates_dir)
           if f.endswith(".zpl.j2")
           }

    # --- Mapeia modos válidos (interno → exibido) ---
    modos_mapeados = {}
    for p in printers:
        for m in p.get('funcao', []):
            chave = m.strip().lower()
            if chave in valid_modes:
                valor_exibicao = ' '.join(part.capitalize() for part in chave.split('_'))
                modos_mapeados[chave] = valor_exibicao

    # --- Lista modos para exibição na tela ---
    modos_disponiveis = [
        (chave, modos_mapeados[chave])
        for chave in sorted(modos_mapeados.keys())]

    # 🔹 Determina o modo atual (POST → último da sessão → primeiro disponível)
    modo = (
        request.form.get("modo")
        or session.get("ultimo_modo")
        or (modos_disponiveis[0] if modos_disponiveis else None)
    )

    # 🔹 Filtra impressoras compatíveis com o modo selecionado
    available = [p for p in printers if modo in p['funcao']]

    # 🔹 Salva o modo atual na sessão
    session["ultimo_modo"] = modo

    # Renderização padrão
    def _render():
        return render_template(
            "index.html",
            printers=printers,
            available=available,
            modo=modo,
            modos_disponiveis=modos_disponiveis,
            modos_mapeados=modos_mapeados,  # novo
            templates_by_mode=list_templates_by_mode(DIRS["templates"])
        )

    # Lógica de POST (ações)
    if request.method == "POST":
        action = request.form.get("action", "print")
        sel_ip = request.form.get("printer_ip")

        if sel_ip and any(p['ip'] == sel_ip for p in available):
            printer_ip = sel_ip
        elif available:
            printer_ip = available[0]['ip']
        else:
            flash(f"❌ Nenhuma impressora disponível para o modo {modo}", "error")
            return _render()

        # 🔸 Carga (comando manual)
        if action == "load":
            ls = loja_map.get('ls_flor') if modo == "floricultura" else loja_map.get('ls_flv')
            zpl = f"^XA\n^MD30\n^LS{ls}\n^XZ"
            sucesso = enviar_para_impressora_ip(zpl, printer_ip)
            flash(
                f"{'✅' if sucesso else '❌'} Carga {modo} {'enviada' if sucesso else 'falhou'} em {printer_ip}",
                "success" if sucesso else "error"
            )
            return _render()

        # 🔸 Impressão normal
        try:
            copies = max(1, min(int(request.form.get("copies", "1")), 100))
        except ValueError:
            copies = 1

        codigo_raw = request.form.get("codigo", "").strip()
        DB = current_app.config["DB"]
        DB_FLV = current_app.config["DB_FLV"]
        db = DB_FLV if modo.lower() == "flv" else DB

        rec = consulta_Base(codigo_raw, db)
        if not rec:
            flash("❌ Produto não encontrado", "error")
            return _render()
        
        norma_descricao = rec['descricao']
        #Limita a quantidade de caracteres em 27 a descrição
        norma_descricao = norma_descricao[:27]
        tpl = f"{modo.lower()}_default.zpl.j2"
        ctx = {
            "modo":     modo,
            "texto":    norma_descricao,
            "codprod":  rec['codprod'],
            "ean":      rec['ean'],
            "copies":   copies,
            "ls":       loja_map.get('ls_flor') if modo == "Floricultura" else loja_map.get('ls_flv'),
            "data":     datetime.now().strftime('%d/%m/%Y'),
            "validade": rec.get('validade'),
            "infnutri": rec.get('info_nutri', []),
        }

        ZPL_ENV = current_app.config["ZPL_ENV"]
        zpl = render_zpl(ZPL_ENV, tpl, **ctx)

        sucesso = enviar_para_impressora_ip(zpl, printer_ip)
        if sucesso:
            append_log("print", client_ip, printer_ip,
                       f"ean={rec['ean']},codprod={rec['codprod']},copies={copies},modo={modo}")
            flash(f"✅ {copies} etiqueta(s) para {printer_ip}", "success")
        else:
            flash(f"❌ Falha de comunicação com {printer_ip}", "error")

        return redirect(url_for("main.index"))

    # 🔸 GET padrão
    return _render()