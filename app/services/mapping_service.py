import csv
from pathlib import Path
from typing import List, Dict, Optional

def _resolve_data_dir(data_dir: Optional[Path]) -> Path:
    """Retorna o diretório de dados, tentando detectar o ProgramData automaticamente."""
    if data_dir is not None:
        return data_dir
    try:
        from flask import current_app
        return current_app.config["DIRS"]["data"]
    except Exception:
        from app.bootstrap import get_programdata_root
        return get_programdata_root() / "data"


def _get_valid_modes_from_templates(data_dir: Path) -> set:
    """
    Retorna o conjunto de modos válidos a partir da pasta de templates ZPL.
    Cada arquivo .zpl.j2 é interpretado em múltiplos níveis:
      - até o primeiro '_' (modo base)
      - até o penúltimo '_' (modo composto)
    Ex: 'estoque_padaria_default.zpl.j2' -> {'estoque', 'estoque_padaria'}
    """
    zpl_dir = data_dir.parent / "zpl_templates"
    if not zpl_dir.exists():
        return set()

    valid_modes = set()
    for f in zpl_dir.iterdir():
        if f.is_file() and f.suffixes[-2:] == ['.zpl', '.j2']:
            nome = f.stem.lower()  # sem extensões -> estoque_padaria_default
            partes = nome.split('_')

            if partes:
                valid_modes.add(partes[0])  # modo base

            # adiciona variações compostas até o penúltimo underline
            if len(partes) > 2:
                valid_modes.add('_'.join(partes[:-1]))

    return valid_modes


def load_printer_map_from(data_dir: Optional[Path] = None) -> List[Dict]:
    """
    Lê o arquivo printers.csv e retorna uma lista de dicionários normalizados.
    - Normaliza campos de texto (strip, lowercase quando aplicável)
    - Converte LS em int
    - Filtra 'funcao' com base nos templates válidos em zpl_templates
    """
    data_dir = _resolve_data_dir(data_dir)
    path = data_dir / "printers.csv"
    maps: List[Dict] = []

    if not path.exists():
        return maps

    valid_modes = _get_valid_modes_from_templates(data_dir)

    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            # Extrai e normaliza lista de funções
            raw_func = (row.get('funcao') or '').strip()
            funcs = [x.strip().lower() for x in raw_func.split(';') if x.strip()]

            # Mantém apenas as funções válidas conforme templates
            funcs_validas = [f for f in funcs if f in valid_modes] or funcs

            maps.append({
                'loja': str(row.get('loja', '')).strip(),
                'pattern': str(row.get('pattern', '')).strip(),
                'nome': (row.get('nome') or '').strip(),
                'ip': (row.get('ip') or '').strip(),
                'funcao': funcs_validas,
                'ls_flor': int(row.get('ls_flor', 0) or 0),
                'ls_flv': int(row.get('ls_flv', 0) or 0),
            })

    return maps


def save_printer_map_to(data_dir: Optional[Path], mappings):
    """Salva o mapeamento de impressoras em printers.csv (sobrescreve o arquivo)."""
    data_dir = _resolve_data_dir(data_dir)
    path = data_dir / "printers.csv"
    fieldnames = ['loja', 'pattern', 'nome', 'funcao', 'ip', 'ls_flor', 'ls_flv']

    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for m in mappings:
            funcs = m.get('funcao') or []
            if isinstance(funcs, list):
                funcao_str = ';'.join(sorted(set(funcs)))  # remove duplicados
            else:
                funcao_str = str(funcs)
            w.writerow({
                'loja': m.get('loja', ''),
                'pattern': m.get('pattern', ''),
                'nome': m.get('nome', ''),
                'funcao': funcao_str,
                'ip': m.get('ip', ''),
                'ls_flor': m.get('ls_flor', 0),
                'ls_flv': m.get('ls_flv', 0),
            })


# Aliases de compatibilidade
def load_printer_map():
    return load_printer_map_from(None)

def save_printer_map(mappings):
    return save_printer_map_to(None, mappings)