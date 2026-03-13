from app.__main__ import app
from app.repositories.printer_repository import load_printer_map_from
import json

with app.app_context():
    dirs = app.config['DIRS']
    printers = load_printer_map_from(dirs['data'])
    print("Found printers count:", len(printers))
    if len(printers) == 0:
        print("Empty printers array. Let's debug valid_modes")
        from app.repositories.printer_repository import _get_valid_modes_from_templates
        valid_modes = _get_valid_modes_from_templates(dirs['data'])
        print("valid_modes:", valid_modes)
