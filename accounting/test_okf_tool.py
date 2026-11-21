#!/usr/bin/env python3
"""Round-trip tests for okf.py — the read/write tool must agree with the guard.

Why this exists: okf.py is now the only way we write OKF headers, so a defect in
it would corrupt every document silently. The rule that matters is not "the tool
runs" but "whatever the tool writes, check_okf.py accepts" — plus the reverse,
that a file with no header is rejected. The first version of okf.py had a parser
that returned None for every file and printed "(sin cabecera)" for headers that
were plainly there; a smoke test would have passed it.

Run: python3 accounting/test_okf_tool.py
"""
# OKF-METADATA
# ---
# type: Test
# title: "Guard de la herramienta okf.py (ida y vuelta)"
# description: "Verifica que okf.py escribe cabeceras que el validador acepta, que reemplaza en vez de duplicar y que respeta el contenido original."
# status: verified
# generated: 2026-11-20T02:45:00+01:00
# source:
#   - "accounting/okf.py"
#   - "accounting/check_okf.py"
# verified: 2026-11-20
# stale_after: 2027-06-30

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_okf
import okf

SAMPLES = {
    "t.md": ("md", "# Título\n\nContenido intacto.\n"),
    "t.html": ("html", "<!DOCTYPE html>\n<html><body><p>prueba</p></body></html>\n"),
    "t.svg": ("svg", '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>\n'),
    "t.py": ("py", "import sys\nprint('hola')\n"),
    "t.json": ("json", '{"a": 1}\n'),
}


def _scratch():
    tmp = tempfile.mkdtemp(prefix="okftest-")
    for name, (_, body) in SAMPLES.items():
        (Path(tmp) / name).write_text(body)
    return Path(tmp)


def test_write_then_validate_roundtrip():
    """Whatever okf.py writes must satisfy check_okf.py. Both directions."""
    root = _scratch()
    for name, (kind, _) in SAMPLES.items():
        path = root / name
        okf.write_okf(path, {"type": "Test", "title": f"Prueba {name}", "status": "verified",
                             "source": "prueba automática"})
        problems = check_okf.validate(path, kind)
        assert not problems, f"{name}: el validador rechaza lo que okf.py escribió: {problems}"


def test_read_returns_what_was_written():
    """A written header must read back with the same values (no silent loss)."""
    root = _scratch()
    for name in SAMPLES:
        path = root / name
        okf.write_okf(path, {"type": "Chart", "title": "Título con acentos: áéíóú",
                             "status": "verified", "source": "origen de prueba"})
        meta = okf.read_okf(path)
        assert meta is not None, f"{name}: no se pudo releer la cabecera recién escrita"
        assert meta.get("type") == "Chart", f"{name}: type perdido: {meta}"
        assert "acentos" in str(meta.get("title", "")), f"{name}: title perdido: {meta}"
        assert meta.get("source") == "origen de prueba", f"{name}: source perdido: {meta}"


def test_rewrite_replaces_and_never_duplicates():
    """Writing twice must leave ONE header, not two."""
    root = _scratch()
    for name, (kind, _) in SAMPLES.items():
        path = root / name
        okf.write_okf(path, {"type": "Test", "title": "primero", "status": "draft",
                             "source": "prueba automática"})
        okf.write_okf(path, {"type": "Test", "title": "segundo", "status": "verified"})
        # JSON keeps its header in a sibling file, not in the body
        text = path.with_suffix(".meta.json").read_text() if kind == "json" else path.read_text()
        if kind == "py":
            assert text.count("OKF-METADATA") == 1, f"{name}: bloque duplicado"
        elif kind == "html":
            assert text.count("OKF-METADATA") == 1, f"{name}: bloque duplicado"
            assert text.count("<!-- OKF-METADATA") == 1, f"{name}: comentario duplicado"
        elif kind == "md":
            fences = sum(1 for ln in text.splitlines() if ln.strip() == "---")
            assert fences == 2, f"{name}: {fences} fences, se esperaban 2 (cabecera + cierre)"
        assert "primero" not in text, f"{name}: el título anterior sobrevive (duplicado)"
        assert "segundo" in text, f"{name}: el título nuevo no se escribió"
        # the body must still be there. For SVG the marker line is split on
        # purpose (the header goes inside <svg>), so check the drawing survived.
        if kind == "svg":
            assert "<rect" in text, f"{name}: se perdió el dibujo original"
        elif kind == "json":
            assert path.read_text().strip() == SAMPLES[name][1].strip(), \
                f"{name}: el cuerpo JSON cambió al escribir la cabecera"
        else:
            original_body = SAMPLES[name][1].strip().splitlines()[-1]
            assert original_body in text, f"{name}: se perdió el contenido original"


