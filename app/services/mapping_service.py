import csv
from pathlib import Path
from typing import List, Dict, Optional

def _resolve_data_dir(data_dir: Optional[Path]) -> Path:
    if data_dir is not None:
        return data_dir
    # tenta pegar do Flask se existir
    try:
        from flask import current_app
        return current_app.config["DIRS"]["data"]
    except Exception:
        # último recurso: ProgramData padrão
        from app.bootstrap import get_programdata_root
        return get_programdata_root() / "data"

def load_printer_map_from(data_dir: Optional[Path] = None) -> List[Dict]:
    data_dir = _resolve_data_dir(data_dir)
    path = data_dir / "printers.csv"
    maps: List[Dict] = []
    if not path.exists():
        return maps
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            raw = (row.get('funcao') or '').strip()
            funcs = [x.strip() for x in raw.split(';') if x.strip()]
            maps.append({
                'loja': row.get('loja',''),
                'pattern': row.get('pattern',''),
                'nome': (row.get('nome') or '').strip(),
                'ip': row.get('ip',''),
                'funcao': funcs,
                'ls_flor': int(row.get('ls_flor', 0) or 0),
                'ls_flv':  int(row.get('ls_flv',  0) or 0),
            })
    return maps

def save_printer_map_to(data_dir: Optional[Path], mappings):
    data_dir = _resolve_data_dir(data_dir)
    path = data_dir / "printers.csv"
    fieldnames = ['loja','pattern','nome','funcao','ip','ls_flor','ls_flv']
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for m in mappings:
            w.writerow({
                'loja':    m.get('loja',''),
                'pattern': m.get('pattern',''),
                'nome':    m.get('nome',''),
                'funcao':  ';'.join(m.get('funcao') or []),
                'ip':      m.get('ip',''),
                'ls_flor': m.get('ls_flor',0),
                'ls_flv':  m.get('ls_flv',0),
            })

# Aliases de compatibilidade (se alguém importar nomes antigos)
def load_printer_map():
    return load_printer_map_from(None)

def save_printer_map(mappings):
    return save_printer_map_to(None, mappings)
