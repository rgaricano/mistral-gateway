---
type: Operational Note
title: "Dependencias de red del dashboard y del parte diario"
description: "Qué depende del túnel y qué no, medido el 20-nov-2026. Corrige la suposición de que el parte diario necesita el túnel estable: no lo necesita."
tags: [operaciones, red, túnel, tailcat, dashboard]
status: verified
generated: 2026-11-20T22:30:00+01:00
source:
  - "accounting/daily_report.py (cadena de llamadas verificada)"
  - "accounting/data.py::live_quota"
  - "gateway.py::read_quota y MISTRAL_*_URL"
  - "ss -tlnp y pgrep -af 'tailcat serve' (medición del 20-nov)"
verified: 2026-11-20
stale_after: 2026-12-15
---

# Dependencias de red: qué necesita el túnel y qué no

Nota escrita el 20-nov porque circulaba una suposición razonable pero falsa:
«si el túnel está inestable, el parte diario puede fallar». **No puede.**
Comprobado siguiendo la cadena de llamadas, no leyendo la intención del código.

## El parte diario no pasa por el túnel

```
daily_report.py
  → data.live_quota()
    → gateway.read_quota()
      → urllib.request.urlopen()
        → https://api.mistral.ai/v1/billing/budget
```

Salida directa a internet. No pasa por el daemon de Companion ni por ningún
`tailcat`. Si el daemon cae, el parte se sigue generando.

El dashboard, igual: escucha en `127.0.0.1:8799` y funciona en local sin túnel.

## Lo que sí está roto (medido el 20-nov)

| Hecho | Medición |
|---|---|
| Procesos `tailcat serve` | **7** (no 3), todos peleando por el puerto 43722 |
| Identidades en conflicto | **2**: `~/.pi/agent/pi-companion/tailcat/…` y `~/.gentle-shell/agent/pi-companion/tailcat/…` |
| Túnel del dashboard (8799) | **ninguno activo** — nadie sirve ese puerto por túnel |

Consecuencia: el dashboard **solo es alcanzable en local**. El acceso remoto está
caído, no el dato. Consolidar esos procesos es de INFRA/ORQ, no de contabilidad.

## Por qué se anota en vez de arreglarse

Tocar procesos del daemon de otra sesión es exactamente el tipo de acción que
requiere autorización explícita y conocimiento de qué está sirviendo cada uno.
Mi trabajo depende de la lectura de `api.mistral.ai`, que va por otra vía, así
que no me bloquea. Se anota para que nadie depure el túnel creyendo que el parte
diario lo necesita.

Si algún día el parte diario se sirve **por** el túnel, esta nota cambia y el
túnel pasa a ser dependencia crítica. Hoy no lo es.
