from app.dtos.product_response_dto import ProductResponseDTO

class ProductMapper:
    @staticmethod
    def to_dto(data: dict) -> ProductResponseDTO:
        return ProductResponseDTO(
            # Tenta pegar 'codprod', se não tiver tenta 'CODPROD', se não, string vazia
            codprod=str(data.get('codprod') or data.get('CODPROD') or data.get('codigo') or ''),
            ean=str(data.get('ean') or data.get('EAN13') or data.get('GTIN') or ''),
            descricao=data.get('descricao') or data.get('DESCRICAO') or data.get('NOME') or '',
            validade=data.get('validade'),
            # AQUI ESTÁ O SEGREDO: Guardamos o JSON original inteiro aqui dentro
            raw_data=data 
        )
