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
