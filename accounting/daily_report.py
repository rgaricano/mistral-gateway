#!/usr/bin/env python3
# OKF-METADATA
# type: Tool
# title: "daily_report.py — parte diario de la suscripción"
# description: "Genera el informe diario de la SUB con datos medidos: cuota, presupuesto, ritmo, agotamiento y tokens. Idempotente por día: no pisa un informe ya existente salvo --force."
# status: verified
# generated: 2026-11-20T21:40:00+01:00
# source:
#   - "accounting/data.py (live_quota, load_plan, allowance_series, daily_tokens)"
#   - "usage.db (tokens por día, registrado del proveedor)"
#   - "journalctl --user -u mistral-gateway (serie de allowance)"
# verified: 2026-11-20
# stale_after: 2027-06-30
"""Parte diario de la suscripción Mistral Vibe.

Rutina fijada: al inicio y/o al final de sesión debe existir un informe del día.
Si no existe, este comando lo crea con datos medidos — nunca estimados.

    python3 accounting/daily_report.py            # crea el de hoy si no existe
    python3 accounting/daily_report.py --force    # lo reescribe con los datos actuales

Salida: accounting/informes/YYYY-MM-DD.md

Por qué un script y no "acordarse": una rutina que depende de la memoria se
pierde el día que hay prisa, y justo ese día es cuando hace falta el dato.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data

OUT_DIR = HERE / "informes"

MES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
       7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre",
       12: "diciembre"}


def es_num(value: float, decimals: int = 2) -> str:
    """REGLA #1: coma decimal, punto de miles."""
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build(today: date) -> str:
    quota = data.live_quota()
    plan = data.load_plan()
    eur_point = data.euro_per_quota_point()
    budget = data.BUDGET_EUR
    price = data.SUBSCRIPTION_PRICE_EUR

    if quota is None:
        # exit 1: refusing is a failure, not a success. A script that declines to
        # do its job and still reports 0 breaks any caller automating the routine.
        print("sin lectura viva del presupuesto: no se inventa el parte", file=sys.stderr)
        raise SystemExit(1)

    pct = quota["percent"]
    used = pct / 100 * budget
    free = budget - used
    pace = plan["recent_pts_day"]
    runway = data.days_until_exhausted(pct, pace)
    series = data.allowance_series()
    tokens = data.daily_tokens()
    today_tokens = next((t for t in tokens if t["day"] == today.isoformat()), None)
    now = datetime.now().astimezone().replace(microsecond=0)

    delta_today = None
    if len(series) >= 2 and series[-1][0] == today.isoformat():
        delta_today = round(series[-1][1] - series[-2][1], 2)

    lines = []
    lines.append("---")
    lines.append("type: Daily Report")
    lines.append(f'title: "Parte diario de la suscripción — {today.isoformat()}"')
    lines.append('description: "Estado medido de la cuota Vibe: consumo, ritmo, agotamiento y tokens del día. Cifras leídas del proveedor, no estimadas."')
    lines.append("tags: [suscripción, cuota, parte-diario]")
    lines.append("status: verified")
    lines.append(f"generated: {now.isoformat()}")
    lines.append("source:")
    lines.append('  - "read_quota() sobre la API del plan (lectura viva)"')
    lines.append('  - "usage.db (tokens por día, registrado del proveedor)"')
    lines.append('  - "journalctl --user -u mistral-gateway (serie de allowance)"')
    lines.append(f"verified: {today.isoformat()}")
    lines.append(f"stale_after: {today.replace(day=min(today.day + 1, 28)).isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append(f"# Parte diario — {today.day} de {MES[today.month]} de {today.year}")
    lines.append("")
    lines.append("## Estado de la cuota")
    lines.append("")
    lines.append("| Concepto | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Cuota usada | **{es_num(pct)} %** |")
    lines.append(f"| Presupuesto consumido | {es_num(used)} € de {es_num(budget, 0)} € |")
    lines.append(f"| Presupuesto libre | {es_num(free)} € |")
    lines.append(f"| Ciclo | día {plan['cycle_day']} de {plan['cycle_days']} · quedan {plan['days_left']} días |")
    lines.append(f"| Reset | {data.RESET_AT} |")
    lines.append("")
    if delta_today is not None:
        lines.append(f"Consumo de hoy: **{es_num(delta_today)} pp** "
                     f"({es_num(delta_today * eur_point)} € de suscripción).")
        lines.append("")
    lines.append("## Ritmo y proyección")
    lines.append("")
    lines.append("| Concepto | Valor |")
    lines.append("|---|---|")
    lines.append(f"| Ritmo reciente | {es_num(pace)} pp/día = {es_num(pace * eur_point)} € suscr./día |")
    lines.append(f"| Ritmo requerido al reset | {es_num(plan['required_pts_day'])} pp/día |")
    if runway is not None:
        margin = runway - plan["days_left"]
        # singular/plural and REGLA #1 decimal comma both matter here: "1 días" and
        # "0.4 meses" are the kind of slip that makes a reader distrust the figures.
        day_word = "día" if round(margin) == 1 else "días"
        verdict = ("margen sobre el reset: "
                   + (f"**{round(margin)} {day_word}**" if margin >= 0
                      else f"**se agota {round(abs(margin))} {day_word} ANTES**"))
        lines.append(f"| Agotamiento al ritmo actual | {runway:.0f} días "
                     f"({es_num(runway / 30, 1)} meses) · {verdict} |")
    lines.append(f"| Escalas | 1 pp = {es_num(budget / 100)} € de presupuesto = {es_num(eur_point, 4)} € de suscripción |")
    lines.append("")
    lines.append("## Serie medida")
    lines.append("")
    lines.append("| Día | Cuota acumulada | Δ del día | Presupuesto usado |")
    lines.append("|---|---|---|---|")
    prev = 0.0
    for day, value in series:
        delta = value - prev
        prev = value
        lines.append(f"| {day} | {es_num(value)} % | {es_num(delta)} pp | {es_num(value / 100 * budget)} € |")
    lines.append("")
    lines.append("## Tokens")
    lines.append("")
    if today_tokens:
        lines.append(f"Hoy: **{es_num(today_tokens['tokens'], 0)} tokens** "
                     f"en {es_num(today_tokens['requests'], 0)} peticiones "
                     f"({es_num(today_tokens['cached'], 0)} en caché).")
        lines.append("")
    lines.append("| Día | Tokens | Peticiones | Caché |")
    lines.append("|---|---|---|---|")
    for item in tokens[-7:]:
        lines.append(f"| {item['day']} | {es_num(item['tokens'], 0)} | "
                     f"{es_num(item['requests'], 0)} | {es_num(item['cached'], 0)} |")
    lines.append("")
    lines.append("## Notas")
    lines.append("")
    lines.append("- Cifras leídas del proveedor; la cuota es la lectura viva del presupuesto, no una estimación.")
    lines.append("- Presupuesto = 255 € incluidos por ciclo; suscripción = "
                 f"{es_num(price)} €/mes. Las dos escalas se declaran por separado a propósito: "
                 "mezclarlas produce un error de "
                 f"{es_num(budget / price)}x (está documentado en `data.py`).")
    lines.append("- El guard es el suelo, no la prueba: una persona verifica antes de decidir con una cifra.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    force = "--force" in argv
    today = date.today()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUT_DIR / f"{today.isoformat()}.md"

    if target.is_file() and not force:
        print(f"ya existe el parte de hoy: {target}")
        print("usa --force para reescribirlo con los datos actuales")
        return 0

    text = build(today)
    target.write_text(text)
    print(f"parte escrito: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
