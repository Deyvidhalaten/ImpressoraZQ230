from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

def list_templates_by_mode(templates_dir: Path):
    flor, flv = [], []
    if not templates_dir.exists():
        return {"Floricultura": flor, "FLV": flv}
    for f in templates_dir.glob("*.zpl.j2"):
        name = f.name.lower()
        if name.startswith("floricultura_"): flor.append(f.name)
        elif name.startswith("flv_"):        flv.append(f.name)
    flor.sort(); flv.sort()
    return {"Floricultura": flor, "FLV": flv}

def make_env(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False, trim_blocks=True, lstrip_blocks=True
    )

def render_zpl(env: Environment, template_name: str | None, **ctx) -> str:
    if template_name:
        try:
            return env.get_template(template_name).render(**ctx)
        except TemplateNotFound:
            pass
    # Fallback com seus ZPL originais
    if ctx.get("modo") == "Floricultura":
        return (
            f"^XA\n^PRD^FS\n^LS{ctx['ls']}^FS\n^PW663^FS\n^LT0\n^LL250^FS\n^JMA^FS\n^BY2\n"
            f"^FO100,020^A0N,40,20^FD{ctx['texto']} ^FS\n"
            f"^FO100,75^A0N,25,20^FD{ctx['codprod']}^FS\n"
            f"^FO100,105^BEN,50,Y,N^FD{ctx['ean']}^FS\n"
            f"^FO455,015^A0N,40,20^FD{ctx['texto']}^FS\n"
            f"^FO455,75^A0N,25,20^FD{ctx['codprod']}^FS\n"
            f"^FO450,105^BEN,50,Y,N^FD{ctx['ean']}^FS\n"
            f"^PQ{ctx['copies']},0,1,N^FS\n^XZ\n"
        )
    inf = ctx.get("infnutri") or []
    lines = ["^XA","^PRD^FS",f"^LS{ctx['ls']}^FS","^LH0,0^FS","^LL400^FS","^JMA^FS","^BY2",
             f"^FO90,50^A0N,50,20^FD{ctx['texto']}^FS"]
    for i in range(16):
        y = 115 + (i*20)
        val = inf[i] if i < len(inf) else ""
        lines.append(f"^FO90,{y}^A0N,15,20^FD{val}^FS")
    lines += [
        f"^FO130,440^A0N,25,20^FD{ctx['codprod']}^FS",
        f"^FO120,460^BEN,50,Y,N^FD{ctx['ean']}^FS",
        f"^FO90,550^A0N,40,30^FDValidade: {ctx['validade']} Dias^FS",
        f"^FO90,590^A0N,40,30^FDProduzido: {ctx['data']}^FS",
        f"^PQ{ctx['copies']},0,1,N","^XZ"
    ]
    return "\n".join(lines)
