from typing import Optional
from app.repositories.product_repository import load_db_flor_from, load_db_flv_from, key_variants, only_digits


# ------------------------------------------------------------
# CONSULTA
# ------------------------------------------------------------
def consulta_Base(codigo: str, db: dict) -> Optional[dict]:
    """
    Consulta por:
    - input puro (se já estiver igual)
    - só dígitos
    - tenta também "7927-5"
    """
    raw = (codigo or "").strip()
    if not raw:
        return None

    rec = db.get(raw)
    if rec:
        return rec

    chave = only_digits(raw)
    if chave:
        rec = db.get(chave)
        if rec:
            return rec

        if len(chave) >= 2:
            f = f"{chave[:-1]}-{chave[-1]}"
            rec = db.get(f)
            if rec:
                return rec

    return None


def busca_por_descricao(termo: str, db: dict, limite: int = 50) -> list:
    """Busca produtos cuja descrição corresponda ao termo (suporta % como wildcard)."""
    if not termo or len(termo) < 2:
        return []
    
    # Escapa caracteres especiais de regex, exceto %
    # Primeiro escapa tudo, depois desfaz o escape do % (que virou \%) para substituir por .*
    import re
    
    # Abordagem simplificada:
    # 1. split por %
    # 2. escape de cada parte
    # 3. join com .*
    parts = termo.split('%')
    parts = [re.escape(p) for p in parts]
    pattern_str = '^' + '.*'.join(parts)
    
    try:
        pattern = re.compile(pattern_str, re.IGNORECASE)
    except re.error:
        return []

    resultados = []
    vistos = set()
    
    for key, rec in db.items():
        codprod = rec.get('codprod', '')
        if codprod in vistos:
            continue
        
        descricao = rec.get('descricao', '')
        if pattern.search(descricao):
            resultados.append(rec)
            vistos.add(codprod)
            if len(resultados) >= limite:
                break
    
    return resultados
