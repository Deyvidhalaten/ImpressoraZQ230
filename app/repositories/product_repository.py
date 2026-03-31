import csv
from pathlib import Path
from typing import Optional

from app.dtos.product_response_dto import RespostaAPI

import aiohttp
from aiohttp import ClientSession, TCPConnector
from app.dtos.product_response_dto import RespostaAPI

class ProductRepository:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        # DEBUG: Verifique se o token começa com "Bearer " ou se está limpo
        print(f"DEBUG REPOSITORY: Token recebido tem {len(token) if token else 0} caracteres")
        self.headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
        }

    async def consultar_produto(self, loja: int, ean: str = "", seq: str = "", nome: str = "") -> "RespostaAPI":
        payload = {
            "loja": loja,
            "sequencia": seq,
            "ean": ean,
            "nome": nome
        }

        # Conector sem SSL, Ver com Jared se vai manter assim
        connector = TCPConnector(ssl=False)
        
        try:
            async with ClientSession(headers=self.headers, connector=connector) as session:
                #  Utilizo a base_url vinda do .env
                url = f"{self.base_url}/c5/it" 
                
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        # Retorna o DTO de Sucesso
                        return RespostaAPI(sucesso=True, status=200, dados=json_data)
                    else:
                        texto_erro = await response.text()
                        return RespostaAPI(sucesso=False, status=response.status, erro=texto_erro)
                        
        except Exception as e:
            # Captura erros de rede, timeout, etc.
            return RespostaAPI(sucesso=False, status=500, erro=str(e))
