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

    # Templates
    repo_tpl = Path(repo_base_dir) / "zpl_templates"
    if not any(dirs["templates"].glob("*.zpl.j2")) and repo_tpl.is_dir():
        for f in repo_tpl.glob("*.zpl.j2"):
            _copy_if_missing(f, dirs["templates"] / f.name)

    # Seeds
    seeds_dir = Path(repo_base_dir) / "seeds"
    if seeds_dir.is_dir():
        for name in ("baseFloricultura.csv", "baseFatiados.csv", "printers.csv"):
            _copy_if_missing(seeds_dir / name, dirs["data"] / name)

    # Migração
    legacy_dir = Path(repo_base_dir)
    for legacy in ("baseFloricultura.csv", "baseFatiados.csv", "printers.csv"):
        legacy_path = legacy_dir / legacy
        if legacy_path.exists():
            dst = dirs["data"] / legacy
            if not dst.exists():
                _copy_if_missing(legacy_path, dst)

    return dirs
