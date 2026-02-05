# app/services/log_service.py
import json
import logging
from pathlib import Path
from flask import has_request_context, request

# Loggers configurados no bootstrap
AUDIT_LOGGER:   logging.Logger | None = None
ERROR_LOGGER:   logging.Logger | None = None

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
def init_loggers(audit, error, audit_jsonl: Path | None):
    global AUDIT_LOGGER, ERROR_LOGGER, AUDIT_JSONL
    AUDIT_LOGGER   = audit
    ERROR_LOGGER   = error
    AUDIT_JSONL    = audit_jsonl


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

