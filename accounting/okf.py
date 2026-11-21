#!/usr/bin/env python3
# OKF-METADATA
# ---
# type: Tool
# title: "okf.py — leer y escribir la cabecera OKF con un comando"
# description: "CLI única para de/codificar OKF en cualquier formato: md, html, svg, py, json, png, ico y gráficos Plotly. Reutiliza el validador de check_okf.py."
# status: verified
# generated: 2026-11-20T02:40:00+01:00
# source:
#   - "accounting/check_okf.py (validador y guard de binarios)"
#   - "accounting/decision_okf_binarios.md (decisión de las tres capas)"
# verified: 2026-11-20
# stale_after: 2027-06-30
"""okf.py — una sola puerta para leer y escribir cabeceras OKF.

El problema que resuelve: cada formato guarda su OKF de una forma distinta
(frontmatter YAML, comentario HTML, comentario XML sin `--`, bloque `#` en
Python, fichero hermano en JSON, chunk `iTXt` en PNG). Recordar seis variantes
garantiza que alguien se equivoque. Este comando las unifica.

USO
    python3 accounting/okf.py read   FICHERO            # imprime la cabecera
    python3 accounting/okf.py read   FICHERO --raw      # texto tal cual, sin parsear
    python3 accounting/okf.py write  FICHERO --set type=Chart --set title="..."
    python3 accounting/okf.py write  FICHERO --from cabecera.yaml
    python3 accounting/okf.py stamp  FICHERO            # binarios: embebe y actualiza el manifiesto
    python3 accounting/okf.py check                     # ejecuta el guard completo
    python3 accounting/okf.py manifest                  # regenera assets/OKF-MANIFEST.md
    python3 accounting/okf.py formats                   # tabla de soporte por formato

Todo `write` rellena `generated` y `verified` con la fecha de hoy si no se dan,
y REEMPLAZA la cabecera existente en vez de añadir una segunda.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
MANIFEST = ASSETS / "OKF-MANIFEST.md"


def assets_dir_for(path: Path | None = None) -> Path:
    """The directory that OWNS the file being stamped — and its manifest.

    A real cross-contamination defect forced this: stamping a PNG living in
    another tree still rewrote THIS project's manifest, writing a stranger's hash
    into our index. The manifest must belong to the tree the file lives in.

      - no path            -> this project's assets/ (the default)
      - path IS a directory -> that directory is the assets dir
      - path is a file      -> its own directory
    """
    if path is None:
        return ASSETS
    target = path.resolve()
    return target if target.is_dir() else target.parent


def manifest_for(path: Path | None = None) -> Path:
    return assets_dir_for(path) / "OKF-MANIFEST.md"

# Formatos que llevan el OKF dentro del propio fichero.
TEXT_KINDS = {".md": "md", ".html": "html", ".htm": "html", ".svg": "svg", ".py": "py"}
BINARY_READABLE = {".png"}                    # iTXt legible por la API estándar
BINARY_WRITEONLY = {".ico", ".webp", ".jpg", ".jpeg"}   # viaja dentro, no se lee de vuelta


# --------------------------------------------------------------- serialización
def _emit_yaml(meta: dict) -> str:
    """YAML mínimo y predecible: preserva el orden, no reformatea fechas.

    No se usa yaml.safe_dump a propósito: convierte las fechas ISO en objetos
    datetime y las reescribe, con lo que el fichero cambia sin que cambie el dato.
    """
    out = []
    for key, value in meta.items():
        if isinstance(value, (list, tuple)):
            out.append(f"{key}:")
            for item in value:
                out.append(f'  - "{item}"')
        elif isinstance(value, bool):
            out.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, (int, float)):
            out.append(f"{key}: {value}")
        else:
            text = str(value).replace('"', "'")
            out.append(f'{key}: "{text}"')
    return "\n".join(out)


def _parse_yaml(text: str) -> dict:
    """Parsea el subconjunto que emitimos, sin depender de PyYAML."""
    meta: dict = {}
    current_key = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+-\s", line) and current_key:
            item = re.sub(r"^\s+-\s+", "", line).strip().strip('"').strip("'")
            meta.setdefault(current_key, [])
            if not isinstance(meta[current_key], list):
                meta[current_key] = [meta[current_key]]
            meta[current_key].append(item)
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        current_key, rest = m.group(1), m.group(2).strip()
        if rest == "":
            meta[current_key] = []
        elif rest.lower() in ("true", "false"):
            meta[current_key] = rest.lower() == "true"
        elif re.fullmatch(r"-?\d+", rest):
            meta[current_key] = int(rest)
        elif re.fullmatch(r"-?\d+\.\d+", rest):
            meta[current_key] = float(rest)
        else:
            meta[current_key] = rest.strip('"').strip("'")
    return meta


# ------------------------------------------------------------------- decodificar
def _find_text_block(text: str):
    """Devuelve (inicio, fin, cuerpo) del bloque OKF dentro de un texto, o None."""
    stripped = text.lstrip()
    offset = len(text) - len(stripped)
    # SVG: <metadata id="okf">…</metadata> — HTML-escaped, cannot break XML
    m_meta = re.search(r'<metadata id="okf">\s*(.*?)\s*</metadata>', text, re.S)
    if m_meta:
        import html as _html
        # full element span, so a rewrite REPLACES it instead of nesting inside it
        return m_meta.start(0), m_meta.end(0), _html.unescape(m_meta.group(1))
    if stripped.startswith("<!-- OKF-METADATA"):
        end = stripped.find("-->")
        if end == -1:
            return None
        inner = stripped[len("<!-- OKF-METADATA"):end]
        fenced = re.search(r"---\n(.*?)\n---", inner, re.S)
        body = fenced.group(1) if fenced else inner.strip()
        return offset, offset + end + 3, body
    if stripped.startswith("---"):
        m = re.match(r"---\n(.*?)\n---\n", stripped, re.S)
        if m:
            return offset, offset + m.end(), m.group(1)
    # Python: comentario contiguo marcado con OKF-METADATA
    if stripped.startswith("#"):
        lines = stripped.splitlines(keepends=True)
        start = None
        collected = []
        for i, line in enumerate(lines):
            if start is None:
                if "OKF-METADATA" in line:
                    start = i
                elif line.startswith("#") and i < 12:
                    continue
                else:
                    break
                continue
            if line.startswith("#"):
                collected.append(re.sub(r"^#\s?", "", line.rstrip("\n")))
            else:
                break
        if start is not None:
            begin = sum(len(line) for line in lines[:start]) + offset
            end = begin + sum(len(line) for line in lines[start:start + len(collected) + 1])
            body = "\n".join(collected)
            if body.lstrip().startswith("---"):
                body = re.sub(r"^---\n(.*?)\n---", r"\1", body, flags=re.S)
            return begin, end, body
    return None


def read_okf(path: Path) -> dict | None:
    """Read the OKF header of any supported format. None if there is none.

    For a format whose standard API cannot return the embedded payload (ICO),
    this returns the MANIFEST ENTRY instead of None. Reporting "no header" for a
    file that does carry one is a false negative, and a false negative is how
    people lose trust in a tool and stop using it.
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        sibling = path.with_suffix(".meta.json")
        if not sibling.is_file():
            return None
        return json.loads(sibling.read_text())
    if suffix in BINARY_READABLE:
        try:
            from PIL import Image
        except ImportError:
            return None
        payload = (Image.open(path).info or {}).get("OKF-METADATA")
        return _parse_yaml(payload) if payload else None
    if suffix in BINARY_WRITEONLY:
        # WebP/JPEG are stamped by sidecar, so the sibling is the reader.
        sidecar = path.with_suffix(f"{suffix}.meta.json")
        if sidecar.is_file():
            import json as _json
            return _json.loads(sidecar.read_text())
        # Está dentro del fichero, pero la API estándar no lo devuelve: se lee del
        # manifiesto. Decirlo es mejor que devolver None y fingir que no existe.
        local_manifest = manifest_for(path)
        # rows are bare filenames (`icon.ico`), relative to the manifest's dir
        needle = f"`{path.name}`"
        for candidate in (local_manifest, MANIFEST):
            if not candidate.is_file():
                continue
            text = candidate.read_text()
            if needle in text:
                row = next((ln for ln in text.splitlines() if needle in ln), "")
                return {
                    "_note": "este formato no admite lectura estándar del payload",
                    "_manifest": str(candidate),
                    "_row": row.strip(),
                }
        return None
    found = _find_text_block(path.read_text(errors="replace"))
    return _parse_yaml(found[2]) if found else None


