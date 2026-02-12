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
# ---------------------------------------------------------
# Logs de estatísticas (CSV)
# ---------------------------------------------------------
STATS_CSV: Path | None = None

def init_loggers(audit, error, audit_jsonl: Path | None, stats_csv: Path | None = None):
    global AUDIT_LOGGER, ERROR_LOGGER, AUDIT_JSONL, STATS_CSV
    AUDIT_LOGGER   = audit
    ERROR_LOGGER   = error
    AUDIT_JSONL    = audit_jsonl
    STATS_CSV      = stats_csv

    # Cria arquivo de stats vazio com header se não existir (Obrigatório)
    if STATS_CSV:
        try:
            STATS_CSV.parent.mkdir(parents=True, exist_ok=True)
            if not STATS_CSV.exists():
                with STATS_CSV.open("w", encoding="utf-8") as f:
                    f.write("Data;Loja;Modo;Qtd\n")
        except Exception:
            pass # Logger de erro talvez não esteja pronto, falha silenciosa no init

def log_stats(loja: str, modo: str, copies: int):
    """
    Registra estatísticas simplificadas em CSV:
    DATA;LOJA;MODO;QTD
    """
    if not STATS_CSV:
        return

    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Garante diretório (redundante, mas seguro)
        STATS_CSV.parent.mkdir(parents=True, exist_ok=True)
        
        # Se arquivo não existe, cria header
        if not STATS_CSV.exists():
            with STATS_CSV.open("w", encoding="utf-8") as f:
                f.write("Data;Loja;Modo;Qtd\n")
        
        # Append data
        with STATS_CSV.open("a", encoding="utf-8") as f:
            f.write(f"{now};{loja};{modo};{copies}\n")
    except Exception:
        # Falha silenciosa em stats para não parar fluxo
        pass

# ---------------------------------------------------------
# Logs de auditoria — registra JSON e arquivo audit.jsonl
# ---------------------------------------------------------
def log_audit(action: str, **meta):
    if AUDIT_LOGGER:
        AUDIT_LOGGER.info(action, extra=_with_request_context(meta))

    # salva JSON por linha
    if "trace" in meta and AUDIT_JSONL:
        try:
            AUDIT_JSONL.parent.mkdir(parents=True, exist_ok=True)
            with AUDIT_JSONL.open("a", encoding="utf-8") as f:
                f.write(json.dumps(meta["trace"], ensure_ascii=False) + "\n")
        except Exception:
            pass

# ---------------------------------------------------------
# Logs de erro
# ---------------------------------------------------------
def log_error(message: str, **meta):
    if ERROR_LOGGER:
        ERROR_LOGGER.error(message, extra=_with_request_context(meta))


def log_exception(message: str, **meta):
    if ERROR_LOGGER:
        ERROR_LOGGER.exception(message, extra=_with_request_context(meta))

