from pathlib import Path
from app.bootstrap import get_appdata_root
from app.services.templates_service import listar_templates_por_modo

zpl_dir = get_appdata_root() / "zpl_templates"
print(f"Buscando em: {zpl_dir}")

modos = listar_templates_por_modo(zpl_dir)
print("\nModos extraídos:")
for m, files in modos.items():
    print(f"Modo '{m}' -> {files}")
