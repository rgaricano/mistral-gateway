---
type: Configuration Bundle
title: Configuración de Gentle Shell para el gateway de Mistral
version: "1.0.0"
description: settings.json y models.json de pi extraídos de una instalación de gentle-shell en funcionamiento, reducidos a los proveedores Mistral, para reutilizar en instalaciones nuevas o existentes.
tags: [pi, gentle-shell, mistral-gateway, configuración, openai-completions]
status: stable
language: es
generated: { by: el_gentleman/gentle-pi, at: 2026-11-16T04:49:00Z }
verified: { by: human:rgaricano, at: 2026-11-16T04:49:00Z }
sources:
  - id: gentle-shell-live
    resource: /home/ricardo/.gentle-shell/agent
    title: Configuración viva del agente gentle-shell
    author: human:rgaricano
    last_modified: 2026-11-16T04:49:00Z
  - id: gateway-readme
    resource: ../README.md
    title: Documentación de mistral-gateway
    author: human:Classic298
---

# Configuración de Gentle Shell para el gateway de Mistral

Copia de una configuración de pi/gentle-shell en funcionamiento que habla con el
[mistral-gateway](../README.md) local, reducida a los proveedores Mistral.

Versión en inglés: [README.md](./README.md).

## Qué es cada fichero

| Fichero | Ruta destino | Propósito |
|---------|--------------|-----------|
| `models.json` | `~/.gentle-shell/agent/models.json` | Declara el proveedor `Mistral-local`: URL base, tipo de API, 16 modelos de chat con capacidades reales (niveles de razonamiento, ventana de contexto, modalidades de entrada, coste). |
| `settings.json` | `~/.gentle-shell/agent/settings.json` | Ajustes de ejecución: modelo por defecto, modelos habilitados, umbrales de compactación por modelo. |

Ambos ficheros provienen de `~/.gentle-shell/agent/` en la máquina donde se
configuró el gateway, tomados después de verificar la configuración completa
de punta a punta (razonamiento, tool calls, ambos proveedores Mistral).

## Qué configuran

- **Proveedor** `Mistral-local`: relay compatible con OpenAI en
  `http://127.0.0.1:8788/v1` (este gateway), usando la API `openai-completions`.
  16 modelos de chat, con alias colapsados (`zai-glm-5` → `zai-glm-5-3`, etc.).
- **Por defecto**: `Mistral-local` / `zai-glm-5-3-flash`, nivel de razonamiento
  `medium`.
- **Modelos habilitados**: 28 (16 del gateway + 12 del proveedor `mistral`
  integrado en pi, que apunta a la API pública de Mistral y necesita sus
  propias credenciales en `auth.json`).
- **Compactación**: habilitada, con overrides por modelo — los modelos con
  ventana de contexto >= 500K tokens compactan al 60% de uso, los más pequeños
  al 80%.

## Niveles de razonamiento

El `thinkingLevelMap` de `models.json` solo ofrece los niveles que cada modelo
acepta realmente. Es deliberado: el canal Vibe-Code del gateway mapea
silenciosamente un nivel no soportado al más cercano que sí lo sea, así que
ofrecer niveles que un modelo no puede honrar haría que pi mostrara opciones
que no hacen lo que dicen (un `medium` que en realidad es `high`, gastando el
presupuesto Vibe en consecuencia).

| Modelo | Niveles ofrecidos |
|--------|-------------------|
| `deepseek-v4-1-flash-1017` | off, low, high, xhigh, max |
| `zai-glm-5-3`, `zai-glm-5-3-flash`, `glm-5.2` | low, high, max |
| `mistral-large`, `mistral-large-4`, `mistral-medium-latest`, `mistral-small-2603`, `magistral-medium-latest`, `labs-leanstral-1-5-1`, `mistral-vibe-cli-with-tools` | off, high |
| `codestral-2508`, `ministral-*`, `voxtral-small-2507` | sin razonamiento |

Notas:

- Vibe-Code solo concede a cada modelo un subconjunto de los niveles
  estándar; por eso el mapa es más estrecho que el conjunto completo de pi.
  El gateway mapea cualquier otro al nivel soportado más cercano (hacia abajo
  para `minimal`/`low`, hacia arriba para el resto).
- `off` se mapea al `none` del gateway. Los modelos `zai-glm-*` no pueden
  apagar el razonamiento, solo bajarlo a `low`.
