from typing import Optional

class ProductService:
    def __init__(self, repository):
        self.repository = repository

    def find_product(self, codigo: str, modo: str) -> Optional[dict]:
        db = self.repository.get_db(modo)
        return self._consulta_base(codigo, db)

    def _consulta_base(self, codigo: str, db: dict) -> Optional[dict]:
        chave = ''.join(c for c in codigo if c.isdigit()).lstrip('0')

        rec = db.get(chave)
        if rec:
            return rec

        if len(chave) >= 2:
            f = f"{chave[:-1]}-{chave[-1]}"
            return db.get(f)

        return None
