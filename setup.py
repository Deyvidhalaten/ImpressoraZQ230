import ssl
import sys
import os
import glob
from cx_Freeze import setup, Executable

# Evita warnings SSL do Python\sssl._create_default_https_context = ssl._create_unverified_context

# Local das DLLs do pywin32
pywin32_system32 = os.path.join(
    sys.base_prefix, "Lib", "site-packages", "pywin32_system32"
)
win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll"))

# Arquivos e pastas a incluir na pasta build
includefiles = [
    ("templates", "templates"),
    ("static", "static"),
    ("baseFloricultura.csv", "baseFloricultura.csv"),
    ("baseFatiados.csv", "baseFatiados.csv"),
    ("printers.csv", "printers.csv"),
    ("printer_zq230.py", "printer_zq230.py"),
    (
        os.path.join(
            os.environ.get("WINDIR", "C:\\Windows"),
            "Fonts",
            "arial.ttf",
        ),
        "arial.ttf",
    ),
]
# Inclui DLLs do pywin32
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

build_exe_options = {
    "packages": [
        "flask", "jinja2", "urllib3",  # web framework
        "PIL",  # imagem
        "os", "sys", "socket", "csv", "fnmatch",  # sistema
    ],
    "includes": [
        "win32print", "win32ui", "win32con",  # pywin32
        "pywintypes", "pythoncom", "win32com",
        "printer_zq230",
    ],
    "include_files": includefiles,
    "include_msvcr": True,
}

# Se for Windows, rodar sem console
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="ImpressoraApp",
    version="1.0",
    description="App de Impressão de EAN-13 via Flask",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="app.py",
            base=base,
            target_name="ImpressoraApp.exe",
        )
    ]
)