# --------------------------------------------------------------------- codificar
def _block_for(kind: str, meta: dict) -> str:
    yaml_text = _emit_yaml(meta)
    if kind == "md":
        return f"---\n{yaml_text}\n---\n"
    if kind == "html":
        return f"<!-- OKF-METADATA\n---\n{yaml_text}\n---\n-->\n"
    if kind == "svg":
        # SVG is XML and XML forbids "--" inside a comment, so a title containing
        # "a--b" would break the file. Escaping is not enough: the real fix is
        # <metadata>, the element SVG defines for exactly this. It also survives
        # XML tooling, which a comment does not.
        import html as _html
        return (f'<metadata id="okf">\n{_html.escape(yaml_text)}\n</metadata>\n')
    if kind == "py":
        body = "\n".join(f"# {line}" if line else "#" for line in yaml_text.splitlines())
        return f"# OKF-METADATA\n# ---\n{body}\n# ---\n"
    raise ValueError(f"sin codificador para {kind}")


def write_okf(path: Path, meta: dict, *, dry_run: bool = False) -> str:
    """Escribe (o reemplaza) la cabecera OKF. Devuelve una línea de resultado."""
    _assert_no_secrets(dict(meta))
    meta = dict(meta)
    now = datetime.now().astimezone().replace(microsecond=0)
    meta.setdefault("generated", now.isoformat())
    meta.setdefault("verified", now.date().isoformat())

    suffix = path.suffix.lower()
    if suffix == ".json":
        sibling = path.with_suffix(".meta.json")
        if not dry_run:
            sibling.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        return f"json → {sibling.name} (fichero hermano)"
    if suffix in BINARY_READABLE or suffix in BINARY_WRITEONLY:
        return stamp_binary(path, meta, dry_run=dry_run)

    kind = TEXT_KINDS.get(suffix)
    if not kind:
        raise SystemExit(f"formato no soportado: {suffix!r} — ver `okf.py formats`")

    original = path.read_text()
    block = _block_for(kind, meta)
    found = _find_text_block(original)
    if found:
        start, end, _ = found
        updated = original[:start] + block + original[end:]
        action = "reemplazada"
    else:
        if kind == "py":
            lines = original.splitlines(keepends=True)
            insert = 1 if lines and lines[0].startswith("#!") else 0
            updated = "".join(lines[:insert]) + block + "".join(lines[insert:])
        elif kind == "svg":
            m = re.match(r"(<\?xml[^>]*\?>\s*)", original)
            insert = len(m.group(1)) if m else 0
            # inside <svg> ... </svg>: <metadata> is only valid as a child of <svg>
            m_svg = re.search(r"<svg\b[^>]*>", original)
            if m_svg:
                insert = m_svg.end()
            updated = original[:insert] + "\n" + block + original[insert:]
        else:
            updated = block + original
        action = "añadida"
    if not dry_run:
        path.write_text(updated)
    return f"{kind} → cabecera {action}"


