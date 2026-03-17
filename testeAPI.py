import asyncio
import platform
from aiohttp import ClientSession, TCPConnector
from pydantic import BaseModel
from typing import Optional, Any

# URL final que descobrimos ser a correta
BAPI_URL = "https://api.bistek.com.br/c5/it"

class RespostaAPI(BaseModel):
    sucesso: bool
    status: int
    dados: Optional[Any] = None
    erro: Optional[str] = None

class BistekClient:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def consultar_produto(self, loja: int, ean: str = "", seq: str = "") -> RespostaAPI:
        payload = {
            "loja": loja,
            "sequencia": seq,
            "ean": ean,
            "nome": ""
        }

        connector = TCPConnector(ssl=False)
        try:
            async with ClientSession(headers=self.headers, connector=connector) as session:
                async with session.post(BAPI_URL, json=payload, timeout=10) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        return RespostaAPI(sucesso=True, status=200, dados=json_data)
                    else:
                        texto_erro = await response.text()
                        return RespostaAPI(sucesso=False, status=response.status, erro=texto_erro)
        except Exception as e:
            return RespostaAPI(sucesso=False, status=500, erro=str(e))

async def main():
    # Substitua pelo seu token atualizado
    meu_token = ""
    
    client = BistekClient(meu_token)
    
    loja_teste = 175 
    ean_teste = "792"

    print(f"consulta: Loja {loja_teste} | EAN {ean_teste}")
    
    resultado = await client.consultar_produto(loja=loja_teste, ean=ean_teste)
    
    if resultado.sucesso:
        # A API retorna um objeto que tem uma lista dentro de 'dados'
        print("✅ Conexão OK!")
        if resultado.dados and resultado.dados.get('dados'):
            print(f"📦 Produto Encontrado: {resultado.dados['dados']}")
        else:
            print("⚠️ API respondeu, mas a lista de produtos veio vazia.")
            print(f"Retorno bruto: {resultado.dados}")
    else:
        print(f"❌ Erro {resultado.status}: {resultado.erro}")

if __name__ == "__main__":
    # Correção para loop do asyncio no Windows
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())