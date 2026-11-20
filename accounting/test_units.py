"""Regression checks for the quota-unit conversion.

Guards the bug found 19-nov-2026: euro_per_quota_point() divided 18,14 by the
euro budget (255) while the plan's `pts` are PERCENTAGE points (0-100), which
reported every "EUR of subscription per day" figure 2,55x too low.
Run: python3 accounting/test_units.py
"""
# OKF-METADATA
# ---
# type: Test
# title: "Guard de unidades cuota↔€"
# description: "Verifica que 1 pp equivale al precio/100 y no al precio/255, y que el plan y la anotación usan la misma escala."
# status: draft
# generated: 2026-11-20T00:51:26+01:00
# source:
# - "accounting/data.py"
# verified: 2026-11-20
# stale_after: 2027-06-30
# ---
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data

PRICE = data.SUBSCRIPTION_PRICE_EUR      # 18,14
BUDGET = data.BUDGET_EUR                 # 255.0


def test_point_is_percentage_scale():
    """1 pp must equal 1% of the budget in subscription terms."""
    expected = PRICE * (1.0 / 100.0)     # 18,14 / 100
    actual = data.euro_per_quota_point()
    assert abs(actual - expected) < 1e-9, f"{actual} != {expected} (wrong divisor again?)"
    # and it must NOT be the old, wrong value
    assert abs(actual - PRICE / BUDGET) > 1e-6, "regressed to dividing by the euro budget"


def test_full_cycle_conversion_is_consistent():
    """100 pp of quota must map to exactly the subscription price."""
    assert abs(100 * data.euro_per_quota_point() - PRICE) < 1e-6


def test_plan_fields_use_the_same_scale():
    plan = data.load_plan()
    eur_per_pp = data.euro_per_quota_point()
    for key in ("required_eur_day", "suggested_eur_day", "required_pts_day", "suggested_pts_day"):
        assert key in plan, f"missing {key} in load_plan()"
    # required_eur_day must be required_pts_day * eur_per_pp (same scale end to end)
    assert abs(plan["required_eur_day"] - plan["required_pts_day"] * eur_per_pp) < 1e-6


def test_annotation_is_generated_not_hardcoded():
    """The chart annotation must be built from the value, never a literal 18,14/255."""
    src = (Path(__file__).resolve().parent / "web_dashboard.py").read_text()
    assert "18,14 € / 255 €" not in src, "hardcoded unit text reintroduced"
    assert "EUR_PER_POINT:.4f" in src, "annotation no longer interpolates the computed value"


def test_series_ends_today_with_live_value():
    """The allowance series must end on today and with the live reading.

    A hand-written series is a cache with no expiry: on 20-nov the series stopped
    at 19-nov/15,45 % while the live budget read 18,58 %, so the dashboard showed
    yesterday's figure as today's. A guard that only checks 'the chart has points'
    would have passed. This one checks that the last point IS today and that its
    value IS the live read.
    """
    series = data.allowance_series()
    assert series, "empty allowance series"
    last_day, last_pct = series[-1]

    live = data.live_quota()
    if live is None or live.get("percent") is None:
        # No live reading (no credentials, e.g. a fresh clone or CI). The series
        # can only carry the recorded history, so a series ending earlier is the
        # honest state, not a defect. What must NOT happen is pretending: the
        # value stays as recorded and the caller can see there is no live point.
        assert last_day <= date.today().isoformat(), (
            f"series ends in the future ({last_day}) — that cannot be a measurement")
        return

    assert last_day == date.today().isoformat(), (
        f"series ends on {last_day}, not today, although a live reading is "
        f"available — the dashboard would show stale data")
    # Tolerance, not equality: the quota advances while the test runs, so a
    # second live read can already be a few hundredths higher than the value the
    # series captured moments earlier. Demanding < 0.01 made the suite fail on a
    # race, not on a defect. Two calls ~1s apart cannot legitimately differ by
    # more than a fraction of a point; a stale series differs by whole points.
    drift = live["percent"] - last_pct
    assert -0.01 <= drift <= 0.2, (
        f"series ends at {last_pct} % but the live budget reads {live['percent']:.2f} % "
        f"(drift {drift:+.2f} pp) — either stale or reading a different source")


def test_plan_uses_live_reading_not_stale_series():
    """plan['current_pct'] must track the live read, not a stale series tail."""
    plan = data.load_plan()
    live = data.live_quota()
    if live and live.get("percent") is not None:
        assert abs(plan["current_pct"] - live["percent"]) < 0.01, (
            f"plan says {plan['current_pct']} % but live budget says {live['percent']:.2f} %")