def stamp_binary(path: Path, meta: dict, *, dry_run: bool = False,
                 update_manifest: bool = True) -> str:
    """Embebe el OKF en un binario (capa 1) y actualiza el manifiesto (capa 2)."""
    _assert_no_secrets(dict(meta))
    payload = _emit_yaml(meta)
    suffix = path.suffix.lower()
    try:
        from PIL import Image, PngImagePlugin
    except ImportError:
        raise SystemExit("se necesita Pillow para los binarios: pip install pillow")

    if dry_run:
        return f"{suffix} → (simulación) se estamparía iTXt + manifiesto"

    if suffix == ".png":
        image = Image.open(path)
        info = PngImagePlugin.PngInfo()
        info.add_itxt("OKF-METADATA", payload)
        image.save(path, pnginfo=info)
        back = Image.open(path).info.get("OKF-METADATA")
        if not back:
            raise SystemExit(f"{path.name}: el chunk no se pudo releer — no se declara éxito")
        result = "png → iTXt embebido y verificado leyéndolo de vuelta"
    elif suffix == ".ico":
        image = Image.open(path).convert("RGBA")
        info = PngImagePlugin.PngInfo()
        info.add_itxt("OKF-METADATA", payload)
        image.save(path, sizes=[(64, 64), (48, 48), (32, 32), (16, 16)], pnginfo=info)
        result = "ico → iTXt en los frames (la API estándar no lo relee: manda el manifiesto)"
    else:
        # WebP/JPEG carry EXIF/XMP, but Pillow's write path for a custom chunk is
        # not something to guess at. Rather than refuse with a dead end, fall back
        # to the sidecar — the same mechanism already defined for .json — so the
        # caller gets working metadata instead of an error and an undocumented task.
        sidecar = path.with_suffix(f"{suffix}.meta.json")
        if not dry_run:
            import json as _json
            sidecar.write_text(_json.dumps({k: (v if not isinstance(v, tuple) else list(v))
                                            for k, v in meta.items()},
                                           indent=2, ensure_ascii=False) + "\n")
        return (f"{suffix} → hermano {sidecar.name} "
                f"(iTXt no implementado para este formato; el sidecar es la capa 1)")

    if update_manifest:
        regenerate_manifest(path)
        return result + " + manifiesto actualizado"
    # Generated output trees have no manifest: an index hashing files that this
    # same run rewrites is stale on arrival.
    return result


