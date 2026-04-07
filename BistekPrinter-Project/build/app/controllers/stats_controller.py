from flask import Blueprint, request, jsonify, current_app

bp = Blueprint("stats_controller", __name__, url_prefix="/api")

@bp.route("/stats", methods=["GET", "OPTIONS"])
def get_stats():
    """Retorna estatísticas de impressão baseadas no stats.csv."""
    if request.method == "OPTIONS":
        return "", 204

    from datetime import datetime, timedelta
    from app.repositories.printer_repository import load_printer_map_from

    DIRS = current_app.config["DIRS"]
    stats_csv = DIRS["logs"] / "stats.csv"

    # Parâmetros
    try:
        dias = int(request.args.get("dias", 30))
    except (ValueError, TypeError):
        dias = 30
    filtro_loja = request.args.get("loja")

    cutoff = datetime.now() - timedelta(days=dias)

    por_loja = {}
    por_dia = {}
    total_etiquetas = 0
    lojas_set = set()

    if stats_csv.exists():
        try:
            with open(stats_csv, "r", encoding="utf-8") as f:
                first_line = True
                for line in f:
                    line = line.strip()
                    if not line: 
                        continue
                    
                    if first_line and (line.lower().startswith("data") or "loja" in line.lower()):
                        first_line = False
                        continue
                    first_line = False

                    parts = line.split(";")
                    if len(parts) < 4:
                        continue

                    data_str, loja, modo, qtd_str = parts[0], parts[1], parts[2], parts[3]

                    try:
                        if "/" in data_str:
                            dt = datetime.strptime(data_str, "%d/%m/%Y %H:%M:%S")
                        else:
                            dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue

                    if dt < cutoff:
                        continue
                    
                    lojas_set.add(loja)

                    if filtro_loja and loja != filtro_loja:
                        continue

                    try:
                        qtd = int(qtd_str)
                    except ValueError:
                        qtd = 1
                    
                    total_etiquetas += qtd
                    
                    por_loja[loja] = por_loja.get(loja, 0) + qtd
                    
                    dia_key = dt.strftime("%Y-%m-%d")
                    por_dia[dia_key] = por_dia.get(dia_key, 0) + qtd

        except Exception as e:
            print(f"Erro ao ler stats.csv: {e}")
            pass

    media_diaria = round(total_etiquetas / max(dias, 1), 1)

    mappings = load_printer_map_from(DIRS["data"])
    todas_lojas = {p["loja"] for p in mappings if p.get("loja")}
    lojas_set.update(todas_lojas)

    sorted_por_dia = [
        {"label": datetime.strptime(k, "%Y-%m-%d").strftime("%d/%m"), "value": v}
        for k, v in sorted(por_dia.items())
    ]

    return jsonify({
        "total": total_etiquetas,
        "lojas": sorted(list(lojas_set), key=lambda x: int(x) if x.isdigit() else 9999),
        "media_diaria": media_diaria,
        "por_loja": por_loja,
        "por_dia": sorted_por_dia,
    })