def test_exhaustion_is_in_days_not_budget_suscription_mix():
    """Runway must be computed on ONE euro scale, never mixing the two.

    Real defect (21-nov, spotted by Ricardo): the dashboard reported "agotamiento
    al ritmo reciente: 7,6 meses" when the truth was 16 days. The line divided
    free euros of BUDGET (255 €) by a pace in SUBSCRIPTION euros (18,14 €), which
    silently scales the result by BUDGET/PRICE = 14,06x.

    A guard that only checked "the number is positive" or "it is < 12 months"
    would pass the wrong value. This one checks the invariants that make the
    figure meaningful: the pp form and the euro form must agree exactly, and the
    result must be days of remaining allowance at that pace.
    """
    plan = data.load_plan()
    pct = plan["current_pct"]
    pace = plan["recent_pts_day"]
    days = data.days_until_exhausted(pct, pace)
    assert days is not None, "sin ritmo medible debería devolver None, no 0 ni inf"
    assert days > 0, f"agotamiento no positivo: {days}"

    # (a) the percentage-point form and the budget-euro form MUST agree.
    #     If someone divides by the subscription euro per point instead, this breaks.
    free_budget_eur = (100 - pct) / 100 * data.BUDGET_EUR
    euro_form = free_budget_eur / (pace * data.budget_eur_per_quota_point())
    assert abs(days - euro_form) < 1e-9, (
        f"las dos formas discrepan: pp={days:.4f} días vs €={euro_form:.4f} días "
        f"(factor {days / euro_form:.2f}x — ¿se mezclaron las escalas?)")

    # (b) the subscription-euro form gives the WRONG value: it must NOT match,
    #     which is the whole point. This pins the bug rather than forgetting it.
    wrong = free_budget_eur / (pace * data.euro_per_quota_point())
    factor = data.BUDGET_EUR / data.SUBSCRIPTION_PRICE_EUR
    assert abs(wrong / days - factor) < 0.01, (
        f"el error conocido debería ser {factor:.2f}x, se midió {wrong / days:.2f}x")


def test_two_euro_scales_are_explicit():
    """The two euro-per-point scales must both exist and differ by BUDGET/PRICE."""
    sub = data.euro_per_quota_point()
    budget = data.budget_eur_per_quota_point()
    assert sub != budget, "las dos escalas no pueden ser el mismo número"
    assert abs((budget / sub) - (data.BUDGET_EUR / data.SUBSCRIPTION_PRICE_EUR)) < 1e-9, \
        f"el cociente entre escalas no es BUDGET/PRICE: {budget / sub}"
    assert abs(budget - data.BUDGET_EUR / 100) < 1e-12, "budget_eur_per_quota_point != 255/100"


def test_web_dashboard_does_not_mix_scales():
    """The rendered source must not divide budget euros by subscription euros.

    The bug lived in an f-string, where no type checker or unit test reaches.
    This pins the shape of the expression: the runway must come from
    days_until_exhausted(), not from a free_eur / (...) division.
    """
    src = (Path(__file__).resolve().parent / "web_dashboard.py").read_text()
    assert "data.days_until_exhausted(" in src, \
        "el dashboard dejó de usar la función con nombre para el agotamiento"
    # Only look at CODE, not comments: the comment explaining the old bug quotes
    # the very expression we forbid, and a guard that fires on its own
    # documentation is a guard that will be deleted in frustration.
    code_lines = [ln for ln in src.splitlines() if not ln.lstrip().startswith("#")]
    code = "\n".join(code_lines)
    assert "free_eur / (rec_pts * EUR_PER_POINT)" not in code, \
        "volvió la división que mezcla € de presupuesto con € de suscripción (14,06x)"


def test_runway_is_not_wildly_off_from_the_reset():
    """Sanity: at the recent pace the runway must be the same order as the cycle.

    This is the check that would have caught 7,6 months at a glance: the cycle is
    days, not months, so a runway of months means a unit error somewhere.
    """
    plan = data.load_plan()
    days = data.days_until_exhausted(plan["current_pct"], plan["recent_pts_day"])
    if days is None:
        return
    assert days < 365, f"agotamiento de {days:.0f} días: demasiado para un ciclo de ~17-30 días"
    months = days / 30
    assert months < 12, f"agotamiento de {months:.1f} meses: huele a mezcla de escalas"