def regenerate_manifest(target: Path | None = None) -> int:
    """Rewrite the OKF-MANIFEST.md that belongs to `target`'s tree.

    `target` is the file being stamped (or an assets dir); with no argument it
    defaults to this project's assets/. The manifest is always written NEXT TO
    the assets it indexes, never into the tool's own directory.
    """
    import hashlib
    assets_dir = assets_dir_for(target)
    manifest = manifest_for(target)
    if not assets_dir.is_dir():
        return 0
    now = datetime.now().astimezone().replace(microsecond=0).isoformat()
    rows = []
    for f in sorted(assets_dir.iterdir()):
        if f.is_dir() or f.name == manifest.name:
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        kind = {".png": "PNG raster", ".ico": "ICO (frames PNG)", ".svg": "SVG (XML)"}.get(
            f.suffix.lower(), f.suffix.lstrip(".").upper())
        if f.suffix.lower() == ".png":
            embedded = "sí (iTXt)"
        elif f.suffix.lower() == ".svg":
            embedded = "sí (<metadata>)"
        else:
            embedded = "sí en frames; la lectura estándar no lo expone"
        rows.append((f.name, kind, f.stat().st_size, digest, embedded))

    header = (
        f"---\ntype: Asset Manifest\ntitle: \"Manifiesto OKF de binarios\"\n"
        f"description: \"Capa 2: índice de assets con su hash. Capa 1 es el OKF embebido en el propio fichero.\"\n"
        f"status: verified\ngenerated: {now}\nsource:\n  - \"assets/* generado por accounting/okf.py manifest\"\n"
        f"verified: {now[:10]}\nstale_after: 2027-06-30\n---\n\n"
    )
    body = (
        "# Manifiesto OKF de assets\n\n"
        "Los binarios no admiten todos la misma cabecera. Solución por capas:\n\n"
        "1. **Embebido** — el propio fichero lleva su OKF (PNG: chunk `iTXt`; SVG: comentario XML).\n"
        "2. **Manifiesto** — esta tabla, para lo que no se puede leer de vuelta (ICO).\n"
        "3. **Guard** — `check_okf.py` exige que cada binario esté aquí, que su hash coincida\n"
        "   y que el `iTXt` del PNG sea legible.\n\n"
        "Regla: si un asset cambia, su hash cambia aquí en el mismo commit. Se regenera con\n"
        "`okf.py manifest --target <carpeta de assets>`.\n\n"
        "| Fichero | Tipo | Bytes | SHA-256 (16) | OKF embebido |\n|---|---|---|---|---|\n"
    )
    # Label rows with the REAL directory name: a manifest living in img/ must not
    # claim its files are under assets/. Paths are shown relative to the manifest.
    # Paths are relative to the manifest's own directory, so rows stay stable no
    # matter where the tree is checked out. A bare `assets/`-only prefix was wrong
    # when the manifest lived elsewhere.
    body += "".join(f"| `{n}` | {k} | {s} | `{h}` | {e} |\n" for n, k, s, h, e in rows)
    manifest.write_text(header + body)
    return len(rows)



