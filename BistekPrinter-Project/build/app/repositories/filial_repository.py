import aiohttp
from dataclasses import dataclass
from typing import List, Any, Optional

@dataclass
class RespostaAPI:
    sucesso: bool
    status: int
    dados: Optional[Any] = None
    erro: Optional[str] = None

class FilialRepository:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get_filiais_raw(self) -> RespostaAPI:
        url = f"{self.base_url}/c5/l"
        connector = aiohttp.TCPConnector(ssl=False)
        try:
            async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        json_data = await response.json()
                        return RespostaAPI(sucesso=True, status=200, dados=json_data)
                    
                    texto_erro = await response.text()
                    return RespostaAPI(sucesso=False, status=response.status, erro=texto_erro)
        except Exception as e:
            return RespostaAPI(sucesso=False, status=500, erro=str(e))