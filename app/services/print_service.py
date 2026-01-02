from pathlib import Path
from datetime import datetime
from app.services.product_service import ProductService
from app.services.job_service import create_job
from app.services import zpl_service
from app.exceptions.validation_exception import ValidationException

def request_print(
    codigo: str,
    mode: str,
    copies: int,
    printer_ip: str,
    loja: str,
    templates_dir: Path,
    product_service: ProductService
):
    if not codigo or not mode or not printer_ip:
        raise ValidationException("Dados obrigatórios ausentes")

    product = product_service.find_product(codigo, mode)
    if not product:
        raise ValidationException("Produto não encontrado")

    template_path = zpl_service.resolve_template(mode, templates_dir)

    context = {
        "modo": mode,
        "texto": product["descricao"][:27],
        "codprod": product["codprod"],
        "ean": product["ean"],
        "copies": copies,
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validade": product.get("validade"),
        "infnutri": product.get("info_nutri", []),
    }
    try:
        copies = int(copies)
    except:
        copies = 1
        
    copies = max(1, min(copies, 100))
    zpl = zpl_service.render_zpl(template_path, context)

    job = create_job(
        printer_ip=printer_ip,
        zpl=zpl,
        loja=loja
    )

    return job