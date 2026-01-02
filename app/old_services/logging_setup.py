# app/services/logging_setup.py
import os, json, socket, platform, logging, time
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

APP_NAME      = "BistekPrinter"
APP_VERSION   = os.environ.get("BISTEK_APP_VERSION", "dev")
ENVIRONMENT   = os.environ.get("BISTEK_ENV", "prd")   # prd|hml|dev
HOSTNAME      = socket.gethostname()
PROCESS_ID    = os.getpid()

class JsonFormatter(logging.Formatter):
    # Gera uma linha JSON por registro
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts":        time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(record.created)),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
            "app":       APP_NAME,
            "version":   APP_VERSION,
            "env":       ENVIRONMENT,
            "host":      HOSTNAME,
            "pid":       PROCESS_ID,
            "module":    record.module,
            "func":      record.funcName,
        }
        # Merge extras, se houver
        if record.args and isinstance(record.args, dict):
            base.update(record.args)
        # Se usarmos logger.info("msg", extra={"key": "val"})
        for k, v in getattr(record, "__dict__", {}).items():
            if k not in base and k not in ("msg", "args", "levelno", "levelname", "name",
                                           "created", "msecs", "relativeCreated", "pathname",
                                           "filename", "module", "lineno", "funcName",
                                           "thread", "threadName", "process", "processName",
                                           "exc_info", "exc_text", "stack_info", "stacklevel"):
                base[k] = v
        # Stack/exception
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)

def _make_handler(path: Path) -> TimedRotatingFileHandler:
    path.parent.mkdir(parents=True, exist_ok=True)
    h = TimedRotatingFileHandler(
        filename=str(path),
        when="midnight",
        backupCount=7,           # mantém 7 dias
        encoding="utf-8",
        utc=False
    )
    h.setFormatter(JsonFormatter())
    return h

def setup_logging(logs_dir: Path) -> dict:
    """
    Cria 3 loggers:
      - app.service → requests, prints, startup/shutdown
      - app.audit   → mudanças em printers.csv, ajustes de LS
      - app.error   → exceções (além de também duplicar no service se quiser)
    Retorna os loggers em um dict para uso eventual.
    """
    logs_dir = Path(logs_dir)
    service_path = logs_dir / "service.log"
    audit_path   = logs_dir / "audit.log"
    error_path   = logs_dir / "error.log"

    # Evita duplicar handlers se setup_logging for chamado 2x
    for name in ("app.service", "app.audit", "app.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = False
        logger.setLevel(logging.INFO)

    # Handlers
    service_h = _make_handler(service_path)
    audit_h   = _make_handler(audit_path)
    error_h   = _make_handler(error_path)

    # Loggers
    service_logger = logging.getLogger("app.service"); service_logger.addHandler(service_h)
    audit_logger   = logging.getLogger("app.audit");   audit_logger.addHandler(audit_h)
    error_logger   = logging.getLogger("app.error");   error_logger.addHandler(error_h)
    error_logger.setLevel(logging.WARNING)  # erros/alertas

    # Também espelha erros no console durante dev
    if ENVIRONMENT != "prd":
        console = logging.StreamHandler()
        console.setFormatter(JsonFormatter())
        service_logger.addHandler(console)
        audit_logger.addHandler(console)
        error_logger.addHandler(console)

    return {
        "service": service_logger,
        "audit":   audit_logger,
        "error":   error_logger,
    }
