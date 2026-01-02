from flask import Blueprint, request, jsonify, current_app

from app.exceptions.validation_exception import ValidationException
from app.services.print_service import request_print
from app.services.product_service import ProductService

bp = Blueprint("print_api", __name__, url_prefix="/api")


@bp.route("/print", methods=["POST"])
def print_label():
    try:
        payload = request.get_json(force=True)

        codigo = payload.get("codigo")
        mode = payload.get("mode")
        copies = payload.get("copies", 1)
        printer_ip = payload.get("printer_ip")
        loja = payload.get("loja")

        templates_dir = current_app.config["DIRS"]["templates"]

        product_service = ProductService(current_app.config)

        job = request_print(
            codigo=codigo,
            mode=mode,
            copies=copies,
            printer_ip=printer_ip,
            loja=loja,
            templates_dir=templates_dir,
            product_service=product_service
        )

        return jsonify({
            "status": "queued",
            "job_id": job.id
        }), 201

    except ValidationException as e:
        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({
            "error": "Erro interno do servidor"
        }), 500