- Los niveles ocultos con `null` no se envían; pi ajusta la selección al
  soportado más cercano en lugar de dejar que el gateway decida en silencio.

## Criterio de compactación

La compactación resume la conversación cuando crece demasiado. Los umbrales
siguen dos buenas prácticas recomendadas para mantener la calidad de
respuesta de los modelos:

- **Ventanas grandes (>= 500K tokens) compactan al 60% de uso** (reserva
  419430 de 1048576). Un transcript enorme degrada el foco del modelo mucho
  antes de llenar la ventana, así que resumir antes mantiene las respuestas
  precisas; y resumir tanto contenido es caro, así que no debe pasar
  constantemente.
- **Las ventanas más pequeñas compactan al 80% de uso** (reserva ~52428 de
  262144). Hay menos margen, pero el transcript también es más barato de
  resumir, así que puede esperar un poco más.
- **Los modelos pequeños (`ministral-*`, `voxtral-small-2507`, reserva 0) no
  compactan.** pi no tiene un interruptor de compactación por modelo;
  `reserveTokens: 0` es el equivalente más cercano (el disparador solo actúa
  al pasar la ventana completa, lo que en la práctica nunca ocurre). Sus
  ventanas son demasiado pequeñas para que un resumen compense: la propia
  petición de resumen se comería buena parte del contexto que tiene el
  modelo.

## Precios

