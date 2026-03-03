from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class PrinterResponseDTO:
    ip: str
    nome: str
    funcao: List[str]
    ls: Dict[str, int]

@dataclass
class ModosResponseDTO:
    key: str
    label: str

@dataclass
class ContextResponseDTO:
    loja: str
    test_mode: bool
    printers: List[PrinterResponseDTO]
    modos: List[ModosResponseDTO]
    ls: Dict[str, int]

    def to_dict(self) -> dict:
        return {
            "loja": self.loja,
            "printers": [
                {
                    "ip": p.ip,
                    "nome": p.nome,
                    "funcao": p.funcao,
                    "ls": p.ls
                } for p in self.printers
            ],
            "modos": [{"key": m.key, "label": m.label} for m in self.modos],
            "ls": self.ls,
            "test_mode": self.test_mode
        }
