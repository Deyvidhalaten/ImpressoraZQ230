from app.dtos.product_response_dto import ProductResponseDTO

class ProductMapper:
    @staticmethod
    def to_dto(raw_dict: dict) -> ProductResponseDTO:
        return ProductResponseDTO(
            codprod=raw_dict.get("codprod", ""),
            ean=raw_dict.get("ean", ""),
            descricao=raw_dict.get("descricao", ""),
            validade=raw_dict.get("validade")
        )
