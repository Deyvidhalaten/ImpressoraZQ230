from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.exceptions.validation_exception import ValidationException

def list_available_modes(templates_dir: Path) -> dict:
    modes = {}

    for tpl in templates_dir.glob("*.zpl.j2"):
        name = tpl.stem.replace(".zpl", "")
        mode = name.split("_")[0].lower()

        if mode not in modes:
            modes[mode] = mode.capitalize()

    return modes


def resolve_template(mode: str, templates_dir: Path) -> Path:
    candidates = sorted(templates_dir.glob(f"{mode}_*.zpl.j2"))

    if not candidates:
        raise ValidationException(f"Template não encontrado para modo '{mode}'")

    return candidates[0]

def render_zpl(template_path: Path, context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=False
    )

    template = env.get_template(template_path.name)
    return template.render(**context)
