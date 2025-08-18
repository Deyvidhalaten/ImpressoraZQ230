import ssl, sys, os, glob
from cx_Freeze import setup, Executable

ssl._create_default_https_context = ssl._create_unverified_context

pywin32_system32 = os.path.join(sys.base_prefix, "Lib", "site-packages", "pywin32_system32")
win32_dlls = glob.glob(os.path.join(pywin32_system32, "*.dll")) if os.path.isdir(pywin32_system32) else []

includefiles = [
    ("app/templates", "app/templates"),
    ("app/static", "app/static"),
    ("app/zpl_templates", "app/zpl_templates"),
    ("app/seeds", "app/seeds"),                 # << seeds vão no build
    # Se ainda precisar do módulo auxiliar:
    ("printer_zq230.py", "app/printer_zq230.py"),
    (
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
        "arial.ttf",
    ),
]
includefiles += [(dll, os.path.basename(dll)) for dll in win32_dlls]

build_exe_options = {
    "packages": ["app", "app.routes", "app.services", "flask", "jinja2", "urllib3", "PIL"],
    "includes": [
        "win32print", "win32ui", "win32con", "pywintypes", "pythoncom", "win32com",
        "app.printer_zq230",
    ],
    "include_files": includefiles,
    "include_msvcr": True,
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="ImpressoraApp",
    version="1.1.0",
    description="App de Impressão de EAN-13 via Flask",
    options={"build_exe": build_exe_options},
    executables=[Executable(script="app/app.py", base=base, target_name="ImpressoraApp.exe")]
)
