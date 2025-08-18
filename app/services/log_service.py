# app/services/log_service.py
import csv, time, logging
from pathlib import Path
from flask import has_request_context, request

# estes três serão preenchidos pelo bootstrap
SERVICE_LOGGER: logging.Logger | None = None
AUDIT_LOGGER:   logging.Logger | None = None
ERROR_LOGGER:   logging.Logger | None = None

LOG_CSV: Path | None = None  # para compat do /logs (histórico compactado)

def _with_request_context(data: dict) -> dict:
    if has_request_context():
        data.setdefault("client_ip", request.remote_addr)
        data.setdefault("method", request.method)
        data.setdefault("path", request.path)
        data.setdefault("user_agent", getattr(request, "user_agent", None) and request.user_agent.string)
    return data

def init_loggers(service: logging.Logger, audit: logging.Logger, error: logging.Logger, csv_file: Path | None):
    global SERVICE_LOGGER, AUDIT_LOGGER, ERROR_LOGGER, LOG_CSV
    SERVICE_LOGGER = service
    AUDIT_LOGGER   = audit
    ERROR_LOGGER   = error
    LOG_CSV        = csv_file

def log_service(message: str, **meta):
    if SERVICE_LOGGER:
        SERVICE_LOGGER.info(message, extra=_with_request_context(meta))

def log_audit(action: str, **meta):
    if AUDIT_LOGGER:
        AUDIT_LOGGER.info(action, extra=_with_request_context(meta))

def log_error(message: str, **meta):
    if ERROR_LOGGER:
        ERROR_LOGGER.error(message, extra=_with_request_context(meta))

def log_exception(message: str, **meta):
    if ERROR_LOGGER:
        ERROR_LOGGER.exception(message, extra=_with_request_context(meta))

# -------- Compatibilidade com sua rota /logs (CSV “compacto”) --------
def append_log(evento: str, ip: str = "", impressora: str = "", detalhes: str = ""):
    """
    Mantém o CSV para sua tela /logs atual.
    """
    if LOG_CSV is None:
        return
    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    exists = LOG_CSV.exists()
    with LOG_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["timestamp","evento","ip","impressora","detalhes"])
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        w.writerow([ts, evento, ip, impressora, detalhes])

    # Além do CSV, já aproveita e dispara no logger de serviço
    log_service(
        f"csv_log/{evento}",
        ip=ip, impressora=impressora, detalhes=detalhes
    )
