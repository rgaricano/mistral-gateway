---
type: Method Guide
title: "Método y comandos para leer y escribir OKF en cualquier fichero"
description: "Procedimiento operativo para codificar y descodificar la cabecera OKF en markdown, HTML, SVG, Python, JSON, PNG, ICO y gráficos Plotly usando un solo comando (okf.py), con el guard que lo verifica."
tags: [okf, método, procedimiento, okf.py, runbook]
status: verified
generated: 2026-11-20T03:00:00+01:00
source:
  - "accounting/okf.py (herramienta)"
  - "accounting/check_okf.py (validador y guard)"
  - "accounting/test_okf_tool.py (pruebas de ida y vuelta)"
  - "accounting/decision_okf_binarios.md (decisión de las tres capas)"
verified: 2026-11-20
stale_after: 2027-06-30
---

# Método para leer y escribir OKF: un solo comando

## El problema

Cada formato guarda su cabecera de una forma distinta. Seis variantes, seis
oportunidades de equivocarse:

| Extensión | Dónde va la cabecera | ¿La API estándar la lee? |
|---|---|---|
| `.md` | frontmatter YAML entre `---` | sí |
| `.html` | `<!-- OKF-METADATA -->` antes de `<!DOCTYPE>` | sí |
| `.svg` | `<metadata id="okf">` dentro de `<svg>` | sí |
| `.py` | bloque `# OKF-METADATA` tras el shebang | sí |
| `.json` | fichero hermano `X.meta.json` | sí |
| `.png` | chunk `iTXt` con clave `OKF-METADATA` | sí |
| `.ico` | `iTXt` en los frames | **no** → manda el manifiesto |

Recordar seis variantes es garantizar que alguien se equivoque. Por eso hay un
único comando: **`accounting/okf.py`**.

## Uso diario

```bash
# Leer la cabecera de cualquier fichero (el formato lo detecta solo)
python3 accounting/okf.py read accounting/data.py
python3 accounting/okf.py read accounting/assets/favicon_64.png
python3 accounting/okf.py read accounting/assets/favicon.ico

# Escribir o reemplazar la cabecera (rellena generated/verified con la fecha de hoy)
python3 accounting/okf.py write nuevo.html \
    --set type="Report" \
    --set title="Informe de costes" \
    --set status=verified \
    --set source="usage.db"

# Desde un YAML completo, cuando hay muchos campos
python3 accounting/okf.py write informe.md --from cabecera.yaml

# Ver qué está mal antes de tocar nada
python3 accounting/okf.py write informe.md --set title="x" --dry-run

# Binarios: embebe y actualiza el manifiesto en un solo paso
python3 accounting/okf.py stamp assets/favicon_64.png --set type="Icon Asset" --set title="Favicon"

# Verificación completa (equivale a check_okf.py)
python3 accounting/okf.py check

# Regenerar el manifiesto de assets
python3 accounting/okf.py manifest

# Recordar qué formato usa cada extensión
python3 accounting/okf.py formats
```


## Trabajar en un árbol ajeno (autocontención)

`okf.py` no asume este proyecto: se le da la ruta y deduce el resto.

- **La cabecera va al fichero que le pasas.** Sin rutas fijas.
- **El manifiesto nace junto a los assets de ESE fichero**, no junto a la herramienta.
  Regla: si el fichero está en una carpeta, el manifiesto se escribe en esa carpeta.
  (Antes escribía siempre en `accounting/assets/`: estampar un icono ajeno metía su
  hash en nuestro índice. Corregido y con tres pruebas que lo impiden.)
- **Las filas del manifiesto son nombres de fichero**, relativos al propio manifiesto,
  para que el árbol funcione esté donde esté.

```bash
# estampar un PNG de otro proyecto: el manifiesto nace a su lado
python3 okf.py stamp /ruta/ajena/img/icono.png --set type=Icon --set title="Icono"

# regenerar el manifiesto de esa carpeta sin tocar el nuestro
python3 okf.py manifest --target /ruta/ajena/img

# leer: mismo comando, detecta el formato
python3 okf.py read /ruta/ajena/img/icono.png
```

Un ICO no se puede leer con la API estándar: `read` devuelve entonces la **fila del
manifiesto** (`_note`, `_manifest`, `_row`) en vez de decir «sin cabecera». Decir que
no hay cabecera cuando sí la hay es un falso negativo, y un falso negativo es como se
pierde la confianza en una herramienta.


## Publicar el árbol estático (un comando)

El árbol de `gentle-companion/docs/accounting/` es **salida generada**, no fuente.
Se regenera entero con:

```bash
python3 accounting/build_static_site.py
```

Genera `index.html` (sin JS, sin CDN), los tres gráficos PNG con su OKF embebido,
las 26 fichas con enlaces relativos, la ficha ampliada del crédito fiscal, la
página de navegación y el favicon. Todas las cifras salen de la lectura viva; si
no hay lectura viva se niega a publicar una cifra inventada.

**Y se comprueba solo.** `test_units.py` incluye una prueba que exige que el sitio
publicado esté fresco, sin `<script>`, sin dependencias de CDN, con OKF en cada
gráfico y **sin un solo enlace roto**. Si está desfasado, lo regenera y lo dice
por stderr.

Antes esto se hacía a mano y por eso el sitio llegó a publicar 20,40 % cuando la
cifra real era 23,36 %: nadie se dio cuenta porque nada lo comprobaba.

## Las tres capas (para binarios)

Los binarios no admiten todos la misma cabecera, así que la solución tiene capas
—y las tres son necesarias para esto:

