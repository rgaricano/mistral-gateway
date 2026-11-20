#!/usr/bin/env python3
# OKF-METADATA
# type: Tool
# title: "build_static_site.py — genera el árbol estático publicable"
# description: "Regenera gentle-companion/docs/accounting/ desde los datos vivos: index.html, los 3 gráficos PNG con OKF embebido, las fichas y las páginas auxiliares. Sin JavaScript, sin CDN."
# status: verified
# generated: 2026-11-20T23:00:00+01:00
# source:
#   - "accounting/data.py (lectura viva, serie, tokens)"
#   - "accounting/fichas/*.html (fichas de financiación)"
#   - "accounting/assets/favicon_conta.svg"
# verified: 2026-11-20
# stale_after: 2027-06-30
"""Genera la versión estática publicable del dashboard.

Hasta ahora el árbol de `gentle-companion/docs/accounting/` se construía a mano
con comandos sueltos, lo que significa que se quedaba obsoleto en cuanto pasaban
unas horas — y lo hacía en silencio, sirviendo cifras viejas como si fueran de
hoy. Este script lo hace reproducible y verificable.

    python3 accounting/build_static_site.py
    python3 accounting/build_static_site.py --dest /ruta/alternativa

Qué genera:
  index.html          dashboard con los gráficos como <img>, sin JS ni CDN
  chart-{1,2,3}.png   gráficos exportados, con su OKF embebido (iTXt)
  fichas/*.html       las 26 fichas, con enlaces relativos
  opcion1.html        ficha ampliada del crédito fiscal I+D
  mapa_completo.html  página de navegación
  favicon.svg         icono

Reglas que respeta: REGLA #1 (coma decimal, punto de miles) dentro del HTML y
DENTRO de los gráficos; cero `<script>`; cero URLs externas para gráficos.
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data

DEFAULT_DEST = (
    Path.home() / "Trabajo" / "IAI" / "gentle-companion" / "docs" / "accounting"
)

MES_CORTO = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
             7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}

STYLE = dict(template="plotly_dark", paper_bgcolor="#1b2740", plot_bgcolor="#16203a")


def es(value: float, decimals: int = 2) -> str:
    """REGLA #1: coma decimal, punto de miles."""
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def es_day(iso_day: str) -> str:
    _, month, day = (int(part) for part in iso_day.split("-"))
    return f"{day} {MES_CORTO[month]}"


# ------------------------------------------------------------------ los gráficos
def build_charts(dest: Path, stamp) -> list[str]:
    """Export the three charts as PNG and embed their OKF. Returns their titles."""
    import plotly.graph_objects as go

    series = data.allowance_series()
    deltas = data.daily_allowance_delta(series)
    days = [es_day(d) for d, _ in series]
    eur_point = data.euro_per_quota_point()

    # 1 — acumulado del ciclo
    fig1 = go.Figure(go.Scatter(x=days, y=[p for _, p in series], mode="lines+markers",
                                line=dict(color="#22c55e", width=3)))
    fig1.update_layout(title="Cuota Vibe usada por día (acumulado del ciclo)",
                       xaxis_title="Día", yaxis_title="% del ciclo", height=380,
                       yaxis=dict(ticksuffix=" %"), **STYLE)
    fig1.write_image(str(dest / "chart-1.png"), width=1100, height=380, scale=2)

    # 2 — euros de suscripción por día
    values = [round(dp * eur_point, 2) for _, dp in deltas]
    fig2 = go.Figure(go.Bar(x=days, y=values, marker_color="#3b82f6",
                            text=[f"{v:.2f} €".replace(".", ",") for v in values],
                            textposition="outside"))
    fig2.update_layout(title="Consumo diario en euros de suscripción",
                       xaxis_title="Día", yaxis_title="€/día", height=330, **STYLE)
    fig2.write_image(str(dest / "chart-2.png"), width=1100, height=330, scale=2)

    # 3 — tokens por día, con separador de miles español en el eje
    tokens = data.daily_tokens()
    if tokens:
        top = max(t["tokens"] for t in tokens)
        step = 100_000_000
        tickvals, ticktext, value = [], [], 0
        while value <= top * 1.05:
            tickvals.append(value)
            ticktext.append(f"{value:,}".replace(",", "."))
            value += step
        fig3 = go.Figure()
        for key, label, colour in (("input_uncached", "input sin caché", "#8b5cf6"),
                                   ("cached", "caché (reutilizado)", "#6366f1"),
                                   ("completion", "compleción", "#22d3ee")):
            fig3.add_trace(go.Bar(x=[es_day(t["day"]) for t in tokens],
                                  y=[t[key] for t in tokens], name=label,
                                  marker_color=colour))
        fig3.update_layout(barmode="stack", title="Tokens medidos por día",
                           xaxis_title="Día", yaxis_title="Tokens", height=360,
                           yaxis=dict(tickvals=tickvals, ticktext=ticktext),
                           legend=dict(traceorder="normal"), **STYLE)
    else:
        fig3 = go.Figure()
        fig3.add_annotation(text="sin datos de tokens en este entorno",
                            showarrow=False, font=dict(size=16, color="#94a3b8"))
        fig3.update_layout(title="Tokens medidos por día", height=360, **STYLE)
    fig3.write_image(str(dest / "chart-3.png"), width=1100, height=360, scale=2)

    titles = [
        ("chart-1.png", "Cuota Vibe usada por día (acumulado del ciclo)",
         "Serie de allowance medida cada día del ciclo."),
        ("chart-2.png", "Consumo diario en euros de suscripción",
         "Incremento diario de cuota expresado en euros de la suscripción."),
        ("chart-3.png", "Tokens medidos por día",
         "Tokens por día desglosados en input sin caché, caché y compleción."),
    ]
    for name, title, description in titles:
        stamp(dest / name, {
            "type": "Chart Image", "title": title, "description": description,
            "status": "verified",
            "source": "usage.db", "verified": datetime.now().date().isoformat(),
            "stale_after": data.RESET_AT,
        })
    return [t for _, t, _ in titles]


