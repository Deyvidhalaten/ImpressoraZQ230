import csv, re, json as _json
from typing import Optional
from pathlib import Path

def load_db_flor_from(data_dir: Path):
    path = data_dir / "baseFloricultura.csv"
    db = {}
    if not path.exists(): return db
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ean = row['EAN-13'].strip()
            desc = row['Descricao'].strip()
            cod  = row['Cod.Prod'].strip()
            db[ean] = {'ean': ean, 'descricao': desc, 'codprod': cod}
            db[cod] = {'ean': ean, 'descricao': desc, 'codprod': cod}
    return db

def load_db_flv_from(data_dir: Path):
    path = data_dir / "baseFatiados.csv"
    db = {}
    if not path.exists(): return db
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ean = (row.get('EAN-13') or '').strip()
            desc= (row.get('Descricao') or '').strip()
            cod = (row.get('Cod.Prod') or '').strip()
            valr= (row.get('Validade') or '').strip()
            info= (row.get('Info.nutricional') or '').strip()
            if not ean or not cod: continue
            try: validade = int(valr)
            except: validade = None
            if info.startswith('"[') and info.endswith(']"'): info_json = info[1:-1]
            else: info_json = info
            info_json = re.sub(r',\s*\]$', ']', info_json)
            try:
                lst = _json.loads(info_json)
                if not isinstance(lst, list): lst = [lst]
            except: lst = [info_json]
            rec = {'ean': ean, 'descricao': desc, 'codprod': cod, 'validade': validade, 'info_nutri': lst}
            db[ean] = rec; db[cod] = rec
    return db

def consulta_Base(codigo: str, db: dict) -> Optional[dict]:
    chave = ''.join(c for c in codigo if c.isdigit()).lstrip('0')
    rec = db.get(chave)
    if rec: return rec
    if len(chave) >= 2:
        f = f"{chave[:-1]}-{chave[-1]}"
        rec = db.get(f)
        if rec: return rec
    return None


def busca_por_descricao(termo: str, db: dict, limite: int = 10) -> list:
    """Busca produtos cuja descrição contenha o termo."""
    if not termo or len(termo) < 2:
        return []
    
    termo_lower = termo.lower()
    resultados = []
    vistos = set()
    
    for key, rec in db.items():
        codprod = rec.get('codprod', '')
        if codprod in vistos:
            continue
        
        descricao = rec.get('descricao', '').lower()
        if termo_lower in descricao:
            resultados.append(rec)
            vistos.add(codprod)
            if len(resultados) >= limite:
                break
    
    return resultados