1. **Embebido nativo.** El propio fichero lleva su OKF. En PNG es un chunk
   `iTXt`, que Pillow escribe y **lee de vuelta**; verificado. En SVG es el
   elemento `<metadata id="okf">`.
2. **Manifiesto.** `assets/OKF-MANIFEST.md` indexa lo que no se puede leer de
   vuelta (ICO), con tipo, bytes, **hash SHA-256** y si lleva OKF dentro.
3. **Guard.** `check_okf.py` exige que cada binario esté en el manifiesto, que su
   **hash coincida** y que el `iTXt` del PNG sea **legible**. El hash es lo que
   caza el fallo silencioso más probable: que alguien regenere el icono y la
   cabecera se quede vieja.

## Reglas que el comando ya respeta por ti

- **Reemplaza, no duplica.** Reescribir una cabecera deja una sola, nunca dos. Es
  el fallo más común al hacerlo a mano y el guard no siempre lo ve.
- **SVG sin `--`.** XML prohíbe `--` dentro de un comentario, así que un título
  como `a--b` rompía el fichero. Por eso el SVG usa `<metadata>` y el texto va
  escapado: el título con guiones se lee intacto.
- **Shebang primero.** En un `.py`, el bloque va **después** del `#!`, nunca antes
  de él.
- **Fechas sin reformatear.** El emisor YAML es propio a propósito: `yaml.safe_dump`
  convierte las fechas ISO en objetos `datetime` y las reescribe, con lo que el
  fichero cambia sin que cambie el dato.
- **JSON intacto.** En un `.json` la cabecera va al hermano; el cuerpo no se toca.
- **Claves repetidas se acumulan, no se pisan.** `--set source=A --set source=B`
  produce **una** clave con dos entradas. Es el fallo que ya nos costó dos fuentes
  de tres: en YAML, dos claves `source:` dejan solo la última y las demás
  desaparecen sin ningún error.
- **Simulación disponible.** `--dry-run` dice qué haría sin escribir nada.

## El guard, y por qué comprueba el significado

Un guard que solo comprueba **presencia** no sirve: un `title:` vacío pasa.
`check_okf.py` verifica claves duplicadas (YAML se queda solo con la última y
pierde las demás en silencio), campos obligatorios, forma ISO de las fechas, que
el SVG sea **XML bien formado**, y en binarios el hash.

Los dos errores que este proyecto ya cometió, y que ahora están cubiertos:

- **Claves `source:` duplicadas** → YAML conservó una sola y se perdieron dos de
  tres fuentes. Correcto: **una** clave `source:` con una lista de URLs.
- **`--` dentro de un comentario XML** → el SVG dejó de parsear. Correcto:
  elemento `<metadata>`.

```bash
# la comprobación completa, tal como se ejecuta en cada cierre
python3 accounting/check_okf.py && \
python3 accounting/check_number_format.py && \
python3 accounting/test_units.py && \
python3 accounting/test_fichas.py && \
python3 accounting/test_auth_hosts.py && \
python3 accounting/test_okf_tool.py
```

## Pruebas que sostienen el método

`test_okf_tool.py` no comprueba que el comando "funcione"; comprueba que **lo que
escribe el comando lo acepta el validador**, y que un fichero sin cabecera se
rechaza. Ocho pruebas:

| Prueba | Qué impide |
|---|---|
| `test_write_then_validate_roundtrip` | que la herramienta y el guard se desincronicen |
| `test_read_returns_what_was_written` | que se pierdan campos o acentos al releer |
| `test_rewrite_replaces_and_never_duplicates` | que una segunda escritura duplique la cabecera |
| `test_repeated_set_accumulates_sources` | que `--set source=A --set source=B` pierda la primera |
| `test_svg_stays_wellformed_xml` | que un título con `--` rompa el SVG |
| `test_python_shebang_survives` | que el bloque se cuele antes del `#!` |
| `test_missing_header_is_detected` | que la ausencia de cabecera pase por éxito |
| `test_cli_write_and_read_agree` | que el CLI y la librería se comporten distinto |

Las ocho se escribieron **después** de encontrar los fallos que cubren, o al
buscarlos a propósito. La primera versión de `okf.py` tenía un parser que
devolvía `None` para todos los ficheros y decía «sin cabecera» de cabeceras que
estaban a la vista; y la primera versión de `--set` repetido borraba las fuentes
anteriores en silencio. Una prueba de humo habría pasado las dos.

## Lo que NO hace

- No inventa el contenido: `type`, `title`, `status` y `source` los pone quien
  escribe. El comando solo rellena las fechas.
- No decide si un dato es cierto. El guard es el **suelo**, no la prueba: una
  persona verifica las cifras antes de usarlas para decidir.
- No toca ficheros fuera del proyecto, y las exclusiones de secretos
  (`dashboard.token`, `auth_fails.log`) siguen en `.gitignore`.

## Añadir un formato nuevo

1. Decidir **dónde** va la cabecera según el formato (¿admite texto propio?).
2. Añadir la extensión a `TEXT_KINDS` o a los conjuntos de binarios en `okf.py`.
3. Implementar el bloque en `_block_for()` y el reconocimiento en
   `_find_text_block()`.
4. Añadir una prueba de ida y vuelta en `test_okf_tool.py`.
5. Actualizar `formats` y esta tabla.

Si el formato **no** permite leer el texto de vuelta, no se finge que sí: va al
manifiesto y se documenta la limitación. Ese fue el caso del ICO.
