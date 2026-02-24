import json
from pathlib import Path
from app.bootstrap import get_appdata_root
from app.services.mapping_service import load_printer_map_from

data_dir = get_appdata_root() / "data"
print(f"Data Dir: {data_dir}")
print(f"CSV exists: {(data_dir / 'printers.csv').exists()}")
print(f"JSON exists: {(data_dir / 'printers.json').exists()}")

try:
    mappings = load_printer_map_from(data_dir)
    print("Mappings Loaded:")
    print(json.dumps(mappings, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
