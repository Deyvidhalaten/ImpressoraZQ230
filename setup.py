import sys
import os
import glob
import ssl
from cx_Freeze import setup, Executable

# --- Corrige problemas de SSL em ambientes sem certificado ---
ssl._create_default_https_context = ssl._create_unverified_context

# --- Localiza DLLs do PyWin32 (para win32print, win32ui, etc.) ---
pywin32_system32 = os.path.join(sys.base_prefix, "Lib", "site-packages", "pywin32_system32")
win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll")) if os.path.isdir(pywin32_system32) else []

# --- Arquivos adicionais a incluir no build ---
includefiles = [
    ("app/static", "app/static"),
    ("app/templates", "app/templates"),
    ("app/zpl_templates", "app/zpl_templates"),
    ("app/seeds", "app/seeds"),
    ("app/printer_zq230.py", "app/printer_zq230.py"),
    ("app/routes", "app/routes"),
]

# --- Inclui DLLs do PyWin32 ---
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

# --- Configurações do build ---
build_exe_options = {
    "packages": [
        "app",
        "app.routes",
        "app.services",
        "flask",
        "jinja2",
        "urllib3",
        "PIL",
        "win32print",
        "win32ui",
        "win32con",
        "win32com",
        "pythoncom",
    ],
    "includes": [
        "app.printer_zq230",
        "app.__main__",
    ],
    "include_files": includefiles,
    "include_msvcr": True,  # Inclui runtime do Visual C++
    "excludes": ["tkinter"],  # reduz tamanho final
}

# --- Define o modo GUI (sem console) ---
base = "Win32GUI" if sys.platform == "win32" else None

# --- Cria executável ---
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
            icon=None,  # opcional: caminho para ícone .ico
        )
    ],
)