def test_spanish_formatter_covers_time_units():
    """REGLA #1: a figure followed by meses/días must also use decimal comma.

    Real leak (21-nov): the formatter only converted numbers before €, %, pp, x,
    so "(0.5 meses)" shipped with an English decimal point straight into the
    dashboard. The rule is about EVERY published figure, not only money.
    """
    import web_dashboard as w
    cases = {
        "(0.5 meses)": "(0,5 meses)",
        "16 días": "16 días",
        "1.5 días": "1,5 días",
        "7.6 meses": "7,6 meses",
        "18.14 €": "18,14 €",
        "7.24 %": "7,24 %",
        "255.000 €": "255.000 €",          # already Spanish thousands: keep
        "0.1814 €": "0,1814 €",
    }
    for raw, expected in cases.items():
        got = w._es_numbers(raw)
        assert got == expected, f"REGLA #1: {raw!r} → {got!r}, se esperaba {expected!r}"


# How much the report may lag the live reading before it counts as stale.
# ~0,5 pp is a few minutes of work; anything more means it is not "today's report".
FRESHNESS_PP = 0.5


def test_daily_report_exists_for_today():
    """The daily part of the subscription must exist for TODAY.

    Fixed routine (Ricardo, 20-nov): at session start and/or end there must be a
    report for the day, generated if missing. A routine that lives only in
    memory is missed exactly on the busy days, which are the days the figure is
    needed. This turns the routine into something the suite enforces.
    """
    import subprocess
    here = Path(__file__).resolve().parent
    today = date.today()
    target = here / "informes" / f"{today.isoformat()}.md"
    live = data.live_quota()
    has_live = live is not None and live.get("percent") is not None
    if not has_live and not target.is_file():
        # Without a live reading the report cannot be generated (by design: it
        # must not invent figures), so the routine is not applicable here rather
        # than failing. A committed report still gets checked below.
        return
    if not target.is_file():
        # generate it, exactly as the routine says, then assert it worked
        run = subprocess.run([sys.executable, str(here / "daily_report.py")],
                             capture_output=True, text=True)
        assert run.returncode == 0, f"daily_report.py falló: {run.stderr[:300]}"
    assert target.is_file(), f"no hay parte diario de hoy: {target}"

    text = target.read_text()
    assert f"verified: {today.isoformat()}" in text, "el parte no está fechado hoy"

    # Freshness, not exact equality: the quota moves continuously, so demanding an
    # exact match would make this test unstable and force a rewrite on every call.
    # The routine is "keep today's report current", so a stale report is refreshed
    # the same way a missing one is created.
    live = data.live_quota()
    if live and live.get("percent") is not None:
        live_pct = live["percent"]
        reported = [float(m.replace(",", ".")) for m in
                    __import__("re").findall(r"Cuota usada \| \*\*([\d,]+) %\*\*", text)]
        assert reported, "el parte no declara la cuota usada"
        drift = live_pct - reported[0]
        assert drift >= -0.01, (
            f"el parte dice {reported[0]} % pero la lectura viva es menor ({live_pct:.2f} %): "
            "la cuota no decrece, el parte miente")
        if drift > FRESHNESS_PP:
            # Say it out loud: a test that silently repairs its own subject tells
            # nobody that the routine had been missed.
            print(f"  [rutina] parte desfasado ({reported[0]} % vs {live_pct:.2f} %): "
                  f"se regenera", file=sys.stderr)
            run = subprocess.run([sys.executable, str(here / "daily_report.py"), "--force"],
                                 capture_output=True, text=True)
            assert run.returncode == 0, f"no se pudo refrescar: {run.stderr[:200]}"
            text = target.read_text()
            reported = [float(m.replace(",", ".")) for m in
                        __import__("re").findall(r"Cuota usada \| \*\*([\d,]+) %\*\*", text)]
            assert live_pct - reported[0] <= FRESHNESS_PP, (
                f"el parte sigue desfasado tras refrescar: {reported[0]} % vs {live_pct:.2f} %")


def test_daily_report_has_no_english_decimals():
    """REGLA #1 applies to the report too: 0.4 meses is a defect, not a detail."""
    import re
    here = Path(__file__).resolve().parent
    reports = sorted((here / "informes").glob("*.md")) if (here / "informes").is_dir() else []
    bad = []
    for r in reports:
        for line in r.read_text().splitlines():
            # a decimal point between digits, followed by a unit
            if re.search(r"\d+\.\d+\s*(€|%|pp|meses|mes|días|día|x)\b", line):
                bad.append(f"{r.name}: {line.strip()[:70]}")
    assert not bad, "decimales ingleses en el parte:\n" + "\n".join(bad)



