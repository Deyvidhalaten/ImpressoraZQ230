import os, shutil
from pathlib import Path

def get_appdata_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or Path.home()
    return Path(base) / "BistekPrinter"

def _copy_if_missing(src: Path, dst: Path):
    if src.is_file() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def init_data_layout(repo_base_dir: str) -> dict:
    root = get_appdata_root()
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

    # Settings padrão (modo teste desligado)
    settings_file = dirs["config"] / "settings.txt"
    if not settings_file.exists():
        settings_file.write_text("impressora_teste=0\n", encoding="utf-8")

    # Templates
    repo_tpl = Path(repo_base_dir) / "zpl_templates"
    if not any(dirs["templates"].glob("*.zpl.j2")) and repo_tpl.is_dir():
        for f in repo_tpl.glob("*.zpl.j2"):
            _copy_if_missing(f, dirs["templates"] / f.name)

    # Seeds
    seeds_dir = Path(repo_base_dir) / "seeds"
    if seeds_dir.is_dir():
        for name in ("baseFloricultura.csv", "baseFatiados.csv", "printers.csv", "baseFLV_normalizada.csv"):
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

