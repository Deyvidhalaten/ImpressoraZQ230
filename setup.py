import ssl
import sys, os, glob
from cx_Freeze import setup, Executable

ssl._create_default_https_context = ssl._create_unverified_context
# local do pywin32 DLLs
pywin32_system32 = os.path.join(
    sys.base_prefix, "Lib", "site-packages", "pywin32_system32"
)
win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll"))

# arquivos a incluir na pasta build
includefiles = [
    ("templates", "templates"),
    ("static",   "static"),
    ("baseFloricultura.csv", "baseFloricultura.csv"),
    ("printers.csv",           "printers.csv"),
    # módulo ZPL
    ("printer_zq230.py",      "printer_zq230.py"),
    # fonte Arial
    (os.path.join(os.environ["WINDIR"], "Fonts", "arial.ttf"), "arial.ttf"),
]
# inclui DLLs do pywin32
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

build_exe_options = {
    "packages": [
        "flask", "jinja2",
        "requests", "urllib3",
        # PIL (Pillow)
        "PIL", 
        # módulos de sistema
        "os", "sys", "socket", "tempfile", "csv", "fnmatch"
    ],
    "includes": [
        # pywin32
        "win32print", "win32ui", "win32con",
        "pywintypes", "pythoncom", "win32com",
        # nosso módulo de ZPL
        "printer_zq230"
    ],
    "include_files": includefiles,
    "include_msvcr": True,
}

base = None
if sys.platform == "win32":
    # modo sem console
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
            target_name="ImpressoraApp.exe"
        )
    ]
)
