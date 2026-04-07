from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PrintRequestDTO:
    modo: str
    codigo: str
    copies: int
    printer_ip: Optional[str] = None
    template: Optional[str] = None
    produto_dados: Optional[dict] = None
    campos_extras: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PrintRequestDTO":
        modo = data.get("modo", "").lower()
        codigo = data.get("codigo", "").strip()
        
        try:
            copies = int(data.get("copies", 1))
            copies = max(1, min(copies, 100))
        except (ValueError, TypeError):
            copies = 1

        return cls(
            modo=modo,
            codigo=codigo,
            copies=copies,
            printer_ip=data.get("printer_ip"),
            template=data.get("template"),
            produto_dados=data.get("produto_dados"),
            campos_extras=data.get("campos_extras", {})
        )

    def is_valid(self) -> bool:
        if not self.modo or not self.codigo:
            return False
        return True