def test_report_wording_agrees_with_the_numbers():
    """Singular/plural must agree with the number actually printed.

    Real defect (20-nov): the word was computed from the signed margin while the
    sentence printed abs(margin), so a margin of -1 rendered "se agota 1 días
    ANTES". A reader who spots "1 días" has reason to doubt every other figure in
    the same table, which is why this is worth a test and not a typo fix.
    """
    import re
    import daily_report
    here = Path(__file__).resolve().parent
    reports = sorted((here / "informes").glob("*.md"))
    assert reports, "no hay informes que validar"
    bad = []
    for r in reports:
        for line in r.read_text().splitlines():
            # a numeral 1 (or -1) immediately followed by a plural time unit
            if re.search(r"(?<![\d,.])1\s+(días|meses)\b", line):
                bad.append(f"{r.name}: {line.strip()[:90]}")
            # and the reverse: a plural-looking number with a singular noun
            if re.search(r"(?<![\d,.])(2|3|4|5|6|7|8|9|\d\d+)\s+(día|mes)\b", line):
                bad.append(f"{r.name}: {line.strip()[:90]}")
    assert not bad, "concordancia singular/plural rota:\n" + "\n".join(bad)


def test_static_site_is_current_and_coherent():
    """The publishable tree must be current, script-free and link-coherent.

    The tree in `gentle-companion/docs/accounting/` is what gets published, and
    until now it was built by hand with ad-hoc commands — so it silently served
    figures from hours earlier (20,40 % published while the live reading was
    23,36 %). A site that shows yesterday as today is the same defect as the
    stale allowance series, in a different costume.

    Freshness is bounds-checked, not compared exactly: the quota moves
    continuously and an exact match would make this test unstable. When stale it
    rebuilds and says so.
    """
    import re
    import subprocess
    here = Path(__file__).resolve().parent
    site = Path.home() / "Trabajo" / "IAI" / "gentle-companion" / "docs" / "accounting"
    if not site.is_dir():
        return  # the publishable tree is not present in this checkout

    index = site / "index.html"
    live = data.live_quota()
    has_live = live is not None and live.get("percent") is not None

    def published_pct() -> float | None:
        if not index.is_file():
            return None
        found = re.search(r"\*\*?([\d,]+) %\*\*? = ", index.read_text())
        if not found:
            found = re.search(r"[^\d,]([\d,]+) % = ", index.read_text())
        return float(found.group(1).replace(",", ".")) if found else None

    stale = False
    if has_live:
        shown = published_pct()
        if shown is None:
            stale = True
        elif abs(live["percent"] - shown) > FRESHNESS_PP:
            stale = True

    if stale or not index.is_file():
        if not has_live:
            return  # cannot rebuild without a live read, by design
        print("  [rutina] sitio estático desfasado: se regenera", file=sys.stderr)
        run = subprocess.run([sys.executable, str(here / "build_static_site.py")],
                             capture_output=True, text=True)
        assert run.returncode == 0, f"build_static_site.py falló: {run.stderr[:400]}"

    text = index.read_text()
    # zero scripts, zero external chart dependencies
    assert "<script" not in text, "el sitio publicado contiene <script>"
    assert not re.search(r"https?://(cdn|cdnjs|unpkg|plotly)", text), \
        "el sitio publicado depende de un CDN para los gráficos"

    # the charts are real images carrying their own provenance
    from PIL import Image
    for name in ("chart-1.png", "chart-2.png", "chart-3.png"):
        chart = site / name
        assert chart.is_file(), f"falta {name} en el sitio publicado"
        assert "OKF-METADATA" in (Image.open(chart).info or {}), \
            f"{name} no lleva su OKF embebido"

    # the generated tree must not carry a manifest of itself: its hashes would be
    # stale the moment the site is rebuilt, and it labelled .md/.html as "en frames"
    assert not (site / "OKF-MANIFEST.md").is_file(), (
        "el árbol publicado lleva un OKF-MANIFEST.md de sí mismo: nace obsoleto")

    # every local reference resolves (this caught 63 dead links in one build)
    import os
    dead = []
    for root, _, files in os.walk(site):
        for f in files:
            if not f.endswith(".html"):
                continue
            page = Path(root) / f
            for ref in re.findall(r'(?:src|href)="([^"#][^"]*)"', page.read_text()):
                if ref.startswith(("http", "mailto")):
                    continue
                target = (Path(root) / ref.split("#")[0]).resolve()
                if not target.exists():
                    dead.append(f"{page.relative_to(site)} → {ref}")
    assert not dead, f"enlaces rotos en el sitio publicado: {dead[:5]}"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
