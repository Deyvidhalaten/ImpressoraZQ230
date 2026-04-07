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
        "waitress",
    ],
    "includes": [
        "http.client",
        "socket",
        "select",
        "queue",
    ],
    "include_files": includefiles,
    "include_msvcr": True,
    "zip_include_packages": "*",
    "zip_exclude_packages": [],
    "optimize": 2,
    "excludes": [
        "tkinter",
        "unittest",
        "email",
        "xml",
    ],
}

# -------------------------------------------------------------------
# Define modo GUI (sem console)
# -------------------------------------------------------------------
#base = None
base = "Win32GUI" if sys.platform == "win32" else None

# -------------------------------------------------------------------
# Criação do executável
# -------------------------------------------------------------------
setup(
    name="BistekPrinter",
    version="2.3.2",
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