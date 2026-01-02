from app.services import print_service, zpl_service
from flask import Blueprint, request, jsonify, current_app

from app.exceptions.validation_exception import ValidationException
from app.services.print_service import request_print
from app.services.product_service import ProductService

bp = Blueprint("print_api", __name__, url_prefix="/api")

@bp.route("/print", methods=["POST"]) # type: ignore
def print_label():
    data = request.json

    job = print_service.request_print(
        codigo=data["codigo"],
        modo=data["modo"],
        copies=data.get("copies", 1),
        printer_ip=data["printer_ip"],
        loja=data["loja"]
    )

    return {
        "job_id": job.job_id,
        "status": job.status
    }, 201

@bp.route("/print/modes", methods=["GET"])
def get_print_modes():
    try:
        templates_dir = current_app.config["DIRS"]["templates"]

        modes = zpl_service.list_available_modes(templates_dir)

        return jsonify({
            "modes": modes
        }), 200

    except Exception as e:
        current_app.logger.exception(e)
        return jsonify({
            "error": "Erro ao listar modos de impressão"
        }), 500
