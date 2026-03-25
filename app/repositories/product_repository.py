import csv
from pathlib import Path
from typing import Optional

from app.dtos.product_response_dto import RespostaAPI

def only_digits(s: str) -> str:
    return ''.join(c for c in (s or "") if c.isdigit()).lstrip('0')

def key_variants(ean: str, cod: str):
    keys = set()
    if ean:
        e = ean.strip()
        keys.add(e)
        keys.add(only_digits(e))
    if cod:
        c = cod.strip()
        keys.add(c)
        keys.add(c.replace("-", ""))
        keys.add(only_digits(c))
        d = only_digits(c)
        if len(d) >= 2:
            keys.add(f"{d[:-1]}-{d[-1]}")
    return keys

def parse_num(s: str):
    s = (s or "").strip()
    if not s: return None
    s = s.replace(",", ".")
    try: return float(s)
    except Exception: return None

def parse_int(s: str, default=None):
    s = (s or "").strip()
    if not s: return default
    try: return int(float(s.replace(",", ".")))
    except Exception: return default

def load_db_flor_from(data_dir: Path):
    path = data_dir / "baseFloricultura.csv"
    db = {}
    if not path.exists(): return db

    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ean = (row.get("EAN-13") or "").strip()
            desc = (row.get("Descricao") or "").strip()
            cod = (row.get("Cod.Prod") or "").strip()
            if not ean or not cod: continue

            rec = {
                "ean": ean, "descricao": desc,
                "codprod": cod, "validade": None, "nutri": None,
            }
            for k in key_variants(ean, cod):
                db[k] = rec
    return db

def load_db_flv_from(data_dir: Path):
    path = data_dir / "baseFLV_normalizada.csv"
    db = {}
    if not path.exists(): return db

    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ean = (row.get("EAN-13") or "").strip()
            desc = (row.get("Descricao") or "").strip()
            cod = (row.get("Cod.Prod") or "").strip()
            if not ean or not cod: continue

            rec = {
                "ean": ean, "descricao": desc, "codprod": cod,
                "validade": parse_int(row.get("Validade"), default=0),
                "nutri": {
                    "porcao": parse_int(row.get("Porcao"), default=100),
                    "kcal": parse_num(row.get("Kcal")),
                    "carb": parse_num(row.get("Carboidratos")),
                    "prot": parse_num(row.get("Proteinas")),
                    "gord": parse_num(row.get("GordurasTotais")),
                    "sat": parse_num(row.get("GordurasSaturadas")),
                    "trans": parse_num(row.get("GordurasTrans")),
                    "colesterol": parse_num(row.get("Colesterol")),
                    "fibra": parse_num(row.get("Fibra")),
                    "calcio": parse_num(row.get("Calcio")),
                    "ferro": parse_num(row.get("Ferro")),
                    "sodio_mg": parse_num(row.get("Sodio")),
                }
            }
            for k in key_variants(ean, cod):
                db[k] = rec
    return db

import aiohttp
from aiohttp import ClientSession, TCPConnector
# from app.dtos.resposta_api import RespostaAPI

class ProductRepository:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
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
                url = f"{self.base_url}/produtos/consultar" 
                
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
