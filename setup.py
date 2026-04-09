import sys
import os
import glob
import ssl
from cx_Freeze import setup, Executable

# -------------------------------------------------------------------
# Configuração SSL para downloads durante o build
# -------------------------------------------------------------------
ssl._create_default_https_context = ssl._create_unverified_context

# -------------------------------------------------------------------
# Localiza DLLs do PyWin32 (Essencial para Zebra ZQ230)
# -------------------------------------------------------------------
pywin32_system32 = os.path.join(sys.base_prefix, "Lib", "site-packages", "pywin32_system32")
win32_dlls = []
if os.path.isdir(pywin32_system32):
    win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll"))

# -------------------------------------------------------------------
# Arquivos Adicionais (Estrutura de pastas do App)
# -------------------------------------------------------------------
includefiles = [
    ("app/zpl_templates", "app/zpl_templates"),
    ("frontend", "frontend"),
]

# Inclui as DLLs do pywin32 na raiz da build
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

# -------------------------------------------------------------------
# Opções de Build
# -------------------------------------------------------------------
build_exe_options = {
    "packages": [
        "app", "flask", "jinja2", "urllib3", "PIL", "waitress"
    ],
    "includes": [
        "http.client", "socket", "select", "queue"
    ],
    "include_files": includefiles,
    "include_msvcr": True,
    
    # --- ESTRATÉGIA "ARQUIVO ABERTO" ---
    "zip_include_packages": [],      # Não coloca nada dentro de um arquivo .zip
    "zip_exclude_packages": ["*"],   # Força tudo a ficar na pasta 'lib' como arquivos individuais
    "optimize": 0,                   # Sem otimização para facilitar o debug
}

# -------------------------------------------------------------------
# Executável (Console Habilitado para Debug)
# -------------------------------------------------------------------
# Deixamos base = "Win32GUI" para rodar invisível de fundo (Sem tela preta)
base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="BistekPrinter",
    version="2.3.2",
    description="Sistema de Impressão ZQ230 - Modo Produção",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="app/__main__.py",
            base=base,
            icon="frontend/logo.ico" if os.path.exists("frontend/logo.ico") else None,
            target_name="BistekPrinter.exe"
        )
    ],
)