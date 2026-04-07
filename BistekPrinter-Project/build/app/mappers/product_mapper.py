from app.dtos.product_response_dto import ProductResponseDTO

class ProductMapper:
    @staticmethod
    def to_dto(data: dict) -> ProductResponseDTO:
        # Tenta pegar 'codprod', se não tiver tenta chaves da BAPI
        codprod_raw = data.get('codprod') or data.get('CODPROD') or data.get('codigo') or data.get('SEQPRODUTO') or ''
        ean_raw = data.get('ean') or data.get('EAN13') or data.get('GTIN') or data.get('EAN') or ''
        desc_raw = data.get('descricao') or data.get('DESCRICAO') or data.get('NOME') or ''
        
        # Validade pode vir como inteiro (antigo) ou string de data dt_validade
        val_raw = data.get('validade') or data.get('DT_VALIDADE')
        
        return ProductResponseDTO(
            codprod=str(codprod_raw),
            ean=str(ean_raw),
            descricao=str(desc_raw),
            validade=val_raw,
            full_data=data 
        )
