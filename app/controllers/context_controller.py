import asyncio
import fnmatch
import os
from dotenv import load_dotenv
from flask import Blueprint, request, jsonify, current_app
from app.repositories.printer_repository import load_printer_map_from
from app.repositories.product_repository import ProductRepository
from app.services.printing_service import _is_test_mode
from app.services.templates_service import list_templates_by_mode
from app.services.product_service import ProductService
from app.dtos.context_response_dto import ContextResponseDTO, PrinterResponseDTO, ModosResponseDTO
from app.mappers.product_mapper import ProductMapper

bp = Blueprint("context_controller", __name__, url_prefix="/api")

@bp.route("/context", methods=["GET", "OPTIONS"])
def context():
    load_dotenv()
    
    # 1. Pega as configuraçõe
    bapi_url = os.getenv("BSTK_BAPI")
    token_ad = os.getenv("TOKEN_AD")

    product_repo = ProductRepository(base_url=bapi_url, token=token_ad)
    product_service = ProductService(client_api=product_repo)
    
    """Retorna info de contexto: loja detectada, impressoras, modos disponíveis."""
    if request.method == "OPTIONS":
        return "", 204

    DIRS = current_app.config["DIRS"]
    data_dir = DIRS["data"]
    templates_dir = DIRS["templates"]

    mappings = load_printer_map_from(data_dir)
    client_ip = request.remote_addr
    is_test_config = _is_test_mode()
    
    # Detecta modo teste: settings.txt OU acesso via localhost
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
    is_test = is_test_config or is_localhost

    # Override de IP em modo teste
    if is_test:
        client_ip = "10.17.30.2"

    # Identificação da loja
    loja_map = next((p for p in mappings if fnmatch.fnmatch(client_ip, p["pattern"])), None)
    
    # Modos válidos (baseado em todos os templates existentes no backend)
    valid_modes = list_templates_by_mode(templates_dir).keys()

    if not loja_map:
        return jsonify({"error": "Loja não cadastrada", "client_ip": client_ip}), 404
    else:
        printers = [p for p in mappings if p["loja"] == loja_map["loja"]]

    modos_mapeados = {}
    for chave in valid_modes:
        chave = chave.lower().strip()
        modos_mapeados[chave] = " ".join(x.capitalize() for x in chave.split("_"))

    printers_dto = [
        PrinterResponseDTO(
            ip=p["ip"],
            nome=p.get("nome", p["ip"]),
            funcao=p.get("funcao", []),
            ls=p.get("ls", {})
        ) for p in printers
    ]

    modos_dto = [
        ModosResponseDTO(key=k, label=v) 
        for k, v in sorted(modos_mapeados.items())
    ]

    response_dto = ContextResponseDTO(
        loja=loja_map["loja"],
        test_mode=is_test,
        printers=printers_dto,
        modos=modos_dto,
        ls=loja_map.get("ls", {})
    )

    return jsonify(response_dto.to_dict())


@bp.route("/search", methods=["GET", "OPTIONS"])
def search_products():
    service = ProductService
    """Busca produtos por código ou descrição."""
    if request.method == "OPTIONS":
        return "", 204

    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "codigo")  # codigo ou descricao
    modo = request.args.get("modo", "flv").lower()
    
    try:
        limit = int(request.args.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50

    if not query:
        return jsonify({"products": [], "error": "Query vazia"})

    # Seleciona a base de dados correta
    #db = current_app.config["DB_FLV"] if modo == "flv" or "padaria" else current_app.config["DB"]
    products = []
    
    if search_type == "descricao":
        resultados = asyncio.run(service.buscar_por_descricao(query, db, limite=limit))
        products = [ProductMapper.to_dto(r).to_dict() for r in resultados]
    else:
        rec = asyncio.run(service.buscar_por_codigo(query, db))
        if rec:
            products = [ProductMapper.to_dto(rec).to_dict()]

    return jsonify({
        "products": products,
        "count": len(products),
        "query": query,
        "type": search_type,
        "modo": modo,
    })