# --------------------------------------------------------------------- el índice
def build_index(dest: Path, quote: dict, plan: dict) -> str:
    now = datetime.now().astimezone().replace(microsecond=0)
    budget = data.BUDGET_EUR
    price = data.SUBSCRIPTION_PRICE_EUR
    eur_point = data.euro_per_quota_point()
    pct = quote["percent"]
    used = pct / 100 * budget
    free = budget - used
    pace = plan["recent_pts_day"]
    runway = data.days_until_exhausted(pct, pace)

    if runway is None:
        runway_row = "sin consumo reciente medible"
    else:
        margin = runway - plan["days_left"]
        shown = round(abs(margin))
        word = "día" if shown == 1 else "días"
        verdict = (f"margen de {shown} {word}" if margin >= 0
                   else f"se agota {shown} {word} antes del reset")
        runway_row = f"{runway:.0f} días ({es(runway / 30, 1)} meses) · {verdict}"

    okf = f"""<!-- OKF-METADATA
---
type: Dashboard Page
title: "CONTA — cuota, coste y financiación (vista estática)"
description: "Versión estática publicable del dashboard: datos reales del ciclo, gráficos como imágenes, sin JavaScript ni CDN."
status: verified
generated: {now.isoformat()}
source:
  - "usage.db (tokens por día y modelo, registrado del proveedor)"
  - "read_quota() sobre la API de suscripción"
  - "journalctl --user -u mistral-gateway (serie de allowance)"
verified: {now.date().isoformat()}
stale_after: {data.RESET_AT}
---
-->"""

    html = okf + f"""
<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>CONTA · Cuota Vibe</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>
 body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:24px auto;max-width:1200px;line-height:1.5}}
 h1{{font-size:1.35rem;margin:0 0 4px}} h2{{font-size:1.05rem;margin:28px 0 8px}}
 .panel{{background:#1b2740;border:1px solid #2d3f63;border-radius:10px}}
 .kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin:12px 0}}
 .kpi div{{background:#1e293b;border-radius:8px;padding:10px}}
 .lbl{{color:#7dd3fc;font-weight:600}} .sub{{color:#94a3b8;font-size:.9rem}}
 table{{width:100%;border-collapse:collapse;font-size:.92rem}}
 th{{background:#1e293b;padding:10px 12px;text-align:left}}
 td{{padding:10px 12px}}
 a{{color:#7dd3fc}}
 nav a{{margin-right:16px;text-decoration:none}}
 img.chart{{width:100%;height:auto;display:block;border-radius:10px}}
 .muted{{color:#94a3b8}}
</style></head>
<body>
<nav class="panel" style="padding:8px 12px;margin-bottom:12px">
<a href="#inventario">Inventario</a><a href="#mapa">Mapa de financiación</a><a href="#graficos">Gráficos</a>
</nav>

<h1>💰 CONTA · Suscripción Mistral Vibe</h1>
<p class="muted">Plan Individual · {es(price)} €/mes · presupuesto {es(budget, 0)} € por ciclo ·
PAYG desactivado · reset {data.RESET_AT} · <b>objetivo: aprovechar la cuota sin derrocharla y sin quedarse corto</b></p>

<div class="kpi">
<div><span class="lbl">Cuota usada</span><br>{es(pct)} % = {es(used)} € de {es(budget, 0)} €<br><span class="sub">medido con read_quota()</span></div>
<div><span class="lbl">Cuota libre</span><br>{es(free)} €<br><span class="sub">PAYG off: lo que sobre no se factura</span></div>
<div><span class="lbl">Ritmo reciente</span><br>{es(pace)} pp/día = {es(pace * eur_point)} € suscr./día<br><span class="sub">última medición</span></div>
<div><span class="lbl">Ritmo requerido</span><br>{es(plan['required_pts_day'])} pp/día<br><span class="sub">para llegar al 100 % el reset</span></div>
<div><span class="lbl">Agotamiento</span><br>{runway_row}<br><span class="sub">al ritmo reciente, en puntos de cuota</span></div>
<div><span class="lbl">Economía del plan</span><br>1 pp = {es(budget / 100)} € de presupuesto = {es(eur_point, 4)} € de lo que pagas<br><span class="sub">fijo: {es(price / plan['cycle_days'])} €/día en un ciclo de {plan['cycle_days']} días</span></div>
<div><span class="lbl">Ciclo</span><br>día {plan['cycle_day']} de {plan['cycle_days']}<br><span class="sub">contratada el 14-nov, reset el día 1</span></div>
</div>

<h2 id="graficos">📈 Evolución</h2>
<div class="panel" style="padding:10px"><img class="chart" src="chart-1.png" alt="Cuota Vibe usada por día, acumulado del ciclo"></div>
<div class="panel" style="padding:10px;margin-top:12px"><img class="chart" src="chart-2.png" alt="Consumo diario en euros de suscripción"></div>
<div class="panel" style="padding:10px;margin-top:12px"><img class="chart" src="chart-3.png" alt="Tokens medidos por día, desglosados"></div>
<p class="muted">Gráficos exportados como imagen desde los datos reales. Sin JavaScript ni CDN:
la página es un HTML plano que puedes abrir desde cualquier sitio.</p>

<h2 id="inventario">🖥️ Inventario de equipos</h2>
<div class="panel" style="padding:6px 10px">
<table>
<tr><th>Equipo</th><th>CPU</th><th>RAM</th><th>GPU / VRAM</th><th>Discos</th></tr>
<tr><td><b>ricardo-HP-Xubuntu</b> (laptop)</td><td>Intel i3-6006U 2C/4T @ 2.0 GHz (Skylake)</td><td>12 GB (11 GiB usables)</td><td>Intel HD 520 + AMD Radeon R5 M330 (2.048 MB dedicados)</td><td>/ 81 GB (90 %) · /home 369 GB (93 %)</td></tr>
<tr><td><b>ricardoPC</b> (escritorio)</td><td>AMD Athlon 200GE 2C/4T @ 3.2 GHz (Zen)</td><td>13 Gi</td><td>NVIDIA RTX 3060 — 12.288 MiB (medido con nvidia-smi)</td><td>/ 64 GB (31 %) · /home 679 GB (94 %) · 3 discos más</td></tr>
</table>
<p class="muted" style="padding:0 6px 6px">HP medido in situ (lscpu/free/lspci/lsblk/df). ricardoPC medido por INFRA vía SSH con nvidia-smi.</p>
</div>

<h2 id="mapa">🗺️ Mapa de financiación</h2>
<p>26 vías identificadas, ordenadas por valor esperado frente a esfuerzo. Cada una con su ficha:
cuantía, plazo, requisitos duros, encaje y fuentes con fecha de consulta.</p>
<p><a href="mapa_completo.html">Ver el mapa completo</a> · <a href="opcion1.html">Ficha ampliada: crédito fiscal I+D+i</a> · <a href="fichas/1-nlnet-restack.html">Ficha #1: NLnet / Restack</a></p>

<hr style="border-color:#2d3f63;margin:24px 0 12px">
<p class="muted">Generado el {now.date().isoformat()} a las {now.strftime('%H:%M')} · datos de
<code>usage.db</code>, <code>read_quota()</code> y <code>journalctl</code> · cifras en formato
español (coma decimal, punto de miles).</p>
</body></html>
"""
    (dest / "index.html").write_text(html)
    return html


