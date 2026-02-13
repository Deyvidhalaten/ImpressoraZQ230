import sys
import os
import glob
import ssl
from cx_Freeze import setup, Executable

# -------------------------------------------------------------------
# (apenas para build / download de dependências)
# -------------------------------------------------------------------
ssl._create_default_https_context = ssl._create_unverified_context

# -------------------------------------------------------------------
# Localiza DLLs do PyWin32 (OBRIGATÓRIO para impressão no Windows)
# -------------------------------------------------------------------
pywin32_system32 = os.path.join(
    sys.base_prefix,
    "Lib",
    "site-packages",
    "pywin32_system32"
)

win32_dlls = []
if os.path.isdir(pywin32_system32):
    win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll"))

# -------------------------------------------------------------------
# Arquivos adicionais do projeto
# -------------------------------------------------------------------
includefiles = [
    ("app/static", "app/static"),
    ("app/templates", "app/templates"),
    ("app/zpl_templates", "app/zpl_templates"),
    ("app/seeds", "app/seeds"),
    ("app/routes", "app/routes"),
    ("app/services", "app/services"),
    ("app/printer_zq230.py", "app/printer_zq230.py"),
    ("frontend", "frontend"),
]

# DLLs do pywin32
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

# -------------------------------------------------------------------
# Configurações do cx_Freeze
# -------------------------------------------------------------------
build_exe_options = {
    "packages": [
        "app",
        "flask",
        "jinja2",
        "urllib3",
        "PIL",
        "win32print",
        "win32ui",
        "win32com",
        "pythoncom",
    ],
    "includes": [
        "http",
        "http.client",
        "socket",
        "select",
        "queue",
        "win32con",
        "win32timezone",
    ],
    "include_files": includefiles,
    "include_msvcr": True,
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "http",
        "xml",
    ],
}

# -------------------------------------------------------------------
# Define modo GUI (sem console)
# -------------------------------------------------------------------
base = "Win32GUI" if sys.platform == "win32" else None

# -------------------------------------------------------------------
# Criação do executável
# -------------------------------------------------------------------
setup(
    name="BistekPrinter",
    version="2.0.0",
    description="Sistema de Impressão ZQ230 - Projeto Bistek",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="app/__main__.py",
            base=base,
            target_name="BistekPrinter.exe",
            icon=None,  # opcional: caminho para .ico
        )
    ],
)