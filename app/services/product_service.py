import csv
from typing import Optional
from pathlib import Path


# ------------------------------------------------------------
# Helpers de normalização e chaves
# ------------------------------------------------------------
def only_digits(s: str) -> str:
    return ''.join(c for c in (s or "") if c.isdigit()).lstrip('0')


def key_variants(ean: str, cod: str):
    """
    Indexa várias formas pra consulta funcionar com:
    - código com hífen: 7927-5
    - código sem hífen: 79275
    - só dígitos
    - ean puro
    """
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
    """
    Aceita '1,2' ou '1.2' ou vazio.
    Retorna float ou None.
    """
    s = (s or "").strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return None


def parse_int(s: str, default=None):
    s = (s or "").strip()
    if not s:
        return default
    try:
        return int(float(s.replace(",", ".")))
    except:
        return default


# ------------------------------------------------------------
# LOAD FLORICULTURA
# ------------------------------------------------------------
def load_db_flor_from(data_dir: Path):
    path = data_dir / "baseFloricultura.csv"
    db = {}
    if not path.exists():
        return db

    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ean = (row.get("EAN-13") or "").strip()
            desc = (row.get("Descricao") or "").strip()
            cod = (row.get("Cod.Prod") or "").strip()

            if not ean or not cod:
                continue

            rec = {
                "ean": ean,
                "descricao": desc,
                "codprod": cod,
                "validade": None,
                "nutri": None,
            }

            for k in key_variants(ean, cod):
                db[k] = rec

    return db


# ------------------------------------------------------------
# LOAD FLV (BASE NOVA NORMALIZADA)
# Arquivo: baseFLV_normalizada.csv
# colunas:
# EAN-13;Descricao;Cod.Prod;Validade;Porcao;Kcal;Carboidratos;Proteinas;GordurasTotais;
# GordurasSaturadas;GordurasTrans;Colesterol;Fibra;Calcio;Ferro;Sodio
# ------------------------------------------------------------
def load_db_flv_from(data_dir: Path):
    path = data_dir / "baseFLV_normalizada.csv"
    db = {}
    if not path.exists():
        return db

    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ean = (row.get("EAN-13") or "").strip()
            desc = (row.get("Descricao") or "").strip()
            cod = (row.get("Cod.Prod") or "").strip()

            if not ean or not cod:
                continue

            validade = parse_int(row.get("Validade"), default=0)
            porcao = parse_int(row.get("Porcao"), default=100)

            nutri = {
                "porcao": porcao,
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

            rec = {
                "ean": ean,
                "descricao": desc,
                "codprod": cod,
                "validade": validade,
                "nutri": nutri,
            }

            for k in key_variants(ean, cod):
                db[k] = rec

    return db


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
