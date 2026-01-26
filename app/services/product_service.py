from typing import Optional

class ProductService:
    def __init__(self, repo):
        self.repo = repo

    def find_product(self, codigo: str, modo: str) -> Optional[dict]:
        db = self.repo.get_db(modo)
        return self._consulta_base(codigo, db)

    def _consulta_base(self, codigo: str, db: dict) -> Optional[dict]:
        chave = ''.join(c for c in (codigo or "") if c.isdigit()).lstrip('0')

        rec = db.get(chave)
        if rec:
            return rec

        if len(chave) >= 2:
            f = f"{chave[:-1]}-{chave[-1]}"
            return db.get(f)

        return None

    def search(self, q: str, modo: str, limit: int = 10) -> list[dict]:
        q = (q or "").strip()
        if not q:
            return []

        limit = max(1, min(int(limit), 30))

        # 1) tenta match exato (ean/codprod normalizado)
        exact = self.find_product(q, modo)
        results = []
        seen = set()

        def add(rec: dict):
            key = (rec.get("codprod"), rec.get("ean"))
            if key in seen:
                return
            seen.add(key)
            results.append({
                "codprod": rec.get("codprod"),
                "ean": rec.get("ean"),
                "descricao": rec.get("descricao")
            })

        if exact:
            add(exact)
            if len(results) >= limit:
                return results

        # 2) busca por descrição (contains case-insensitive)
        qlow = q.lower()
        for rec in self.repo.get_records(modo):
            desc = (rec.get("descricao") or "")
            if qlow in desc.lower():
                add(rec)
                if len(results) >= limit:
                    break

        return results