# ------------------------------------------------------------------- secret guard
# A credential must never reach a file because a tool wrote it there. okf.py takes
# free-form --set values, so it is exactly the kind of utility that can stamp a
# password into a document and hand it to git with everything looking correct.
#
# Rule (Ricardo, 21-nov): credentials are stored in an env file outside version
# control or the secret store, and referenced by LOCATION, never by value.
SECRET_KEY_RE = re.compile(
    r"(?i)^(api[_-]?key|apikey|token|secret|password|passwd|contrase[ñn]a|"
    r"private[_-]?key|access[_-]?key|client[_-]?secret|bearer)$")

# High-entropy strings that look like a generated credential rather than prose.
SECRET_VALUE_RE = re.compile(r"^[A-Za-z0-9_\-+/]{24,}={0,2}$")

def _assert_no_secrets(meta: dict) -> None:
    """Refuse a header carrying a credential. Called by EVERY writer.

    Originally this lived only in main(), which meant the CLI refused and the
    LIBRARY did not: `stamp_binary(p, {"api_key": "sk-..."})` wrote the secret
    happily. A guard at the entry point is a door, not a lock — anything that
    calls the function directly walks past it. build_static_site.py does exactly
    that, so the hole was live in our own tree.

    Raises ValueError (not SystemExit) so a library caller can handle it, and the
    CLI converts it to exit 2.
    """
    violations = [r for k, v in meta.items()
                  for val in (v if isinstance(v, list) else [v])
                  if (r := _looks_like_secret(k, val))]
    if violations:
        raise ValueError("; ".join(violations))


# A hash is not a credential: it is a verification artefact and belongs in the
# header. Recognising the FIELD keeps the value-shape check strict everywhere else,
# whereas lowering the threshold or excluding hex strings would have opened a gap
# that a real key could walk through.
DIGEST_KEY_RE = re.compile(r"(?i)^(md5|sha1|sha256|sha512|hash|digest|checksum|"
                           r"original_md5|source_md5|etag)$")


def _looks_like_secret(key: str, value: str) -> str | None:
    """Return a reason if this key/value pair must not be written, else None."""
    key_name = key.strip()
    text = str(value).strip()
    if DIGEST_KEY_RE.match(key_name):
        return None      # a documented digest field, not a secret
    if SECRET_KEY_RE.match(key_name) and not text.startswith(("env:", "file:", "vault:", "/")):
        return (f"el campo {key_name!r} parece una credencial; guarda el valor fuera del "
                f"fichero y referencia su ubicación (env:VAR, file:RUTA)")
    if SECRET_VALUE_RE.match(text) and not text.startswith(("http", "assets/", "accounting/", "/")):
        # long, unbroken, alphanumeric: a generated token, not a path or a title
        if any(c.isdigit() for c in text) and any(c.isalpha() for c in text):
            return ("el valor parece una credencial generada (cadena larga alfanumérica); "
                    "guárdala fuera del fichero y referencia su ubicación")
    return None


