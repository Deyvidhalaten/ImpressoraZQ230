from __future__ import annotations

from pathlib import Path
import math
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound


# ============================================================
# REGRAS DE REFERÊNCIA (%VD) - padrão informado por você
# ============================================================
VD_REF = {
    "kcal": 2000.0,
    "carb": 300.0,
    "prot": 75.0,
    "gord": 55.0,
    "sat": 22.0,
    "fibra": 25.0,
    "sodio_mg": 2400.0,
}
# Gorduras trans: VD não estabelecido


# ============================================================
# FUNÇÕES AUXILIARES (Filtros do template)
# ============================================================
def _to_float(v) -> float:
    if v is None:
        return 0.0
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def arredonda_meio_pra_cima(x: float) -> int:
    # 1.5 -> 2 / 1.49 -> 1
    return int(math.floor(x + 0.5))


def fmt_1_casa(v) -> str:
    """
    Sempre 1 casa decimal (inclusive 0,0).
    Ex:
      31 -> '31,0'
      0  -> '0,0'
      6.8 -> '6,8'
    """
    return f"{_to_float(v):.1f}".replace(".", ",")


def kcal_para_kj(kcal) -> str:
    """
    Converte kcal -> kJ com 1 casa decimal.
    """
    kj = _to_float(kcal) * 4.184
    return f"{kj:.1f}".replace(".", ",")


def calcular_vd_percentual(valor, chave_ref: str) -> str:
    """
    Retorna %VD inteiro (sem casas), arredondado meio-pra-cima.
    """
    ref = VD_REF.get(chave_ref)
    if not ref:
        return ""

    pct = (_to_float(valor) / ref) * 100.0
    return str(arredonda_meio_pra_cima(pct))


# ============================================================
# TEMPLATES
# ============================================================
def listar_templates_por_modo(templates_dir: Path) -> Dict[str, List[str]]:
    """
    Procura arquivos *.zpl.j2 e agrupa por "modo" usando o prefixo antes do primeiro "_".
    Ex:
      flv_default.zpl.j2         -> modo "flv"
      floricultura_default.zpl.j2-> modo "floricultura"
      calcados_etiqueta.zpl.j2   -> modo "calcados"
    """
    modos: Dict[str, List[str]] = {}

    if not templates_dir.exists():
        return modos

    for f in templates_dir.glob("*.zpl.j2"):
        nome = f.name
        lower = nome.lower()

        if "_" not in lower:
            # sem prefixo de modo, ignora
            continue

        modo = lower.split("_", 1)[0].strip()
        if not modo:
            continue

        modos.setdefault(modo, []).append(nome)

    # ordena para UI ficar bonitinha
    for m in modos:
        modos[m].sort()

    return modos


def criar_ambiente_zpl(templates_dir: Path) -> Environment:
    """
    Cria o ambiente Jinja para os templates ZPL,
    registrando filtros de padronização e cálculos (%VD / kJ).
    """
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Filtros para usar dentro do .zpl.j2
    env.filters["d1"] = fmt_1_casa
    env.filters["kj"] = kcal_para_kj
    env.filters["vd"] = calcular_vd_percentual

    return env


def render_zpl(env: Environment, template_name: str, **ctx) -> str:
    """
    Renderiza um template ZPL Jinja2.
    Sem fallback automático: se o template não existir, estoura erro
    (melhor pra debug e evitar imprimir "coisa errada").
    """
    try:
        return env.get_template(template_name).render(**ctx)
    except TemplateNotFound as e:
        raise RuntimeError(f"Template ZPL não encontrado: {template_name}") from e

list_templates_by_mode = listar_templates_por_modo