# ------------------------------------------------------------ fichas y auxiliares
def relativise_links(path: Path, dest: Path) -> int:
    """Absolute `/fichas/...` links break a subpath deployment (GitHub Pages).

    `depth` is measured against the DESTINATION ROOT, not against the file's own
    parent: measuring against the parent always yields 1 part and therefore zero
    "../", so a ficha inside fichas/ linked to "index.html" and pointed at
    fichas/index.html. That produced 63 dead links in one build.
    """
    text = path.read_text()
    original = text
    depth = len(path.relative_to(dest).parts) - 1
    prefix = "../" * depth
    text = re.sub(r'href="(/fichas/[^"]+)"',
                  lambda m: f'href="{prefix}{m.group(1).lstrip("/")}"', text)
    text = text.replace('href="/#mapa"', f'href="{prefix}index.html#mapa"')
    text = text.replace('href="/#inventario"', f'href="{prefix}index.html#inventario"')
    text = text.replace('href="/#f-top"', f'href="{prefix}index.html"')
    text = text.replace('href="/index.html"', f'href="{prefix}index.html"')
    text = text.replace('href="/opcion1.html"', f'href="{prefix}opcion1.html"')
    text = text.replace('href="/mapa-completo.html"', f'href="{prefix}mapa_completo.html"')
    if text != original:
        path.write_text(text)
        return 1
    return 0


