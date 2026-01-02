import csv, re, json as _json
from pathlib import Path

class ProductRepository:
    def __init__(self, data_dir: Path):
        self.db_flor = self._load_db_flor(data_dir)
        self.db_flv  = self._load_db_flv(data_dir)

    def _load_db_flor(self, data_dir: Path):
        path = data_dir / "baseFloricultura.csv"
        db = {}
        if not path.exists():
            return db

        with path.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                ean  = row['EAN-13'].strip()
                desc = row['Descricao'].strip()
                cod  = row['Cod.Prod'].strip()
                rec = {'ean': ean, 'descricao': desc, 'codprod': cod}
                db[ean] = rec
                db[cod] = rec
        return db

    def _load_db_flv(self, data_dir: Path):
        path = data_dir / "baseFatiados.csv"
        db = {}
        if not path.exists():
            return db

        with path.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                ean  = (row.get('EAN-13') or '').strip()
                desc = (row.get('Descricao') or '').strip()
                cod  = (row.get('Cod.Prod') or '').strip()
                valr = (row.get('Validade') or '').strip()
                info = (row.get('Info.nutricional') or '').strip()

                if not ean or not cod:
                    continue

                try:
                    validade = int(valr)
                except:
                    validade = None

                if info.startswith('"[') and info.endswith(']"'):
                    info_json = info[1:-1]
                else:
                    info_json = info

                info_json = re.sub(r',\s*\]$', ']', info_json)

                try:
                    lst = _json.loads(info_json)
                    if not isinstance(lst, list):
                        lst = [lst]
                except:
                    lst = [info_json]

                rec = {
                    'ean': ean,
                    'descricao': desc,
                    'codprod': cod,
                    'validade': validade,
                    'info_nutri': lst
                }

                db[ean] = rec
                db[cod] = rec

        return db

    def get_db(self, modo: str):
        return self.db_flv if modo.lower() == "flv" else self.db_flor