El campo `cost` de `models.json` lleva los **precios oficiales de lista** de Mistral (USD por millón de tokens), tomados de la [página de precios de Mistral](https://docs.mistral.ai/inference/pricing) y la documentación de cada modelo. pi los multiplica por los tokens de cada petición, y eso es lo que muestran las estadísticas de sesión.

| Modelo | Input $/M | Input €/M | Input caché $/M | Input caché €/M | Output $/M | Output €/M |
|--------|----------:|----------:|----------------:|----------------:|-----------:|-----------:|
| `magistral-medium-latest` | 2 | 1,84 | 0,15 | 0,138 | 5 | 4,6 |
| `mistral-medium-latest` | 1,5 | 1,38 | 0,15 | 0,138 | 7,5 | 6,9 |
| `zai-glm-5-3` | 1,4 | 1,288 | 0,14 | 0,1288 | 4,4 | 4,048 |
| `glm-5.2` | 1,4 | 1,288 | 0,26 | 0,2392 | 4,4 | 4,048 |
| `mistral-large` | 0,7 | 0,644 | 0,07 | 0,0644 | 2,1 | 1,932 |
| `mistral-large-4` | 0,7 | 0,644 | 0,07 | 0,0644 | 2,1 | 1,932 |
| `deepseek-v4-1-flash-1017` | 0,3 | 0,276 | 0,007 | 0,0064 | 1,2 | 1,104 |
| `codestral-2508` | 0,3 | 0,276 | 0,03 | 0,0276 | 0,9 | 0,828 |
| `ministral-14b-2512` | 0,2 | 0,184 | 0,02 | 0,0184 | 0,2 | 0,184 |
| `zai-glm-5-3-flash` | 0,15 | 0,138 | 0,03 | 0,0276 | 0,5 | 0,46 |
| `mistral-small-2603` | 0,15 | 0,138 | 0,015 | 0,0138 | 0,6 | 0,552 |
| `mistral-vibe-cli-with-tools` | 0,15 | 0,138 | 0,015 | 0,0138 | 0,6 | 0,552 |
| `ministral-8b-2512` | 0,15 | 0,138 | 0,015 | 0,0138 | 0,15 | 0,138 |
| `ministral-3b-2512` | 0,1 | 0,092 | 0,01 | 0,0092 | 0,1 | 0,092 |
| `voxtral-small-2507` | 0,1 | 0,092 | 0,01 | 0,0092 | 0,3 | 0,276 |
| `labs-leanstral-1-5-1` | 0 | 0 | 0 | 0 | 0 | 0 | (preview de Labs, gratis)

Cambio aproximado: 1 USD ≈ 0,92 EUR (solo referencia; los valores `cost` de `models.json` son la columna USD). `cacheWrite` está a 0 en todos: Mistral no factura por separado la escritura en caché.

**Qué son y qué no son estos números.** El plan Vibe es un presupuesto mensual, no pago por token: el endpoint `/quota` del gateway es la fuente de verdad del gasto real. Medido contra una exportación real de facturación, el uso de esta configuración se factura a ~0,92x de los precios de lista, así que las estadísticas son una referencia justa para comparar modelos y estimar costes, ligeramente por encima de lo que el plan consume realmente. Dos motivos por los que el número real sale más bajo: la mecánica del presupuesto del plan, y la caché de prompt — más de la mitad del tráfico medido se sirvió desde caché al 10-20% del precio de entrada.

Ejemplo de una exportación real anonimizada de 16 días: ~240M de tokens totales en `zai-glm-5-3-flash`, de los que ~197M (82%) fueron lecturas cacheadas. A precios de lista ese uso ronda los $9,76; el descuento por caché es lo que mantiene la tarifa efectiva a la baja, no un descuento por token del plan.

## Qué suscripción usa cada proveedor

Los dos proveedores de `models.json` llegan a Mistral por caminos distintos:

- **`Mistral-local`** pasa por este gateway. Usa la **suscripción Pro de
  Mistral** mediante la clave Vibe: el gateway envía las peticiones con
  **precedencia Vibe-Code** (el presupuesto del plan Vibe se consume primero)
  y hace fallback a la **clave de API de Studio** cuando la clave Vibe está
  limitada por tasa o agotó su presupuesto mensual. El manejo de credenciales
  vive por completo en el gateway (`gateway.env`); gentle-shell nunca ve una clave para
  este proveedor.
- **`mistral`** (el proveedor integrado en pi) habla con la API pública de
  Mistral directamente desde gentle-shell, con credenciales configuradas en
  el propio gentle-shell (`gentle-shell auth login mistral`). Usa el **acceso API de la
  suscripción Pro directamente**, con **precedencia API y sin acceso a
  Vibe-Code**: lo que se consume ahí se factura por el uso de API del plan,
  nunca por el presupuesto de código Vibe.

Ambos apuntan al mismo plan Pro, pero por puertas distintas: lo que cada uno
gasta depende del canal que tomó la petición.

## Instalación nueva

Prerrequisito: el gateway corriendo localmente (ver el
[README principal](../README.md)).

1. Copiar los ficheros a sus rutas destino, creando el directorio si hace
   falta:

   ```bash
   mkdir -p ~/.gentle-shell/agent
   cp models-mistral-only.json ~/.gentle-shell/agent/models.json
   cp settings-mistral-only.json ~/.gentle-shell/agent/settings.json
   ```

2. Si se quiere el proveedor público `mistral`, añadir sus credenciales:

   ```bash
   gentle-shell auth login mistral
   ```

   Sin credenciales esos 12 modelos `mistral/*` quedan listados pero fallan
   al usarse.

3. Reiniciar gentle-shell para que se cargue la configuración.

## Instalación existente

Fusionar en vez de sobrescribir: la máquina destino puede tener otros
proveedores (`Omniroute-local`, `LlamaSwap-local`, ...) que deben sobrevivir.

1. Hacer copia de seguridad de los ficheros actuales:

   ```bash
   cp ~/.gentle-shell/agent/models.json ~/.gentle-shell/agent/models.json.bak
   cp ~/.gentle-shell/agent/settings.json ~/.gentle-shell/agent/settings.json.bak
   ```

2. En `models.json`, añadir el proveedor `Mistral-local` de este paquete al
   objeto `providers` existente. No reemplazar el fichero completo si hay
   otros proveedores presentes.

3. En `settings.json`, fusionar tres secciones:
   - `enabledModels`: añadir las 28 entradas de este paquete.
   - `compaction.modelOverrides`: añadir los umbrales por modelo.
   - `defaultProvider` / `defaultModel`: poner `Mistral-local` /
     `zai-glm-5-3-flash` solo si la instalación debe cambiarse a este proveedor.

4. Reiniciar gentle-shell.

## Advertencias

- El gateway debe ser accesible en `127.0.0.1:8788`; si escucha en otro
  sitio, actualizar `baseUrl` en `models.json`.
- `models.json` es la única fuente de verdad para los proveedores: no hace
  falta ninguna extensión custom-provider, e instalar una ensombecería esta
  configuración.
- Los niveles de razonamiento están restringidos a lo que cada modelo acepta
  realmente (el gateway mapea silenciosamente los niveles no soportados). Los
  modelos `zai-glm-*` no pueden apagar el razonamiento, solo bajarlo.
