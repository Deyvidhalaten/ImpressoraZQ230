import logging
from logging.handlers import RotatingFileHandler
import os, shutil
from pathlib import Path

def get_programdata_root() -> Path:
    base = os.environ.get("PROGRAMDATA") or ("/var/lib" if os.name != "nt" else r"C:\ProgramData")
    return Path(base) / "BistekPrinter"

def _copy_if_missing(src: Path, dst: Path):
    if src.is_file() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def init_data_layout(repo_base_dir: str) -> dict:
    """
    Garante:
      ProgramData\BistekPrinter\{config, zpl_templates, static\fonts, logs, data}
    Semeia templates (.zpl.j2) e CSVs (seeds) na PRIMEIRA execução.
    Também migra CSVs legados que porventura estejam no diretório do app.
    """
    root = get_programdata_root()
    dirs = {
        "root": root,
        "config": root / "config",
        "templates": root / "zpl_templates",
        "fonts": root / "static" / "fonts",
        "logs": root / "logs",
        "data": root / "data",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)

    # --- TEMPLATES se vazio ---
    repo_tpl = Path(repo_base_dir) / "zpl_templates"
    if not any(dirs["templates"].glob("*.zpl.j2")) and repo_tpl.is_dir():
        for f in repo_tpl.glob("*.zpl.j2"):
            _copy_if_missing(f, dirs["templates"] / f.name)

    # --- CSVs (SEEDS) se não existirem ---
    seeds_dir = Path(repo_base_dir) / "seeds"
    if seeds_dir.is_dir():
        for name in ("baseFloricultura.csv", "baseFatiados.csv", "printers.csv"):
            _copy_if_missing(seeds_dir / name, dirs["data"] / name)

    # --- Migração de legado ---
    legacy_dir = Path(repo_base_dir)
    for legacy in ("baseFloricultura.csv", "baseFatiados.csv", "printers.csv"):
        legacy_path = legacy_dir / legacy
        if legacy_path.exists():
            dst = dirs["data"] / legacy
            if not dst.exists():  # só move se ProgramData ainda não tem
                try:
                    shutil.move(str(legacy_path), str(dst))
                except Exception:
                    # se não conseguir mover, ao menos tenta copiar
                    _copy_if_missing(legacy_path, dst)

    return dirs

def setup_logging(logs_dir: Path):
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"

    handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler, logging.StreamHandler()]
    )