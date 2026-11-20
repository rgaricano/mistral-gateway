---
type: Investigation
title: "Granularidad horaria del consumo: qué ofrece el proveedor y qué alcanza nuestra clave"
description: "Investigación del 20-nov sobre la posibilidad de monitorizar el consumo con detalle sub-horario. Conclusión: la granularidad fina existe, pero NO es alcanzable con la clave del plan Individual; la superficie donde Ricardo la ve es de navegador."
tags: [monitorización, granularidad, api, límites-del-plan, investigación]
status: verified
generated: 2026-11-20T23:55:00+01:00
source:
  - "docs.mistral.ai/admin/admin-api/usage-metrics (Admin API es Enterprise-only)"
  - "docs.mistral.ai/api/endpoint/beta/admin/billing (POST /v1/admin/usage/query)"
  - "Sondeo propio contra api.mistral.ai con la clave del plan (20-nov, endpoints y códigos de estado)"
verified: 2026-11-20
stale_after: 2027-03-01
---

# Granularidad del consumo: lo que se puede y lo que no

Ricardo indicó que el proveedor da desglose horario en rangos menores a una
semana, y de 3 h, 1 h, 15 min, con datos de hasta 1 segundo, y que él lo ve en
`admin.mistral.ai`. Investigado. **La parte de que existe es cierta; la parte de
que podamos consultarla desde aquí, no.** Conviene distinguirlas antes de
prometer una monitorización al segundo.

## 1. La granularidad fina existe — en el Admin API

El endpoint que la ofrece es:

```
POST https://api.mistral.ai/v1/admin/usage/query
{
  "start": "...", "end": "...",
  "granularity": "...",     ← aquí va el cubo de tiempo
  "include_nb_api_calls": true
}
```

Admite agrupación y cubos de tiempo elegidos por quien llama, paginación y
recuento de llamadas distintas. Devuelve cantidades, no precios. Documentación:
`docs.mistral.ai/admin/admin-api/usage-metrics` y
`docs.mistral.ai/api/endpoint/beta/admin/billing`.

## 2. Pero es Enterprise-only, y nuestro plan no lo es

La documentación es explícita: *«The Admin API is available only on Enterprise
plans, and access isn't self-serve. On other plans, you can't create an Admin API
key, and a standard API key doesn't work with admin endpoints.»*

Comprobado, no supuesto:

| Sondeo con nuestra clave | Resultado |
|---|---|
| `POST api.mistral.ai/v1/admin/usage/query` | **401 Invalid API Key** |
| `GET admin.mistral.ai/api/billing/v2/usage` | **403 error code 1010** (bloqueo de Cloudflare) |

Nuestro plan es **Individual**. No hay Admin API key, y la clave de suscripción
no vale en endpoints de administración.

## 3. La superficie donde Ricardo lo ve es de navegador, no de API

La URL que Ricardo usa (`admin.mistral.ai/organization/usage?…granularity=second…`)
es el panel web. Esa interfaz **sí** pinta la granularidad al segundo porque está
autenticada con su **sesión de navegador**, no con la clave del gateway. No es una
API pública reutilizable: responde 403 a la clave y exige cookies de sesión.

Consecuencia: **el dato existe, pero el camino para leerlo desde un script está
cerrado para este plan.** Que exista una vista no significa que exista un
endpoint que podamos llamar.

## 4. Lo que sí devuelve nuestra clave: un agregado sin serie

`GET api.mistral.ai/v1/billing/budget` (el que usa `read_quota()`) devuelve
**solo** el estado actual:

```json
{"vibe_budget": {"usage_percentage": 26.75, "initial_budget": 255.0,
                 "currency": "EUR", "reset_at": "2026-12-01T00:00:00Z",
                 "payg_enabled": false}}
```

Y **ignora** los parámetros de ventana o granularidad. Lo verifiqué comparando
cuerpos de respuesta:

| Parámetro añadido | ¿Cambia la respuesta? |
|---|---|
| `?granularity=second` | **no** (idéntica) |
| `?period=last15Minutes` | **no** (idéntica) |
| `?start=2026-11-01T00:00:00Z` | **no** (idéntica) |

Devuelve 200 con cualquier parámetro, pero el cuerpo es el mismo: **acepta la
petición y no atiende el parámetro**. Un 200 aquí no significa «soportado».

## 5. Por tanto: qué se puede construir y qué no

**No se puede** con el plan actual:
- monitorización al segundo vía API;
- desglose horario automático;
- llamadas cada 15 min que devuelvan una serie temporal más fina que «ahora».

**Sí se puede**, y es lo que ya hacemos:
- muestrear `usage_percentage` cada N minutos y **construir nuestra propia serie
  temporal** con esos muestreos. La granularidad resultante es la del muestreo
  (15 min si muestreamos cada 15 min), no la del proveedor, pero es real y
  verificable;
- el detalle por **día, modelo y cuenta** desde `usage.db`, que sí existe y es
  fiable.

Esto es importante y no hay que disfrazarlo: **muestrear cada 15 minutos da una
serie de 15 minutos.** No da «detalle al segundo» y decir lo contrario sería
vender una monitorización que no existe. Lo que da es bueno: se puede ver **cuándo
empieza un pico, cuánto dura y a qué ritmo crece** — que es exactamente lo que
faltaba hoy para explicar el consumo.

## 6. Lo que hay que hablar con INFRA

Nada de esto es mío: el muestreo periódico es un proceso que corre siempre, y eso
es infraestructura. Preguntas concretas para INFRA:

1. **¿Quién hace el muestreo?** Un `cron`/timer de usuario que llame a
   `read_quota()` y escriba en una tabla nueva `allowance_samples(ts, percent)`.
   No requiere reiniciar el gateway ni tocar su código: es un script aparte.
2. **¿Cada cuánto?** Cada 15 min son 96 muestras/día, coste de API despreciable
   (una lectura de budget no consume tokens).
3. **¿Dónde se guarda?** Propuesta: `usage.db`, tabla nueva, para no multiplicar
   ficheros. Migración aditiva, no destructiva.
4. **¿Se puede obtener el detalle al segundo de otra forma?** Solo si existe una
   sesión de navegador reutilizable o un endpoint autenticado por cookie. Eso es
   frágil (rompe con cada cambio de sesión) y no lo recomiendo como base de un
   sistema contable.

## 7. Recomendación

1. **Corto plazo:** el script de muestreo cada 15 min, propiedad de INFRA, con la
   tabla en `usage.db`. Da trazabilidad temporal real y habría respondido la
   pregunta de hoy («¿cuándo se disparó?»).
2. **Si Ricardo quiere el segundo de verdad:** el camino no es una API, es la
   **exportación del panel web** que él ya puede hacer. Ese CSV sí tendría la
   granularidad del proveedor. Importarlo es trivial; automatizarlo no, porque
   depende de su sesión.
3. **No prometer** granularidad al segundo por API mientras el plan sea Individual.

## Lo que esta investigación corrige

Mi informe anterior decía que no había forma de saber a qué hora se disparó el
consumo porque `usage.db` solo guarda el día. Eso era cierto **para nuestra
base de datos**, pero incompleto: el proveedor sí tiene el dato fino. Lo que no
tiene es un camino abierto para que lo leamos. La distinción importa: no es que
«no exista», es que «no está a nuestro alcance con este plan».