def test_svg_stays_wellformed_xml():
    """The SVG header must never contain '--': XML forbids it inside a comment."""
    root = _scratch()
    path = root / "t.svg"
    okf.write_okf(path, {"type": "Test", "title": "a--b: título con guiones",
                         "status": "verified", "source": "prueba automática"})
    ET.parse(str(path))          # raises if not well-formed
    # the "--" is legal now: it lives in <metadata>, HTML-escaped, not in a comment
    tree = ET.parse(str(path))
    node = tree.find(".//{http://www.w3.org/2000/svg}metadata")
    assert node is not None, "no <metadata> element — the SVG header lost its home"
    assert "a--b" in (node.text or ""), f"el título no sobrevivió: {node.text!r}"


def test_python_shebang_survives():
    """In a script with a shebang, the OKF block goes AFTER it, not before."""
    root = _scratch()
    path = root / "t.py"
    path.write_text("#!/usr/bin/env python3\nimport sys\n")
    okf.write_okf(path, {"type": "Test", "title": "con shebang", "status": "verified",
                         "source": "prueba automática"})
    first = path.read_text().splitlines()[0]
    assert first.startswith("#!"), f"el shebang dejó de ser la primera línea: {first!r}"


def test_repeated_set_accumulates_sources():
    """`--set source=A --set source=B` must keep BOTH, not just the last one.

    This is the exact defect that already lost two of three NLnet sources once:
    duplicate `source:` keys in YAML keep only the last and the rest vanish with
    no error. The tool must build ONE key with a list instead.
    """
    root = _scratch()
    path = root / "multi.md"
    path.write_text("# multi\n")
    run = subprocess.run(
        [sys.executable, str(HERE / "okf.py"), "write", str(path),
         "--set", "type=Test", "--set", "title=multi", "--set", "status=verified",
         "--set", "source=primera", "--set", "source=segunda", "--set", "source=tercera"],
        capture_output=True, text=True)
    assert run.returncode == 0, f"write falló: {run.stderr}"
    text = path.read_text()
    header = text.split("---")[1] if text.startswith("---") else text
    assert header.count("source:") == 1, f"clave source duplicada: {header}"
    for value in ("primera", "segunda", "tercera"):
        assert value in header, f"se perdió la fuente {value!r}"
    meta = okf.read_okf(path)
    assert isinstance(meta.get("source"), list) and len(meta["source"]) == 3, \
        f"source no quedó como lista de 3: {meta.get('source')!r}"


def test_stamp_subcommand_accepts_the_same_flags_as_write():
    """`stamp` must parse every flag `write` does (--from among them).

    It did not: stamp was missing --from while sharing the code path that reads
    args.from_file, so `okf.py stamp x.png --set ...` crashed with AttributeError.
    write worked, stamp did not — a smoke test of "the tool runs" would pass.
    """
    from PIL import Image
    root = _scratch()
    png = root / "t.png"
    Image.new("RGBA", (8, 8), (255, 0, 0, 255)).save(png)
    run = subprocess.run(
        [sys.executable, str(HERE / "okf.py"), "stamp", str(png),
         "--set", "type=Icon", "--set", "title=prueba", "--set", "status=draft",
         "--set", "source=origen"],
        capture_output=True, text=True)
    assert run.returncode == 0, f"stamp falló: {run.stderr.strip()[:200]}"
    assert "AttributeError" not in run.stderr, f"stamp: {run.stderr.strip()[:200]}"
    meta = okf.read_okf(png)
    assert meta and meta.get("title") == "prueba", f"el OKF no quedó estampado: {meta}"
    # and the --from path must parse too, without crashing
    yaml_file = root / "hdr.yaml"
    yaml_file.write_text('type: "Icon"\ntitle: "desde yaml"\nstatus: "draft"\n')
    run2 = subprocess.run(
        [sys.executable, str(HERE / "okf.py"), "stamp", str(png), "--from", str(yaml_file)],
        capture_output=True, text=True)
    assert run2.returncode == 0, f"stamp --from falló: {run2.stderr.strip()[:200]}"


def test_missing_header_is_detected():
    """The tool must report a missing header as an error, not as empty success."""
    root = _scratch()
    path = root / "sin.md"
    path.write_text("sin cabecera alguna\n")
    assert okf.read_okf(path) is None, "leyó una cabecera que no existe"
    assert check_okf.validate(path, "md"), "el validador aceptó un fichero sin cabecera"
    run = subprocess.run([sys.executable, str(HERE / "okf.py"), "read", str(path)],
                         capture_output=True, text=True)
    assert run.returncode == 1, f"okf.py read no falló: exit={run.returncode}"


def test_cli_write_and_read_agree():
    """The command line path must behave like the library path."""
    root = _scratch()
    path = root / "cli.md"
    path.write_text("# cli\n")
    write = subprocess.run(
        [sys.executable, str(HERE / "okf.py"), "write", str(path),
         "--set", "type=Test", "--set", "title=desde el CLI", "--set", "status=verified"],
        capture_output=True, text=True)
    assert write.returncode == 0, f"write falló: {write.stderr}"
    read = subprocess.run([sys.executable, str(HERE / "okf.py"), "read", str(path)],
                          capture_output=True, text=True)
    assert read.returncode == 0, f"read falló: {read.stderr}"
    assert "desde el CLI" in read.stdout, f"el título no volvió: {read.stdout!r}"