def build_fichas(dest: Path) -> tuple[int, int]:
    fichas_dest = dest / "fichas"
    fichas_dest.mkdir(exist_ok=True)
    changed = copied = 0
    for source in sorted((HERE / "fichas").glob("*.html")):
        target = fichas_dest / source.name
        target.write_text(source.read_text())
        copied += 1
    for target in fichas_dest.glob("*.html"):
        changed += relativise_links(target, dest)
    return copied, changed


def build_aux(dest: Path) -> list[str]:
    made = []
    now = datetime.now().astimezone().replace(microsecond=0)

    # ficha ampliada del crédito fiscal
    source = HERE / "opcion1_credito_fiscal_id.html"
    if source.is_file():
        text = source.read_text()
        text = text.replace('href="/#mapa"', 'href="index.html#mapa"')
        text = text.replace('href="/#inventario"', 'href="index.html#inventario"')
        text = text.replace('href="/#f-top"', 'href="index.html"')
        text = text.replace('href="/index.html"', 'href="index.html"')
        text = text.replace('href="/fichas/', 'href="fichas/')
        (dest / "opcion1.html").write_text(text)
        made.append("opcion1.html")

    # página de navegación
    mapa = f"""<!-- OKF-METADATA
---
type: Navigation Page
title: "Mapa de financiación — vista completa"
description: "Contenedor del mapa de financiación en la vista estática publicable. Sin JavaScript."
status: verified
generated: {now.isoformat()}
source:
  - "accounting/mapa_financiacion.md (26 vías con fuente y fecha)"
  - "accounting/fichas/*.html"
verified: {now.date().isoformat()}
stale_after: {data.RESET_AT}
---
-->
<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Mapa de financiación</title>
<style>body{{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:24px auto;max-width:1000px}}a{{color:#7dd3fc}}</style>
</head><body>
<p><a href="index.html">← volver al dashboard</a></p>
<h1>🗺️ Mapa de financiación — 26 vías</h1>
<p>El mapa completo con la tabla de las 26 vías está en el dashboard:
<a href="index.html#mapa">ver la sección del mapa en el inicio</a>.</p>
<p>Fichas individuales: <a href="fichas/1-nlnet-restack.html">#1 NLnet/Restack</a> ·
<a href="opcion1.html">Crédito fiscal I+D+i (ficha ampliada)</a> ·
<a href="fichas/14-credito-fiscal.html">#14 crédito fiscal</a></p>
</body></html>
"""
    (dest / "mapa_completo.html").write_text(mapa)
    made.append("mapa_completo.html")

    favicon = HERE / "assets" / "favicon_conta.svg"
    if favicon.is_file():
        shutil.copy(favicon, dest / "favicon.svg")
        made.append("favicon.svg")
    return made


# ------------------------------------------------------------------------ main
def main(argv: list[str]) -> int:
    dest = Path(argv[argv.index("--dest") + 1]) if "--dest" in argv else DEFAULT_DEST
    dest.mkdir(parents=True, exist_ok=True)

    quote = data.live_quota()
    if quote is None:
        print("sin lectura viva del presupuesto: no se publica una cifra inventada",
              file=sys.stderr)
        return 1
    plan = data.load_plan()

    # Embedding uses the same tool as everything else, but WITHOUT the manifest
    # side effect: the published tree is generated output, and an index of files
    # this same run rewrites is stale before it is committed. It also mislabelled
    # .md/.html as "en frames", which is nonsense for text files.
    import okf

    def stamp(path: Path, meta: dict) -> None:
        okf.stamp_binary(path, meta, update_manifest=False)

    # A manifest here would be self-defeating: it hashes files this same run
    # rewrites, so it is stale before it is committed, and it labels .md/.html as
    # "en frames". The publishable tree does not need an index of itself.
    stale_manifest = dest / "OKF-MANIFEST.md"
    if stale_manifest.is_file():
        stale_manifest.unlink()

    titles = build_charts(dest, stamp)
    build_index(dest, quote, plan)
    copied, changed = build_fichas(dest)
    made = build_aux(dest)

    print(f"generado en {dest}")
    print(f"  index.html · {len(titles)} gráficos con OKF embebido")
    print(f"  fichas: {copied} copiadas, {changed} con enlaces relativizados")
    print(f"  auxiliares: {', '.join(made)}")
    print(f"  cuota publicada: {es(quote['percent'])} % del ciclo {plan['cycle_day']}/{plan['cycle_days']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
