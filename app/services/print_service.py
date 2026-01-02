# app/services/print_service.py

from app.services import product_service
from app.services import job_service
from app.services import zpl_service
from app.exceptions import validation_exception


def request_print(codigo, modo, copies, printer_ip, loja):
    if not codigo or not modo:
        raise ValidationException("Dados inválidos")

    product = product_service.find_product(codigo, modo)
    if not product:
        raise ValidationException("Produto não encontrado")

    zpl = zpl_service.build_zpl(
        product=product,
        modo=modo,
        copies=copies,
        loja=loja
    )

    job = job_service.create_job(
        printer_ip=printer_ip,
        zpl=zpl,
        loja=loja
    )

    return job
