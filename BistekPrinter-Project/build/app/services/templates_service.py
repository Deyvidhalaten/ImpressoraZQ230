from __future__ import annotations

from pathlib import Path
import math
from typing import Dict, List, Optional
import re
import json

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
    Procura arquivos *.zpl e *.zpl.j2 e agrupa por "modo".
    Adiciona logs para monitorar a detecção em runtime.
    """
    modos: Dict[str, List[str]] = {}

    import traceback
    try:
        from app.services.log_service import log_error, log_audit
    except ImportError:
        def log_error(acao, erro, **kwargs):
            print(f"[ERRO TEMPLATES] {acao}: {erro}")
        def log_audit(acao, **kwargs):
            print(f"[AUDIT TEMPLATES] {acao}: {kwargs}")

    if not templates_dir.exists():
        log_error("templates_not_found", erro=f"O diretório {templates_dir} não existe ou está inacessível.")
        return modos

    found_files = []
    for ext in ("*.zpl", "*.zpl.j2"):
        for f in templates_dir.glob(ext):
            nome = f.name
            lower = nome.lower()
            found_files.append(nome)

            base_name = lower.replace(".zpl.j2", "").replace(".zpl", "")
            
            if base_name.endswith("_default"):
                modo = base_name.replace("_default", "").strip()
            elif "_" in base_name and any(base_name.endswith(x) for x in ["_v2", "_var", "_promo"]):
                modo = base_name.rsplit("_", 1)[0].strip()
            elif "_" in base_name:
                modo = base_name.strip()
            else:
                modo = base_name.strip()

            if not modo:
                continue

            modos.setdefault(modo, []).append(nome)

    for m in modos:
        modos[m] = list(set(modos[m]))
        modos[m].sort()

    log_audit("templates_scanned", dir=str(templates_dir), qtd_arquivos=len(found_files), files=found_files, modos_extraidos=list(modos.keys()))
    return modos

def get_template_meta(templates_dir: Path) -> dict:
    """Busca os metadados das Etiquetas (ex: permitir_campos_extras)."""
    meta_path = templates_dir / "template_meta.json"
    if not meta_path.exists():
        return {}
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_template_meta(templates_dir: Path, template_name: str, permitir_extras: bool):
    """Salva a flag de campos extras para o template ZPL específico."""
    meta = get_template_meta(templates_dir)
    if template_name not in meta:
        meta[template_name] = {}
    meta[template_name]["permitir_campos_extras"] = bool(permitir_extras)
    
    meta_path = templates_dir / "template_meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4)


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

def render_zpl_dynamico(template_path: Path, **ctx) -> str:
    """
    Lê um arquivo ZPL plano e substitui {{ variaveis }} dinamicamente via Regex.
    Suporta dot notation para acessar dicionários (ex: nutri.kcal).
    """
    if not template_path.exists():
        raise RuntimeError(f"Template ZPL dinâmico não encontrado: {template_path.name}")
        
    with template_path.open("r", encoding="utf-8") as f:
        content = f.read()

    def replace_match(match):
        tag = match.group(1).strip()
        parts = tag.split('.')
        val = ctx
        
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part, "")
            else:
                val = ""
                break
                
        if val is None:
            val = ""
            
        return str(val)

    # Captura tudo entre {{ }} (espaços opcionais)
    processed = re.sub(r"\{\{\s*(.*?)\s*\}\}", replace_match, content)
    return processed

list_templates_by_mode = listar_templates_por_modo