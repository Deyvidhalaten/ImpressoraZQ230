# services/filial_service.py
from typing import Optional


class FilialService:
    def __init__(self, client_api):
        self.client_api = client_api
        self.mapa_filiais = {} # Cache em memória

    async def sincronizar_rede(self):
        """Roda na Main: Limpa e mapeia Lojas e CDs"""
        res = await self.client_api.get_filiais_raw() # Chama /c5/l
        if res.sucesso:
            novo_mapa = {}
            for item in res.dados:
                cod_puro = str(item['CODIGO'])
                tipo = item['TIPO']
                
                # Suas regras de filtragem
                if tipo == 'L': filtrado = cod_puro[:-1]
                elif tipo == 'C': filtrado = cod_puro[1:-1]
                else: continue
                
                novo_mapa[filtrado] = int(cod_puro)
            
            self.mapa_filiais = novo_mapa
            return True
        return False

    def obter_cod_empresa_por_ip(self, ip_cliente: str) -> Optional[int]:
        """Ex: Recebe 10.17.30.41 -> Extrai '17' -> Retorna 175"""
        try:
            partes = ip_cliente.split('.')
            segmento = partes[1] # Pega o '17'
            return self.mapa_filiais.get(segmento)
        except (IndexError, AttributeError):
            return None