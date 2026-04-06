import os, shutil
from pathlib import Path

def get_appdata_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or Path.home()
    return Path(base) / "BistekPrinter"

def _copy_if_missing(src: Path, dst: Path):
    if src.is_file() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def init_data_layout(repo_base_dir: str) -> dict:
    root = get_appdata_root()
    dirs = {
        "root": root,
        "config": root / "config",
        "templates": root / "zpl_templates",
        "fonts": root / "static" / "fonts",
        "logs": root / "logs",
        "data": root / "data",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)

    # Settings padrão (modo teste desligado)
    settings_file = dirs["config"] / "settings.txt"
    if not settings_file.exists():
        settings_file.write_text("impressora_teste=0\n", encoding="utf-8")

    # Templates
    repo_tpl = Path(repo_base_dir) / "zpl_templates"
    if not any(dirs["templates"].glob("*.zpl.j2")) and repo_tpl.is_dir():
        for f in repo_tpl.glob("*.zpl.j2"):
            _copy_if_missing(f, dirs["templates"] / f.name)

    # Seeds JSON base construído a partir de curinga genérico
    printers_json = dirs["data"] / "printers.json"
    if not printers_json.exists():
        import json
        
        raw_csv_lines = [
            "2,10.2.*,Mataburro,Floricultura;FLV,10.2.30.109,50,-100",
            "3,10.3.*,Mataburro,Floricultura;FLV,10.3.30.110,0,-50",
            "4,10.4.*,Retaguarda-Mataburro,Floricultura;FLV,10.4.30.116,50,-100",
            "5,10.5.*,Mataburro,Floricultura;FLV,10.5.30.111,60,-60",
            "6,10.6.*,Mataburro,Floricultura;FLV,10.6.30.119,0,0",
            "7,10.7.*,Mataburro,Floricultura;FLV,10.7.30.140,0,0",
            "8,10.8.*,Mataburro,Floricultura;FLV,10.8.30.104,0,0",
            "8,10.8.*,Mataburro,Floricultura;FLV,10.8.30.105,0,0",
            "8,10.8.*,Mataburro,Floricultura;FLV,10.8.30.106,0,0",
            "8,10.8.*,Mataburro,Floricultura;FLV,10.8.30.110,0,0",
            "9,10.9.*,Mata Burro,Floricultura;FLV;Estoque Padaria,10.9.30.127,50,-80",
            "10,10.10.*,Mataburro,Floricultura;FLV,10.10.30.150,0,0",
            "11,10.11.*,Mataburro,Floricultura;FLV,10.11.30.129,0,0",
            "12,10.12.*,Mataburro,Floricultura;FLV,10.12.30.118,0,0",
            "14,10.14.*,Mataburro,Floricultura;FLV,10.14.30.102,0,0",
            "15,10.15.*,Mataburro,Floricultura;FLV,10.15.30.228,0,0",
            "15,10.15.*,Mataburro,Floricultura;FLV,10.15.30.204,0,0",
            "16,10.16.*,Mataburro,Floricultura;FLV,10.16.30.67,0,0",
            "17,10.17.*,Mataburro,Floricultura;FLV,10.17.30.118,50,-120",
            "17,10.17.*,Frente de Caixa,Floricultura;FLV;Estoque Padaria,10.17.30.119,50,-80",
            "18,10.18.*,Mataburro,Floricultura;FLV,10.18.30.127,0,0",
            "19,10.19.*,Mataburro,Floricultura;FLV,,0,0",
            "20,10.20.*,Mataburro,Floricultura;FLV,,0,0",
            "22,10.22.*,Mataburro,Floricultura;FLV,10.22.30.106,0,0",
            "23,10.23.*,Mataburro,Floricultura;FLV,10.23.30.119,0,0",
            "24,10.24.*,Mataburro,Floricultura;FLV,10.24.30.127,0,0",
            "25,10.25.*,Mataburro,Floricultura;FLV,10.25.30.158,0,0",
            "25,10.25.*,Mataburro,Floricultura;FLV,10.25.30.159,0,0",
            "26,10.26.*,Mataburro,Floricultura;FLV,10.26.30.108,0,0",
            "27,10.27.*,Mataburro,Floricultura;FLV,10.27.30.108,0,0",
            "29,10.29.*,Mataburro,Floricultura;FLV,10.29.30.103,0,0",
            "30,10.30.*,Mataburro,Floricultura;FLV,10.30.30.119,0,0",
            "30,11.30.*,Mataburro,Floricultura;FLV,10.30.30.118,0,0",
            "31,12.31.*,Mataburro,Floricultura;FLV,10.31.30.108,0,0",
            "32,13.32.*,Mataburro,Floricultura;FLV,10.32.30.108,0,0",
            "33,14.33.*,Mataburro,Floricultura;FLV,10.33.30.108,0,0",
            "8249,10.24.*,Mataburro,Floricultura;FLV,10.24.30.126,0,0"
        ]
        
        base_hierarquica = {}
        for linha in raw_csv_lines:
            cols = linha.split(",")
            loja = cols[0].strip()
            pattern = cols[1].strip()
            nome = cols[2].strip()
            funcoes = cols[3].strip().split(";")
            ip = cols[4].strip()
            ls_flor = int(cols[5].strip()) if len(cols) > 5 and cols[5].strip() else 0
            ls_flv = int(cols[6].strip())  if len(cols) > 6 and cols[6].strip() else 0
            
            for f_raw in funcoes:
                f_key = f_raw.strip().lower()
                if not f_key: continue
                
                ls_val = 0
                if "flor" in f_key:
                    ls_val = ls_flor
                    f_key = "floricultura"
                elif "flv" in f_key:
                    ls_val = ls_flv
                    f_key = "flv"
                    
                if f_key not in base_hierarquica:
                    base_hierarquica[f_key] = {"lojas": {}}
                    
                if loja not in base_hierarquica[f_key]["lojas"]:
                    base_hierarquica[f_key]["lojas"][loja] = {"impressoras": []}
                    
                base_hierarquica[f_key]["lojas"][loja]["impressoras"].append({
                    "nome": nome,
                    "ip": ip,
                    "pattern": pattern,
                    "ls": ls_val
                })
        
        # Gravar template no JSON
        with printers_json.open('w', encoding='utf-8') as f:
             json.dump(base_hierarquica, f, indent=4, ensure_ascii=False)

    return dirs

