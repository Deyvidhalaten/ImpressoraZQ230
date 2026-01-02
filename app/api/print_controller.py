from urllib import request

from app.services import print_service


@bp.route("/api/print", methods=["POST"]) # type: ignore
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
