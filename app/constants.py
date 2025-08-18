import os, sys
from datetime import timedelta

BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(__file__)
)

# Arquivos
CONFIG_FILE  = os.path.join(BASE_DIR, 'config.txt')
CSV_FILE     = os.path.join(BASE_DIR, 'baseFloricultura.csv')
CSV_FILE2    = os.path.join(BASE_DIR, 'baseFatiados.csv')
PRINTERS_CSV = os.path.join(BASE_DIR, 'printers.csv')
LOG_FILE     = os.path.join(BASE_DIR, "logs.csv")

# Defaults
DEFAULT_IP       = "10.17.30.119"
DEFAULT_PORTA    = 9100
DEFAULT_LS_FLOR  = -40
DEFAULT_LS_FLV   = -20

# Credenciais
SHUTDOWN_PASSWORD = "admin"
USUARIO           = "admin"
SENHA             = "1234"

# Sessão
SECRET_KEY = "chave-secreta"
PERMANENT_SESSION_LIFETIME = timedelta(minutes=5)
