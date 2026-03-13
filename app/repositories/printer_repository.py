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
        from app.services.log_service import log_error
        log_error("Aviso Migração", erro="A geração via CSV legado foi desativada. Exclua a pasta data para recriar o JSON puro ou cadastre impressoras no Admin Nível 2.")

    if not json_path.exists():
        return maps

    import json
    from app.services.log_service import log_error
    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Formato Hierárquico: Funcao -> Lojas -> Object { impressoras: [...] }
            # Precisamos 'achatar' (flatten) isso para os Controladores do Backend
            if not isinstance(data, dict):
                log_error("Erro Estrutura", erro="printers.json deve ser um dicionário hierárquico (Função -> Lojas).")
                return maps
            
            # Rastreador de impressoras únicas (usando IP como chave primária)
            printers_by_ip = {}
            
            for funcao, blocos_loja in data.items():
                if funcao not in valid_modes:
                    continue
                    
                lojas = blocos_loja.get("lojas", {})
                for codigo_loja, loja_info in lojas.items():
                    impressoras = loja_info.get("impressoras", [])
                    
                    for imp in impressoras:
                        ip = imp.get("ip")
                        if not ip: continue
                        
                        if ip not in printers_by_ip:
                            # Cria o modelo flatten baseado na primeira vez que vê ela
                            printers_by_ip[ip] = {
                                "loja": codigo_loja,
                                "pattern": imp.get("pattern", f"10.{int(codigo_loja)}.*" if codigo_loja.isdigit() else "*"),
                                "nome": imp.get("nome", ""),
                                "ip": ip,
                                "funcao": set(),
                                "ls": {}
                            }
                        
                        # Adiciona a função
                        printers_by_ip[ip]["funcao"].add(funcao)
                        
                        # Registra o Limit Switch específico desta função caso exista
                        if "ls" in imp:
                            printers_by_ip[ip]["ls"][funcao] = imp["ls"]

            # Converte a estrutura achatada para a lista esperada
            for ip, p in printers_by_ip.items():
                p["funcao"] = list(p["funcao"])  # set para list
                maps.append(p)
                
    except json.JSONDecodeError as e:
        log_error("Erro JSON", erro=f"O arquivo printers.json está corrompido ou mal formatado. A lista será retornada vazia. Erro: {e}")
    except Exception as e:
        log_error("Erro Leitura", erro=f"Falha inesperada ao ler a hierarquia printers.json: {e}")

    return maps


def save_printer_map_to(data_dir: Optional[Path], flat_mappings: List[Dict]):
    """Salva a lista achadada de mapeamentos convertendo-a devolta para a Hierarquia Função -> Loja"""
    data_dir = _resolve_data_dir(data_dir)
    json_path = data_dir / "printers.json"
    
    hierarquia = {}
    
    for printer in flat_mappings:
        loja = printer.get("loja", "")
        if not loja: continue
            
        funcoes = printer.get("funcao", [])
        
        for funcao in funcoes:
            if funcao not in hierarquia:
                hierarquia[funcao] = {"lojas": {}}
                
            if loja not in hierarquia[funcao]["lojas"]:
                hierarquia[funcao]["lojas"][loja] = {"impressoras": []}
                
            # O limit switch no modelo hierárquico é um número simples embaixo da impressora
            # Mapeado a partir do dicionário de "ls" no flat model
            ls_value = printer.get("ls", {}).get(funcao, 0)
            
            hierarquia[funcao]["lojas"][loja]["impressoras"].append({
                "nome": printer.get("nome", ""),
                "ip": printer.get("ip", ""),
                "pattern": printer.get("pattern", f"10.{int(loja)}.*" if str(loja).isdigit() else "*"),
                "ls": ls_value
            })

    import json
    from app.services.log_service import log_error
    try:
        with json_path.open('w', encoding='utf-8') as f:
            json.dump(hierarquia, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log_error("Erro Escrita", erro=f"Falha ao salvar modificações hierárquicas no printers.json: {e}")


# Aliases de compatibilidade
def load_printer_map():
    return load_printer_map_from(None)


def save_printer_map(mappings):
    return save_printer_map_to(None, mappings)