def test_stamp_never_writes_into_another_trees_manifest():
    """Stamping a file in a foreign tree must NOT touch this project's manifest.

    Real defect (21-nov): `okf.py stamp /tmp/foreign/assets/icon.png` rewrote
    THIS project's assets/OKF-MANIFEST.md, injecting a stranger's hash into our
    index. Caught before the tool was spread team-wide; each member would have
    corrupted the others' manifests, which is the opposite of provenance.
    """
    import hashlib
    mine = HERE / "assets" / "OKF-MANIFEST.md"
    before = hashlib.sha256(mine.read_bytes()).hexdigest()

    # NOTE: the foreign tree must be its OWN temp root. Using _scratch() puts the
    # file in a shared temp dir whose sibling layout can resolve back to this
    # project, which made an earlier version of this test pass while the bug was
    # fully reproducible by hand. The setup must differ from the tools' own tree.
    root = Path(tempfile.mkdtemp(prefix="okf-foreign-"))
    foreign_assets = root / "assets"
    foreign_assets.mkdir()
    from PIL import Image
    png = foreign_assets / "icon.png"
    Image.new("RGBA", (16, 16), (10, 20, 30, 255)).save(png)

    run = subprocess.run(
        [sys.executable, str(HERE / "okf.py"), "stamp", str(png),
         "--set", "type=Icon", "--set", "title=ajeno", "--set", "status=draft"],
        capture_output=True, text=True)
    assert run.returncode == 0, f"stamp falló: {run.stderr[:300]}"

    after = hashlib.sha256(mine.read_bytes()).hexdigest()
    assert before == after, "el manifiesto de ESTE proyecto cambió al estampar un fichero ajeno"
    foreign_manifest = foreign_assets / "OKF-MANIFEST.md"
    assert foreign_manifest.is_file(), "no se creó el manifiesto en el árbol del fichero"
    assert "icon.png" in foreign_manifest.read_text(), "el manifiesto ajeno no lista su propio asset"
    assert "icon.png" not in mine.read_text(), "el asset ajeno se coló en nuestro índice"


def test_manifest_labels_rows_with_the_real_directory():
    """A manifest inside img/ must label its rows img/..., not assets/..."""
    import okf as _okf
    root = _scratch()
    img = root / "img"
    img.mkdir()
    from PIL import Image
    Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(img / "a.png")
    _okf.regenerate_manifest(img)
    manifest = img / "OKF-MANIFEST.md"
    assert manifest.is_file(), (
        "regenerate_manifest(dir) no escribió el manifiesto en el directorio indicado "
        "— está escribiendo en el árbol de la herramienta")
    text = manifest.read_text()
    # rows are bare filenames, relative to the manifest that lists them, so the
    # same row is correct wherever the tree is checked out
    assert "`a.png`" in text, f"el manifiesto no lista el asset: {text[-200:]}"
    assert "`assets/a.png`" not in text, "el manifiesto miente sobre su propia ruta"


def test_a_directory_target_is_its_own_assets_dir():
    """Passing a directory must not walk up to its parent (it did, once)."""
    import okf as _okf
    root = _scratch()
    img = root / "img"
    img.mkdir()
    assert _okf.assets_dir_for(img) == img, "un directorio no se reconoció como assets dir"
    from PIL import Image
    Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(img / "a.png")
    assert _okf.assets_dir_for(img / "a.png") == img, "la ruta del fichero no resolvió a su carpeta"


def test_secret_guard_covers_the_library_not_only_the_cli():
    """The credential refusal must live in the writers, not in main().

    Real defect (21-nov, found by ORQ asking about exit codes): the check was only
    in main(), so the CLI refused and the LIBRARY did not. Any code calling
    stamp_binary directly — build_static_site.py does — walked straight past it. A
    guard at the entry point is a door, not a lock.
    """
    from PIL import Image
    root = _scratch()
    png = root / "s.png"
    Image.new("RGBA", (8, 8), (1, 1, 1, 255)).save(png)

    cases = [
        {"type": "I", "title": "t", "api_key": "sk-abc123"},                 # named field
        {"type": "I", "title": "t", "note": "aB3xK9mP2qR7tY4wZ8nC5vB1xL6kJ3hG"},  # value shape
    ]
    for meta in cases:
        try:
            okf.stamp_binary(png, dict(meta))
        except ValueError:
            continue
        raise AssertionError(f"la librería escribió un secreto: {meta}")
        # a refusal that is not an exception would silently succeed here

    # md (write_okf) must refuse too
    md = root / "s.md"
    md.write_text("# x\n")
    try:
        okf.write_okf(md, {"type": "T", "title": "t", "token": "abcdef123456789012345678"})
        raise AssertionError("write_okf escribió un token")
    except ValueError:
        pass
    assert "token" not in md.read_text(), "el token llegó al fichero"

    # and a legitimate location reference must still work
    okf.write_okf(md, {"type": "T", "title": "t", "api_key": "env:MY_KEY"})
    assert "env:MY_KEY" in md.read_text()


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
