#!/usr/bin/env python3
"""The static paths must not escape their own directory.

Guards the defect found 20-nov-2026 while evaluating a request to host a new
subdirectory: `/fichas/` joined the RAW request path onto the project directory,
so `/fichas/../../gateway.py` returned 200 and served any file the process could
read. `startswith("/fichas/")` is a prefix check, and a prefix check says nothing
about where the path ends up.

The test attacks with the forms that actually bypass naive filters: dot-dot,
percent-encoded dot-dot, and an absolute path.
"""
# OKF-METADATA
# ---
# type: Test
# title: "Guard de path traversal en las rutas estáticas"
# description: "Verifica que /fichas/ no puede salir de su directorio con .., %2e%2e ni rutas absolutas."
# status: verified
# generated: 2026-11-20T23:30:00+01:00
# source:
#   - "accounting/web_dashboard.py (bloque /fichas/)"
# verified: 2026-11-20
# stale_after: 2027-06-30

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _resolve(path_only: str):
    """Replicate the handler's resolution so the rule can be tested without I/O."""
    base = (HERE / "fichas").resolve()
    candidate = (base / path_only[len("/fichas/"):]).resolve()
    inside = candidate == base or base in candidate.parents
    return candidate if inside else None


def test_traversal_is_refused():
    """No escaping form may resolve to anything outside the fichas directory."""
    attacks = [
        "fichas/../data.py",
        "fichas/../../gateway.py",
        "fichas/../../../etc/passwd",
        "fichas/../web_dashboard.py",
        "fichas/./../../data.py",
        "fichas/subdir/../../data.py",
        "fichas//../../gateway.py",
    ]
    base = (HERE / "fichas").resolve()
    for attack in attacks:
        got = _resolve("/" + attack)
        assert got is None, f"{attack} resolvió a {got}, fuera de {base}"


def test_encoded_traversal_is_refused():
    """Percent-encoded dot-dot must not slip through after unquoting."""
    from urllib.parse import unquote
    attacks = [
        "fichas/%2e%2e/data.py",
        "fichas/%2e%2e%2f%2e%2e/gateway.py",
    ]
    for attack in attacks:
        decoded = "/" + unquote(attack)
        got = _resolve(decoded)
        assert got is None, f"{attack} (decodificado {decoded}) resolvió a {got}"


def test_absolute_path_is_refused():
    """An absolute path must not be able to name a file anywhere."""
    base = (HERE / "fichas").resolve()
    got = _resolve("/fichas//etc/passwd")
    assert got is None or base in got.parents, f"ruta absoluta escapó: {got}"


def test_legitimate_fichas_still_serve():
    """The fix must not break the real pages (a guard that blocks everything is useless)."""
    real = sorted(p.name for p in (HERE / "fichas").glob("*.html"))
    assert real, "no hay fichas que probar"
    for name in real[:5]:
        got = _resolve(f"/fichas/{name}")
        assert got is not None, f"{name} dejó de servirse"
        assert got.is_file(), f"{name} no resuelve a un fichero"


def test_handler_uses_resolved_containment_not_a_prefix():
    """Pin the shape: a startswith-only check on the raw path is the bug."""
    src = (HERE / "web_dashboard.py").read_text()
    assert 'base in candidate.parents' in src, \
        "desapareció la comprobación de contención por ruta resuelta"
    assert 'Path(__file__).resolve().parent / self.path.lstrip("/")' not in src, \
        "volvió a unirse la ruta cruda del cliente al directorio del proyecto"


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
