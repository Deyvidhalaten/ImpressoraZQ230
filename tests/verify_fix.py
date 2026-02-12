import os
os.environ["IMPORT_ONLY"] = "true"

import sys
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path("c:/Users/deyvid.silva/Documents/GitHub/ImpressoraZQ230")
sys.path.append(str(root_dir))

from app.services.product_service import load_db_flv_from, consulta_Base
from app.services.templates_service import criar_ambiente_zpl, render_zpl

def verify_flv_label():
    data_dir = root_dir / "app" / "seeds"
    # Ajuste para rodar onde seeds estão (na 'app/seeds' no repo ou 'data' no appdata)
    # Como estamos testando o codigo direto do repo, apontamos para app/seeds
    # Mas o load_db_flv_from espera que o arquivo esteja em data_dir/baseFLV_normalizada.csv
    
    print(f"Loading DB from {data_dir}...")
    db = load_db_flv_from(data_dir)
    print(f"DB loaded with {len(db)} entries.")
    
    # Teste com EAN do ABACATE (7204) - EAN curto (4 digitos)
    # Esperado: tipoean="B2", ean="000000007204" (padding 12)
    codigo = "7204"
    rec = consulta_Base(codigo, db)
    
    if not rec:
        print(f"Erro: Produto {codigo} nao encontrado.")
        return

    print(f"Produto encontrado: {rec['descricao']}")
    print(f"EAN Original: {rec['ean']}")

    # Simula a lógica da API corrigida (incluindo EAN)
    ean_raw = str(rec.get("ean") or "")
    ean_final = ean_raw
    tipoean = "BE"

    if len(ean_raw) < 13:
        tipoean = "B2"
        if len(ean_raw) < 12:
            ean_final = ean_raw.zfill(12)
            
    print(f"Tipo EAN Calculado: {tipoean}")
    print(f"EAN Final: {ean_final}")

    nutri_obj = rec.get("nutri") or {}
    nutri_list = [nutri_obj] if nutri_obj else []

    # Setup do ambiente ZPL
    templates_dir = root_dir / "app" / "zpl_templates"
    env = criar_ambiente_zpl(templates_dir)
    
    ctx = {
        "tipoean": tipoean,
        "modo": "flv",
        "texto": rec["descricao"][:27],
        "codprod": rec["codprod"],
        "ean": ean_final,
        "copies": 1,
        "ls": 0,
        "data": datetime.now().strftime("%d/%m/%Y"),
        "validade": rec.get("validade"),
        "infnutri": nutri_list,
        "nutri": nutri_obj,
    }

    print("Renderizando template...")
    try:
        zpl = render_zpl(env, "flv_default.zpl.j2", **ctx)
        print("ZPL Renderizado com sucesso!")
        print("-" * 40)
        
        # Check nutri check
        if "96" in zpl:
             print("CHECK NUTRI: OK")
        
        # Check EAN logic
        # Esperado: ^B2N,50,Y,N^FD000000007204^FS
        token_bar = f"^{tipoean}N,50,Y,N^FD{ean_final}^FS"
        if token_bar in zpl:
            print(f"CHECK BARCODE: OK ({token_bar})")
        else:
            print(f"CHECK BARCODE: FALHA. Esperado: {token_bar}")
            
        print(zpl)
        print("-" * 40)
    except Exception as e:
        print(f"Erro ao renderizar: {e}")

if __name__ == "__main__":
    verify_flv_label()
