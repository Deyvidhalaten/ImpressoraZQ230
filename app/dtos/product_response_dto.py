from dataclasses import dataclass
from typing import Optional

@dataclass
class ProductResponseDTO:
    codprod: str
    ean: str
    descricao: str
    validade: Optional[int] = None
    full_data: dict = None

    def to_dict(self) -> dict:
        return {
            "codprod": self.codprod,
            "ean": self.ean,
            "descricao": self.descricao,
            "validade": self.validade,
            "full_data": self.full_data # Isso vai para o JS
        }
class RespostaAPI:
    def __init__(self, sucesso: bool, status: int, dados: dict = None, erro: str = None):
        self.sucesso = sucesso
        self.status = status
        self.dados = dados or {}
        self.erro = erro
