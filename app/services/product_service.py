# services/product_service.py

from app.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, client_api, token: str):
        self.client_api = client_api
        self.repository = ProductRepository(base_url=client_api, token=token)

    async def buscar_por_codigo(self, cod_empresa: int, entrada: str):
        """
        Tenta EAN e Sequência.
        """
        apenas_digitos = "".join(filter(str.isdigit, entrada))
        if not apenas_digitos:
            return None

        # 1. Tenta como EAN
        res = await self.repository.consultar_produto(loja=cod_empresa, ean=apenas_digitos, seq="", nome="")
        
        # 2. Se não achou (lista vazia ou erro), tenta como Sequência (Cod Interno)
        if not res.sucesso or not res.dados.get('dados'):
            res = await self.repository.consultar_produto(loja=cod_empresa, ean="", seq=apenas_digitos, nome="")
            
        return res

    async def buscar_por_descricao(self, cod_empresa: int, termo: str):
        """
        Chama a API focando apenas no campo 'nome'.
        """
        return await self.repository.consultar_produto(
            loja=cod_empresa, 
            ean="", 
            seq="", 
            nome=termo.lower()
        )