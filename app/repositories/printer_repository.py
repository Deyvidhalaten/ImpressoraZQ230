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
        from app.bootstrap import get_appdata_root
        return get_appdata_root() / "data"


def _get_valid_modes_from_templates(data_dir: Path) -> set:
    """
    Retorna o conjunto de modos válidos usando o serviço de templates unificado.
    """
    from app.services.templates_service import list_templates_by_mode
    
    # Dependendo de como dirs estão definidos, o zpl_templates fica geralmente no mesmo nível que 'data' ou em ProgramData.
    try:
        from flask import current_app
        templates_dir = current_app.config["DIRS"]["templates"]
    except Exception:
        templates_dir = data_dir.parent / "zpl_templates"
        
    modos = list_templates_by_mode(templates_dir)
    return set(modos.keys())


def load_printer_map_from(data_dir: Optional[Path] = None) -> List[Dict]:
    """
    Lê o arquivo printers.json. Se não existir, migra de printers.csv.
    Normaliza a chave 'ls' para ser um dict.
    """
    data_dir = _resolve_data_dir(data_dir)
    json_path = data_dir / "printers.json"
    csv_path = data_dir / "printers.csv"
    maps: List[Dict] = []

    valid_modes = _get_valid_modes_from_templates(data_dir)

    if not json_path.exists() and csv_path.exists():
        import csv
        from app.services.log_service import log_error
        try:
            with csv_path.open(newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    raw_func = (row.get('funcao') or '').strip()
                    funcs = [x.strip().lower() for x in raw_func.split(';') if x.strip()]
                    funcs_validas = [f for f in funcs if f in valid_modes] or funcs
                    
                    maps.append({
                        'loja': str(row.get('loja', '')).strip(),
                        'pattern': str(row.get('pattern', '')).strip(),
                        'nome': (row.get('nome') or '').strip(),
                        'ip': (row.get('ip') or '').strip(),
                        'funcao': funcs_validas,
                        'ls': {
                            'floricultura': int(row.get('ls_flor', 0) or 0),
                            'flv': int(row.get('ls_flv', 0) or 0),
                        }
                    })
            save_printer_map_to(data_dir, maps)
            return maps
        except Exception as e:
            log_error("Erro Migração CSV", erro=f"Falha ao tentar converter o CSV antigo para o novo formato JSON: {e}")

    if not json_path.exists():
        return maps

    import json
    from app.services.log_service import log_error
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            
            if not isinstance(data, list):
                log_error("Erro Estrutura", erro="printers.json não contém uma lista válida.")
                return maps
                
            for item in data:
                if not isinstance(item, dict):
                    continue
                    
                if 'ls' not in item or not isinstance(item['ls'], dict):
                    item['ls'] = {}
                    
                if 'ls_flor' in item and 'floricultura' not in item['ls']:
                    item['ls']['floricultura'] = item.pop('ls_flor', 0)
                if 'ls_flv' in item and 'flv' not in item['ls']:
                    item['ls']['flv'] = item.pop('ls_flv', 0)
                    
                funcs = item.get('funcao', [])
                if isinstance(funcs, str):
                    funcs = [x.strip().lower() for x in funcs.split(';') if x.strip()]
                item['funcao'] = [f for f in funcs if f in valid_modes] or funcs
                
                maps.append(item)
    except json.JSONDecodeError as e:
        log_error("Erro JSON", erro=f"O arquivo printers.json está corrompido ou mal formatado. O sistema usará uma lista vazia. Erro: {e}")
    except Exception as e:
        log_error("Erro Leitura", erro=f"Falha inesperada ao ler printers.json: {e}")

    return maps


def save_printer_map_to(data_dir: Optional[Path], mappings):
    """Salva o mapeamento de impressoras em printers.json."""
    data_dir = _resolve_data_dir(data_dir)
    json_path = data_dir / "printers.json"
    
    import json
    from app.services.log_service import log_error
    try:
        with json_path.open('w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log_error("Erro Escrita", erro=f"Falha ao salvar modificações no printers.json: {e}")


# Aliases de compatibilidade
def load_printer_map():
    return load_printer_map_from(None)


def save_printer_map(mappings):
    return save_printer_map_to(None, mappings)