from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import os, csv
from ..constants import USUARIO, SENHA, SHUTDOWN_PASSWORD, LOG_FILE, DEFAULT_LS_FLOR, DEFAULT_LS_FLV
from ..services.mapping_service import load_printer_map, save_printer_map
from ..services.log_service import append_log

bp = Blueprint("admin", __name__)

@bp.route("/login", methods=["GET","POST"])
def login():
    next_page = request.args.get('next', url_for('admin.settings'))
    if request.method == "POST":
        if request.form.get('username') == USUARIO and request.form.get('password') == SENHA:
            session.permanent = True
            session['logged_in']= True
            flash("✅ Login bem-sucedido!", "success")
            return redirect(next_page)
        flash("❌ Credenciais inválidas!", "error")
        return redirect(url_for('admin.login', next=next_page))
    return render_template("login.html")

@bp.route("/logout")
def logout():
    session.clear()
    flash("✅ Logout realizado!", "success")
    return redirect(url_for('main.index'))

@bp.route("/printers", methods=["GET","POST"])
def printers():
    mappings = load_printer_map()
    mappings.sort(key=lambda m: int(m['loja'] or 0))
    if request.method == "POST":
        action_type = request.form.get("action", "save")
        if action_type == "delete":
            pattern_to_delete = request.form.get("pattern")
            ip_to_delete      = request.form.get("ip")
            m_antigo = next((m for m in mappings if m["pattern"]==pattern_to_delete and m["ip"]==ip_to_delete), None)
            if m_antigo:
                mappings = [m for m in mappings if not (m["pattern"]==pattern_to_delete and m["ip"]==ip_to_delete)]
                save_printer_map(mappings)
                append_log("mapping_delete", request.remote_addr, m_antigo.get("nome", m_antigo.get("ip","")),
                           f"loja={m_antigo['loja']}, ip={ip_to_delete}")
                flash(f"🗑️ Impressora {ip_to_delete} excluída com sucesso!", "success")
            else:
                flash("❌ Impressora não encontrada para exclusão.", "error")
            return redirect(url_for("admin.printers"))

        loja   = request.form.get('loja','').strip()
        funcao_list = request.form.getlist("funcao")
        nome = request.form.get('nome','').strip()
        ip = request.form.get('ip','').strip()
        ls_flor = request.form.get('ls_flor','').strip()
        ls_flv  = request.form.get('ls_flv','').strip()
        if not loja.isdigit() or not funcao_list:
            flash("❌ Loja e pelo menos uma Função são obrigatórios", "error")
            return redirect(url_for('admin.printers'))
        try:
            ls_flor_val = int(ls_flor); ls_flv_val = int(ls_flv); ip_str = str(ip)
        except ValueError:
            flash("❌ Valores de LS inválidos", "error")
            return redirect(url_for('admin.printers'))

        pattern = f"10.{int(loja)}.*"
        updated = False
        for m in mappings:
            if m['loja'] == loja and m['ip'] == ip_str:
                m_antigo = m.copy()
                m.update({'nome': nome, 'funcao': funcao_list, 'ip': ip_str, 'ls_flor': ls_flor_val, 'ls_flv': ls_flv_val})
                updated = True
                append_log("mapping_update", request.remote_addr, detalhes=(
                    f"loja={loja}, old_ls_flor={m_antigo['ls_flor']}, new_ls_flor={ls_flor_val}, "
                    f"old_ls_flv={m_antigo['ls_flv']}, new_ls_flv={ls_flv_val}"
                ))
                break
        if not updated:
            mappings.append({'loja': loja, 'pattern': pattern, 'nome': nome, 'ip': ip_str,
                             'funcao': funcao_list, 'ls_flor': ls_flor_val, 'ls_flv': ls_flv_val})
        append_log("mapping_add", request.remote_addr, detalhes=f"loja={loja}, ls_flor={ls_flor_val}, ls_flv={ls_flv_val}")
        save_printer_map(mappings)
        flash("✅ Mapeamento salvo com sucesso!", "success")
        return redirect(url_for('admin.printers'))
    return render_template("printers.html", mappings=mappings)

@bp.route("/logs")
def logs():
    linhas = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                linhas.append(row)
    return render_template("logs.html", logs=linhas)

@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("logged_in"):
        return redirect(url_for("admin.login", next=url_for("admin.settings")))
    mappings   = load_printer_map()
    client_ip  = request.remote_addr
    loja_map = next((m for m in mappings if client_ip.startswith(f"10.{m['loja']}.")), None)
    if request.method == "POST":
        try:
            novo_ls_flor = int(request.form["ls_flor"]); novo_ls_flv  = int(request.form["ls_flv"])
        except (KeyError, ValueError):
            flash("❌ Valores inválidos para LS", "error")
            return redirect(url_for("admin.settings"))
        if loja_map:
            loja_map["ls_flor"] = novo_ls_flor; loja_map["ls_flv"]  = novo_ls_flv
            save_printer_map(mappings)
            flash("✅ LS atualizados com sucesso!", "success")
        else:
            flash("❌ Sua loja não está cadastrada para ajustes de margem.", "error")
        return redirect(url_for("admin.settings"))
    if loja_map:
        ls_flor = loja_map.get("ls_flor", DEFAULT_LS_FLOR); ls_flv  = loja_map.get("ls_flv",  DEFAULT_LS_FLV)
    else:
        ls_flor = DEFAULT_LS_FLOR; ls_flv  = DEFAULT_LS_FLV
    return render_template("settings.html", ls_flor=ls_flor, ls_flv=ls_flv)
