from flask import Blueprint, request, jsonify, current_app
from app.exceptions.validation_exception import ValidationException

bp = Blueprint("products_api", __name__, url_prefix="/api/products")

@bp.route("/search", methods=["GET"])
def search_products():
    try:
        q = (request.args.get("q") or "").strip()
        modo = (request.args.get("mode") or "flor").strip()
        limit = request.args.get("limit") or "10"

        if len(q) < 2:
            raise ValidationException("Informe ao menos 2 caracteres para busca")

        product_service = current_app.config["SERVICES"]["product_service"]
        items = product_service.search(q=q, modo=modo, limit=int(limit))

        return jsonify({"items": items}), 200

    except ValidationException as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({"error": "Erro interno do servidor"}), 500
