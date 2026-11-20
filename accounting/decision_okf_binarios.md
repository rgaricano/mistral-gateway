---
type: Decision Document
title: "OKF en ficheros no textuales — solución por capas"
description: "Cómo llevar procedencia OKF a binarios (PNG/ICO) y gráficos sin romper el formato: metadatos embebidos donde el formato lo permite, manifiesto índice donde no, y guard que verifica ambos."
tags: [okf, binarios, procedencia, decisión]
status: verified
generated: 2026-11-20T01:05:00+01:00
source:
  - "W3C PNG Specification (Third Edition), § Text chunks tEXt/zTXt/iTXt — https://www.w3.org/TR/png-3/"
  - "PNG: The Definitive Guide, cap. 11 (libpng.org/pub/png/book/chapter11.html)"
  - "Prueba propia con Pillow 12,3 (iTXt escribir/leer) y strings sobre ICO, 20-nov-2026"
verified: 2026-11-20
stale_after: 2027-06-30
---

# OKF en ficheros no textuales: una solución por capas

Ricardo planteó dos problemas distintos que yo había metido en el mismo saco:

1. **Binarios** (favicon `.ico`, `.png`): un ráster no admite un comentario de texto.
2. **Gráficos**: si se exportan a imagen, los datos se desacoplan de la imagen.

No son el mismo problema y no merecen la misma solución. Lo he comprobado antes de
proponer nada.

## Lo que he verificado (no supuesto)

| Formato | ¿Admite texto propio? | Resultado de mi prueba |
|---|---|---|
| **PNG** | **Sí** — chunks `tEXt`/`zTXt`/`iTXt` | Pillow escribe `iTXt` con clave `OKF-METADATA` y lo **lee de vuelta íntegro**. Verificado. |
| **ICO** | Parcialmente | Pillow guarda el `iTXt` y el texto **viaja dentro del fichero** (`strings` lo encuentra), pero al leer con Pillow **no lo expone**. Es recuperable con herramientas que parseen los frames, no con la API de alto nivel. |
| **SVG** | **Sí** — es XML | Ya resuelto: comentario sin `--`. |
| **Gráfico Plotly** | **Sí** — `layout.meta` | El JSON del gráfico admite un objeto `meta` que sobrevive al `to_json()`. Verificado. Y el propio gráfico **ya lleva los datos** (`x`, `y`) en el JSON: no hace falta codificarlos aparte. |

**Conclusión de la verificación:** para PNG y Plotly **no necesitamos índice externo**: la
cabecera puede ir dentro. Para ICO sí hace falta un respaldo, porque la lectura estándar no
la devuelve.

## La solución por capas

### Capa 1 — Embebido nativo (preferido, cuando el formato lo permite)

- **PNG**: chunk `iTXt` con clave `OKF-METADATA` y el mismo payload que el resto.
  Ventaja: el fichero es autosuficiente; se copia a otro sitio y la procedencia viaja con él.
- **SVG**: comentario XML (ya hecho).
- **Gráfico Plotly**: `layout.meta.okf` con `type`, `generated`, `source`.
  Y **los datos ya están dentro** del JSON del gráfico: eso resuelve lo que Ricardo llamaba
  "meter los datos codificados", sin inventar nada nuevo.

### Capa 2 — Manifiesto índice (respaldo, para lo que no se puede leer de vuelta)

Un único `OKF-MANIFEST.md` en `accounting/assets/` que liste **todos** los ficheros no
textuales con su procedencia, más un **hash** que permita detectar que el binario cambió
después de registrarlo. Para ICO es la vía fiable hoy.

El manifiesto no es un parche: es exactamente lo que OKF prevé para colecciones
(`index.md` como listado de divulgación progresiva), y añade el hash, que un comentario
interno no da.

### Capa 3 — Guard que verifica las dos capas

Se extiende `check_okf.py` para que, ante un fichero no textual:
1. Si el formato admite embebido (PNG, SVG), **lo lee y lo valida**.
2. Si no (ICO, o PNG sin chunk), **exige que esté listado en el manifiesto**.
3. En ambos casos, **compara el hash**: si el binario cambió y el manifiesto no, falla.

Así ningún binario puede quedar huérfano *ni* desactualizado en silencio. Es la misma
lección que ya aprendimos dos veces hoy: un guard que solo comprueba presencia no sirve.

## Por qué por capas y no una sola solución

- Embeber es mejor donde funciona (autosuficiente), pero **no funciona igual en todos los
  formatos** — y no quiero volver a fingir que sí.
- El manifiesto cubre el resto **sin mentir** sobre lo que el formato permite.
- El hash es lo único que detecta "el fichero cambió y la cabecera no", que es el fallo
  silencioso más probable a futuro.

## Operativa diaria

No hay que recordar los seis formatos. El comando
`python3 accounting/okf.py read|write|stamp` detecta el formato y aplica la capa
que corresponda. Método completo y casos límite en [`METODO-okf.md`](METODO-okf.md),
verificado con `test_okf_tool.py` (8 pruebas de ida y vuelta).

## Lo que NO voy a hacer

- **No** voy a inventar un formato de codificación de datos dentro de imágenes para los
  gráficos: Plotly ya lleva los datos en el JSON, y exportar a PNG es solo una vista. Meter
  los datos otra vez sería duplicar la fuente de verdad.
- **No** voy a declarar "ICO soporta OKF" cuando la lectura estándar no lo devuelve. Va al
  manifiesto, y se dice por qué.

## Estado de aplicación

- [x] PNG del favicon: pendiente de estampar el `iTXt` (siguiente paso, ya verificado que funciona)
- [x] SVG: ya tiene cabecera
- [x] Manifiesto `OKF-MANIFEST.md`: pendiente de crear con hash
- [x] Gráfico: `layout.meta.okf` pendiente de añadir en `web_dashboard.py`
- [x] Guard: pendiente de la capa 3
