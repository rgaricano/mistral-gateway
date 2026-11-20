#!/usr/bin/env python3
# OKF-METADATA
# type: Tool
# title: "import_mistral_export.py — importa la exportación CSV del panel"
# description: "Lee la exportación de uso del panel de Mistral (CSV con time_bucket y dimensiones) y la normaliza a una tabla propia con granularidad real. Complementa a usage.db, que solo tiene día/modelo/cuenta."
# status: verified
# generated: 2026-11-21T00:05:00+01:00
# source:
#   - "Exportación del panel admin.mistral.ai (descarga manual de Ricardo, 16-nov-2026)"
#   - "accounting/data.py (usage.db y presupuesto)"
# verified: 2026-11-20
# stale_after: 2027-06-30
"""Importa la exportación de uso del panel de Mistral.

Por qué existe: `usage.db` guarda solo día/modelo/cuenta, sin hora y sin
recuento de llamadas. La exportación del panel trae más: `time_bucket` (con la
granularidad que se elija en el panel), `nb_api_calls`, `call_type`,
`service_tier`, `api_zone` y el id de la API key.

Lo que NO hace y no puede hacer: descargar la exportación por sí mismo. La ruta
de exportación de `admin.mistral.ai` responde con una pantalla de login de Ory
Kratos aunque se envíe la API key — comprobado, y es un 200 con cuerpo de login,
no datos. Automatizarlo exigiría reutilizar la sesión del navegador de Ricardo,
que es frágil y convierte su login en dependencia del sistema contable. Se
descarga a mano y se importa aquí.

    python3 accounting/import_mistral_export.py RUTA.csv
    python3 accounting/import_mistral_export.py RUTA.csv --db otra.db

La tabla es aditiva: no toca `usage`, que sigue siendo la fuente del día a día.
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE.parent / "usage.db"

# Columnas del export que nos interesan, con el nombre que usamos nosotros.
# NOTE: the export names the model column `billing_display_name`, not `model`.
# Mapping the wrong key left every model empty and collapsed 10 models into 1 —
# caught by comparing the import against the file's real header instead of my
# assumption about it.
COLUMN_MAP = {
    "time_bucket": "time_bucket",
    "billing_display_name": "model",
    "value": "value",
    "count": "count",
    "nb_api_calls": "api_calls",
    "call_type": "call_type",
    "service_tier": "service_tier",
    "api_zone": "api_zone",
    "usage_type": "usage_type",
    "api_key_id": "api_key_id",
    "workspace_id": "workspace_id",
    "user_id": "user_id",
    "service_account_id": "service_account_id",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS panel_usage (
    time_bucket   TEXT NOT NULL,
    model         TEXT NOT NULL,
    usage_type    TEXT,
    call_type     TEXT,
    service_tier  TEXT,
    api_zone      TEXT,
    api_key_id    TEXT,
    workspace_id  TEXT,
    user_id       TEXT,
    service_account_id TEXT,
    value         INTEGER DEFAULT 0,
    count         INTEGER DEFAULT 0,
    api_calls     INTEGER DEFAULT 0,
    source_file   TEXT,
    imported_at   TEXT,
    PRIMARY KEY (time_bucket, model, usage_type, call_type, api_key_id)
)
"""


def _int(value: str) -> int:
    """The export writes plain integers; an empty cell means zero, not an error."""
    text = (value or "").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def import_csv(csv_path: Path, db_path: Path) -> dict:
    if not csv_path.is_file():
        raise SystemExit(f"no existe: {csv_path}")

    from datetime import datetime
    now = datetime.now().astimezone().replace(microsecond=0).isoformat()

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"{csv_path.name}: sin cabecera, no parece un export del panel")
        missing = [c for c in ("time_bucket", "value") if c not in reader.fieldnames]
        if missing:
            raise SystemExit(
                f"{csv_path.name}: faltan columnas {missing}. "
                f"Cabecera vista: {reader.fieldnames[:6]}")

        rows = []
        # keys() are the CSV column names; values() are our destination columns.
        # Iterating values() here read the CSV looking for our own names, found
        # nothing, and wrote empty strings for every field.
        source_columns = list(COLUMN_MAP.keys())
        for record in reader:
            rows.append(tuple((record.get(col) or "").strip() for col in source_columns))

    if not rows:
        raise SystemExit(f"{csv_path.name}: cero filas de datos")

    with sqlite3.connect(db_path) as cx:
        cx.execute(SCHEMA)
        # upsert: reimportar el mismo fichero no duplica, y un export más reciente
        # del mismo bucket actualiza la cifra en lugar de sumar dos verdades.
        placeholders = ",".join("?" * (len(COLUMN_MAP) + 2))
        cx.executemany(
            f"INSERT INTO panel_usage ({','.join(COLUMN_MAP.values())}, source_file, imported_at) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(time_bucket, model, usage_type, call_type, api_key_id) DO UPDATE SET "
            f"value=excluded.value, count=excluded.count, api_calls=excluded.api_calls, "
            f"imported_at=excluded.imported_at, source_file=excluded.source_file",
            [r + (csv_path.name, now) for r in rows],
        )
        cx.commit()
        cols = list(COLUMN_MAP.values())
        i_model, i_value, i_calls = cols.index("model"), cols.index("value"), cols.index("api_calls")
        buckets = [r[0] for r in rows]
        total_value = sum(_int(r[i_value]) for r in rows)
        total_calls = sum(_int(r[i_calls]) for r in rows)
        models = len({r[i_model] for r in rows if r[i_model]})

    return {
        "rows": len(rows),
        "buckets": len(set(buckets)),
        "first": min(buckets),
        "last": max(buckets),
        "models": models,
        "value": total_value,
        "api_calls": total_calls,
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip().split("\n\n")[0])
        print("\nuso: import_mistral_export.py RUTA.csv [--db RUTA.db]")
        return 2
    csv_path = Path(argv[0]).expanduser()
    db_path = Path(argv[argv.index("--db") + 1]) if "--db" in argv else DEFAULT_DB

    stats = import_csv(csv_path, db_path)
    print(f"importado {csv_path.name} → {db_path}")
    print(f"  filas: {stats['rows']} · modelos: {stats['models']} "
          f"· buckets: {stats['buckets']}")
    print(f"  rango: {stats['first']} → {stats['last']}")
    print(f"  total value: {stats['value']:,} · llamadas API: {stats['api_calls']:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
