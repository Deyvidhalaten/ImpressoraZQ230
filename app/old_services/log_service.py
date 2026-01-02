# app/services/log_service.py
import json
import csv, time, logging
from pathlib import Path
from flask import has_request_context, request

# Loggers configurados no bootstrap
SERVICE_LOGGER: logging.Logger | None = None
AUDIT_LOGGER:   logging.Logger | None = None
ERROR_LOGGER:   logging.Logger | None = None

LOG_CSV: Path | None = None  # para compatibilidade com /logs CSV, Descartar quando atualizar para Graficos
AUDIT_JSONL: Path | None = None

# ---------------------------------------------------------
# Insere dados do contexto HTTP automaticamente
# ---------------------------------------------------------
def _with_request_context(data: dict) -> dict:
    if has_request_context():
        data.setdefault("client_ip", request.remote_addr)
        data.setdefault("method", request.method)
        data.setdefault("path", request.path)
        data.setdefault("user_agent",
                        getattr(request, "user_agent", None)
                        and request.user_agent.string)
    return data


# ---------------------------------------------------------
# Inicialização feita no bootstrap
# ---------------------------------------------------------
def init_loggers(service, audit, error, csv_file: Path | None, audit_jsonl: Path | None):
    global SERVICE_LOGGER, AUDIT_LOGGER, ERROR_LOGGER, LOG_CSV, AUDIT_JSONL
    SERVICE_LOGGER = service
    AUDIT_LOGGER   = audit
    ERROR_LOGGER   = error
    LOG_CSV        = csv_file
    AUDIT_JSONL    = audit_jsonl


# ---------------------------------------------------------
# Logs gerais do sistema (INFO)
# ---------------------------------------------------------
def log_service(message: str, **meta):
    if SERVICE_LOGGER:
        SERVICE_LOGGER.info(message, extra=_with_request_context(meta))


# ---------------------------------------------------------
# Logs de auditoria — registra JSON e arquivo audit.jsonl
# ---------------------------------------------------------
def log_audit(action: str, **meta):
    if AUDIT_LOGGER:
        AUDIT_LOGGER.info(action, extra=_with_request_context(meta))

    # salva JSON por linha
    if "trace" in meta and AUDIT_JSONL:
        AUDIT_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(meta["trace"], ensure_ascii=False) + "\n")


# ---------------------------------------------------------
# Logs de erro
# ---------------------------------------------------------
def log_error(message: str, **meta):
    if ERROR_LOGGER:
        ERROR_LOGGER.error(message, extra=_with_request_context(meta))


def log_exception(message: str, **meta):
    if ERROR_LOGGER:
        ERROR_LOGGER.exception(message, extra=_with_request_context(meta))


def append_log(evento: str, ip: str = "", impressora: str = "", detalhes: str = ""):
    if LOG_CSV is None:
        return

    LOG_CSV.parent.mkdir(parents=True, exist_ok=True)

    exists = LOG_CSV.exists()
    with LOG_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["timestamp", "evento", "ip", "impressora", "detalhes"])
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        w.writerow([ts, evento, ip, impressora, detalhes])

    log_service("csv_log/" + evento, ip=ip, impressora=impressora, detalhes=detalhes)