# -------------------------------------------------------------------------- CLI
FORMATS = [
    ("md", "frontmatter YAML entre ---", "sí"),
    ("html", "<!-- OKF-METADATA --> antes de <!DOCTYPE>", "sí"),
    ("svg", '<metadata id="okf"> dentro de <svg>', "sí"),
    ("py", "bloque # OKF-METADATA tras el shebang", "sí"),
    ("json", "fichero hermano .meta.json", "sí"),
    ("png", "chunk iTXt OKF-METADATA", "sí"),
    ("ico", "iTXt en los frames", "no: manda el manifiesto"),
    ("webp", "hermano X.meta.json (escritor no implementa iTXt)", "sí, por el hermano"),
    ("jpg", "hermano X.meta.json (escritor no implementa iTXt)", "sí, por el hermano"),
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="okf.py", description="Leer y escribir la cabecera OKF de cualquier fichero.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="imprime la cabecera OKF de un fichero")
    p_read.add_argument("file")
    p_read.add_argument("--raw", action="store_true", help="texto tal cual, sin parsear")

    p_write = sub.add_parser("write", help="escribe o reemplaza la cabecera OKF")
    p_write.add_argument("file")
    p_write.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR")
    p_write.add_argument("--from", dest="from_file", help="YAML con la cabecera completa")
    p_write.add_argument("--dry-run", action="store_true")

    p_stamp = sub.add_parser("stamp", help="embebe OKF en un binario y actualiza el manifiesto")
    p_stamp.add_argument("file")
    p_stamp.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR")
    p_stamp.add_argument("--from", dest="from_file", help="YAML con la cabecera completa")
    p_stamp.add_argument("--dry-run", action="store_true")

    sub.add_parser("check", help="ejecuta el guard completo (equivale a check_okf.py)")
    p_man = sub.add_parser("manifest", help="regenera el OKF-MANIFEST.md del árbol indicado")
    p_man.add_argument("--target", help="carpeta de assets cuyo manifiesto se regenera "
                                        "(por defecto, los assets de este proyecto)")
    sub.add_parser("formats", help="muestra qué formato usa cada extensión")

    args = parser.parse_args(argv)

    if args.cmd == "formats":
        print(f"{'EXT':<6} {'DÓNDE SE GUARDA':<45} {'LECTURA'}")
        for ext, where, readable in FORMATS:
            print(f"{ext:<6} {where:<45} {readable}")
        return 0

    if args.cmd == "check":
        import check_okf
        return check_okf.main()

    if args.cmd == "manifest":
        target = Path(args.target).resolve() if getattr(args, "target", None) else None
        count = regenerate_manifest(target)
        print(f"manifiesto regenerado · {count} assets")
        return 0

    path = Path(args.file).resolve()
    if not path.is_file():
        raise SystemExit(f"no existe: {path}")

    if args.cmd == "read":
        if args.raw:
            suffix = path.suffix.lower()
            if suffix in BINARY_READABLE:
                from PIL import Image
                print((Image.open(path).info or {}).get("OKF-METADATA") or "(sin cabecera)")
            else:
                found = _find_text_block(path.read_text(errors="replace"))
                print(found[2] if found else "(sin cabecera)")
            return 0
        meta = read_okf(path)
        if meta is None:
            print(f"(sin cabecera OKF) {path.name}", file=sys.stderr)
            return 1
        for key, value in meta.items():
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")
        return 0

    # write / stamp: construir la cabecera
    meta: dict = {}
    if getattr(args, "from_file", None):
        meta = _parse_yaml(Path(args.from_file).read_text())
    else:
        existing = read_okf(path)
        if existing and not any(k.startswith("_") for k in existing):
            meta = {k: v for k, v in existing.items() if not k.startswith("_")}
    for pair in args.set:
        if "=" not in pair:
            raise SystemExit(f"--set necesita CLAVE=VALOR, recibido {pair!r}")
        key, value = pair.split("=", 1)
        key, value = key.strip(), value.strip()
        # Repeating a key must ACCUMULATE, never silently overwrite. This is the
        # exact defect that lost two of three NLnet sources: duplicate `source:`
        # keys in YAML keep only the last one. `--set source=A --set source=B`
        # now yields one key with two entries instead of one survivor.
        if key in meta:
            existing = meta[key]
            if not isinstance(existing, list):
                existing = [existing]
            if value not in existing:
                existing.append(value)
            meta[key] = existing
        else:
            meta[key] = value
    if not meta:
        raise SystemExit("cabecera vacía: usa --set clave=valor o --from fichero.yaml")

    # The writers assert this too; the CLI only translates it to a stable exit code
    # so a caller can tell "refused" (2) from an I/O failure (1).
    try:
        _assert_no_secrets(meta)
    except ValueError as exc:
        print(f"RECHAZADO: {exc}", file=sys.stderr)
        raise SystemExit(2)

    if args.cmd == "stamp":
        print(stamp_binary(path, meta, dry_run=args.dry_run))
    else:
        print(write_okf(path, meta, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
