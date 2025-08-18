import csv
from pathlib import Path
from typing import List, Dict

def load_printer_map_from(data_dir: Path) -> List[Dict]:
    path = data_dir / "printers.csv"
    maps = []
    if not path.exists(): return maps
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            raw = row.get('funcao','').strip()
            funcs = [x.strip() for x in raw.split(';') if x.strip()]
            maps.append({
                'loja': row['loja'],
                'pattern': row['pattern'],
                'nome': row.get('nome','').strip(),
                'ip': row.get('ip',''),
                'funcao': funcs,
                'ls_flor': int(row.get('ls_flor', 0)),
                'ls_flv': int(row.get('ls_flv', 0)),
            })
    return maps

def save_printer_map_to(data_dir: Path, mappings):
    path = data_dir / "printers.csv"
    fieldnames = ['loja','pattern','nome','funcao','ip','ls_flor','ls_flv']
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader()
        for m in mappings:
            w.writerow({
                'loja': m.get('loja',''),
                'pattern': m.get('pattern',''),
                'nome': m.get('nome',''),
                'funcao': ';'.join(m.get('funcao') or []),
                'ip': m.get('ip',''),
                'ls_flor': m.get('ls_flor',0),
                'ls_flv': m.get('ls_flv',0),
            })
