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
    ("app/controllers", "app/controllers"),
    ("app/dtos", "app/dtos"),
    ("app/mappers", "app/mappers"),
    ("app/models", "app/models"),
    ("app/repositories", "app/repositories"),
    ("app/seeds", "app/seeds"),
    ("app/services", "app/services"),
    ("app/zpl_templates", "app/zpl_templates"),
    # Se você tiver um config.txt ou base.db, adicione aqui
]

# Inclui as DLLs do pywin32 na raiz da build
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

# -------------------------------------------------------------------
# Opções de Build
# -------------------------------------------------------------------
build_exe_options = {
    "packages": [
        "app", "flask", "jinja2", "urllib3", "PIL", "waitress",
        "win32print", "win32ui", "win32gui", "win32com", "pythoncom" # UTEIS E NECESSÁRIOS
    ],
    "includes": [
        "http.client", "socket", "select", "queue",
        "win32con", "win32timezone" # UTEIS PARA CONTEXTO DE REDE E HORA
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
# Deixamos base = None para que o console apareça. 
# Se o app crashar, o erro ficará parado na tela preta.
base = None 

setup(
    name="BistekPrinter",
    version="2.3.2",
    description="Sistema de Impressão ZQ230 - Modo Debug",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="app/__main__.py",
            base=base,
            target_name="BistekPrinter.exe"
        )
    ],
)