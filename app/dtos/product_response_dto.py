from dataclasses import dataclass
from typing import Optional

@dataclass
class ProductResponseDTO:
    codprod: str
    ean: str
    descricao: str
    validade: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "codprod": self.codprod,
            "ean": self.ean,
            "descricao": self.descricao,
            "validade": self.validade
        }
class RespostaAPI:
    def __init__(self, sucesso: bool, status: int, dados: dict = None, erro: str = None):
        self.sucesso = sucesso
        self.status = status
        self.dados = dados or {}
        self.erro = erro
