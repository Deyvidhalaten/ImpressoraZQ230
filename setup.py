import sys, os, glob
from cx_Freeze import setup, Executable

# onde o pywin32 instala as DLLs
pywin32_system32 = os.path.join(
    sys.base_prefix, "Lib", "site-packages", "pywin32_system32"
)

# lista todas as DLLs do pywin32 para copiar pro build
win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll"))

includefiles = [
    ("templates", "templates"),
    ("static",   "static"),
    ("baseFloricultura.csv", "baseFloricultura.csv"),
    ("config.txt",           "config.txt"),
    
    (os.path.join(os.environ["WINDIR"], "Fonts", "arial.ttf"), "arial.ttf"),
]
# joga as DLLs do pywin32 pra mesma pasta do EXE
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

build_exe_options = {
    "packages": [
        "flask", "jinja2",
        "requests", "urllib3",
        "PIL",
        "csv", "socket", "tempfile",
        # adiciona win32com pois algumas partes de pywin32 precisam dele
        "win32print", "win32ui", "win32con", "pywintypes", "pythoncom", "win32com"
    ],
    "includes": [
        "win32print", "win32ui", "win32con",
        "pywintypes", "pythoncom", "win32com"
    ],
    "include_files": includefiles,
    "include_msvcr": True,
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"  # sem console

setup(
    name="ImpressoraApp",
    version="1.0",
    description="App de Impressão de EAN-13",
    options={"build_exe": build_exe_options},
    executables=[Executable(
        script="app.py",
        base=base,
        target_name="ImpressoraApp.exe"
    )],
)