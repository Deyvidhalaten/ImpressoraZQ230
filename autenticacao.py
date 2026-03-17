import asyncio
import platform
from aiohttp import ClientSession
from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.fernet import Fernet
from json import dumps
from os import environ
from pydantic import BaseModel
from typing import Any

BAPI = "https://api.bistek.com.br"
TOKEN = ""
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

class Autenticado(BaseModel):
    sucesso: bool = False
    mensagem: str = "Nenhuma"
    status: int = 401


async def patch_bapi_autenticador(envio: dict) -> Autenticado:
    if not TOKEN:
        return Autenticado(mensagem="Token não informado")

    async with ClientSession(headers=HEADERS) as s:
        async with s.patch(f"{BAPI}/ad/autenticacao", json=envio, ssl=False) as r:
            retorno = {"ok": False}
            if r.status in(200, 400, 401):
                retorno = await r.json()
            return Autenticado(
                sucesso=retorno.get("ok") or False,
                mensagem=str(retorno.get("msg") or r.reason),
                status=r.status,
            )


def decode(d: Any = None) -> str:
    return urlsafe_b64encode(d or Fernet.generate_key()).decode("UTF-8")


def empacota(segredo: str, dado: dict) -> str:
    return decode(
        urlsafe_b64decode(
            Fernet(urlsafe_b64decode(segredo)).encrypt(
                dumps(dado).encode()
            )
        )
    )


async def realizar_login_ad(usuario: str, senha: str) -> Autenticado:
    if not usuario:
        return Autenticado(mensagem="Usuário não informado")
    if not senha:
        return Autenticado(mensagem="Senha não informada")

    try:
        segredo = [decode() for _ in range(2)]
        password = empacota(segredo[1], {"senha": senha})
        dado = empacota(segredo[0], {
            "login": usuario, "token": segredo[1], "pass": password
        })
        envio = {"data": dado, "secret": segredo[0]}
        return await patch_bapi_autenticador(envio)
    except Exception as e:
        return Autenticado(mensagem=str(e))


def isWindows() -> bool:
    return platform.system() == "Windows"


if __name__ == "__main__":
    if isWindows():
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()  # type:ignore
        )
    autenticado = asyncio.run(realizar_login_ad('login', 'senha'))
    print(autenticado)
