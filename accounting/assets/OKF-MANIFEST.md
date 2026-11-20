---
type: Asset Manifest
title: "Manifiesto OKF de binarios"
description: "Capa 2: índice de assets con su hash. Capa 1 es el OKF embebido en el propio fichero."
status: verified
generated: 2026-11-20T21:23:41+01:00
source:
  - "assets/* generado por accounting/okf.py manifest"
verified: 2026-11-20
stale_after: 2027-06-30
---

# Manifiesto OKF de assets

Los binarios no admiten todos la misma cabecera. Solución por capas:

1. **Embebido** — el propio fichero lleva su OKF (PNG: chunk `iTXt`; SVG: comentario XML).
2. **Manifiesto** — esta tabla, para lo que no se puede leer de vuelta (ICO).
3. **Guard** — `check_okf.py` exige que cada binario esté aquí, que su hash coincida
   y que el `iTXt` del PNG sea legible.

Regla: si un asset cambia, su hash cambia aquí en el mismo commit. Se regenera con
`okf.py manifest --target <carpeta de assets>`.

| Fichero | Tipo | Bytes | SHA-256 (16) | OKF embebido |
|---|---|---|---|---|
| `favicon.ico` | ICO (frames PNG) | 9243 | `8cd719082a7bbc2c` | sí en frames; la lectura estándar no lo expone |
| `favicon_64.png` | PNG raster | 3186 | `fae69391d1bd52ba` | sí (iTXt) |
| `favicon_conta.svg` | SVG (XML) | 2150 | `d73d9481e5332241` | sí (<metadata>) |
| `icon-180.png` | PNG raster | 19952 | `21873da1a152280d` | sí (iTXt) |
| `icon-512.png` | PNG raster | 89960 | `68b6efa69003dbd5` | sí (iTXt) |
