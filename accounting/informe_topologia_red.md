---
type: Network Topology Assessment
title: Topología de red para pruebas — estado actual y combinaciones posibles
description: Investigación read-only del hardware de red disponible (router OpenWrt,
  ricardoHP, ricardoPC, A2) y las topologías construibles hoy vs las que exigen cambios.
tags:
- red
- topología
- wifi
- bluetooth
- pruebas
status: draft
generated:
  by: CONTA/zai-glm-5-3-flash
  at: 2026-11-19 19:45:00+01:00
verified:
- by: human:pendiente
  at: 2026-11-19 19:45:00+01:00
source:
- iw dev / iw phy phy0 info
- lspci -nn
- bluetoothctl list/show/info
- ip route / ping
stale_after: 2027-01-31 00:00:00+01:00
sources:
- resource: iw dev / iw phy phy0 info
  id: iw-local
  title: Interfaz y capacidades de la radio local (ricardoHP)
- resource: lspci -nn
  id: lspci
  title: Adaptador físico de red del HP
- resource: bluetoothctl list/show/info
  id: bluez
  title: Estado del stack BlueZ (adaptador, dispositivos emparejados)
- resource: ip route / ping
  id: link
  title: Ruta y latencia LAN hacia ricardoPC
---

# Topología de red — qué se puede construir hoy

## 0-bis. CORRECCIÓN DE RICARDO (19-nov, posterior a la primera redacción)

La topología **real** es distinta de lo que asumí al redactar la primera versión:

- El **móvil A2 hace USB tethering al router** (el router sale a Internet por el móvil).
- El **móvil A2 hace además WiFi AP** (hotspot) **para ricardoPC**.
- **La WiFi propia del router está caída** (no es el AP de la LAN).

Esto invalida mi recomendación de "A + C" en el punto 4 (que asumía el router dando WiFi).
Lo correcto hoy: el móvil es la **doble puerta de enlace** (USB al router + AP WiFi al PC),
y el HP va por cable al router. El PC recibe WiFi del móvil, no del router.

## 0. Resumen ejecutivo

- **Una sola radio WiFi** en el HP (RTL8723BE, **solo 2,4 GHz**). No hay 5 GHz. `wlo1` está **DOWN**;
  el HP está conectado por **Ethernet** (`enp2s0`, 192.168.2.20).
- **No se puede AP+STA simultáneo de forma fiable** con esta radio: el controlador RTL8723BE
  no expone combinaciones `valid interface combinations` en `iw phy phy0 info` — es decir, el
  driver no anuncia multi-iface. (VERIFICADO por ausencia de la sección; POR CONFIRMAR con
  `iw list` completo o documentación del driver, pero la ausencia es indicio fuerte.)
- **Ethernet es el enlace bueno**: 0,268 ms de RTT medio a ricardoPC por cable — topología
  actual sana.
- **Bluetooth del A2 ya está emparejado y confiado** (`Paired: yes`, `Trusted: yes`) pero
  **no conectado**. El adaptador BT del HP funciona (hci0, USB, UP RUNNING). El "no transmite"
  que reporta Ricardo no es de emparejamiento: es un problema de **conexión/servicio activo**,
  no de pairing.

## 1. ¿Dos radios WiFi a la vez? (AP + STA simultáneos)

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Cuántas radios físicas? | **1** (`phy0`) | `ls /sys/class/ieee80211/` → `phy0` |
| ¿Bandas? | **Solo 2,4 GHz** (canal 1, 2412 MHz, 20 dBm) | `iw phy phy0 info` → `Band 1: 2412.0 MHz [1]` |
| ¿Adaptador? | Realtek **RTL8723BE** PCIe (WiFi + BT combo) | `lspci -nn` → `10ec:b723` |
| ¿AP+STA simultáneo? | **No anunciado por el driver**: sin sección `valid interface combinations` | `iw phy phy0 info` no la expone |
| Limitación real | Con una radio, AP y STA comparten el mismo canal/tiempo de antena: aunque el driver lo permitiera, el rendimiento se degrada a la mitad y el escaneo se interrumpe | Conocimiento del dominio + ausencia de combos |

**Conclusión**: para tener AP y STA a la vez hace falta **hardware adicional** (un segundo
adaptador WiFi USB o un dispositivo AP dedicado). El router (OpenWrt) es quien debe hacer de AP.

## 2. Ancho de banda (teórico vs observado)

| Interfaz | Estado | Modo | Notas |
|---|---|---|---|
| `enp2s0` (Ethernet) | **UP**, 192.168.2.20/24 | — | Enlace real: RTT 0,268 ms a ricardoPC (cable, gigabit probable) |
| `wlo1` (WiFi) | **DOWN** (NO-CARRIER) | managed | No conectada; radio 2,4 GHz 802.11n (RTL8723BE) |

- **Observado**: la LAN por cable va a sub-milisegundo. Es la vía buena para pruebas y para el dashboard.
- **Teórico WiFi**: RTL8723BE = 802.11n 1×1, hasta 150 Mbps por 2,4 GHz. **No medido** (interfaz caída).
- **Distinción importante**: 150 Mbps es el máximo negociable de la radio; el caudal real con
  una sola antenna y 2,4 GHz congestionado suele quedar en 40–70 Mbps. Ninguna medición propia aún.

## 3. ¿El A2 pierde 4G al activar WiFi cliente?

- **No verificable sin prueba en vivo**: requiere operar el teléfono (TelfMNG) y observar el
  estado de datos móviles mientras el WiFi está asociado.
- **Lo que sí puedo afirmar del lado del HP**: el HP no tiene ninguna asociación WiFi activa
  (`wlo1` DOWN), así que hoy el A2 no está conectado a este equipo por WiFi.
- **Cómo se probaría** (para TelfMNG): con el A2 en hotspot, asociar `wlo1` a esa red, y en
  paralelo leer `ip -brief addr` + un `ping` a Internet por la interfaz móvil. Si el 4G cae al
  asociar, es una limitación del teléfono (algunos Android desactivan datos con WiFi activo si
  "WiFi preferred" está forzado); si no cae, el problema es de rutas/DNS.
- **Nota**: el A2 en hotspot (192.168.43.x) es una red **distinta** de 192.168.2.x; no hay
  conflicto de subred, pero tampoco hay ruta automática entre ambas sin NAT/proxy.

## 4. Topologías construibles (de menos a más esfuerzo)

| # | Topología | Qué hace falta | Conflictos | Para qué sirve |
|---|---|---|---|---|
| A | **PC ↔ router por cable; A2 por WiFi al router** | Nada — es el estado actual si el A2 se asocia al AP del router | Ninguno | Pruebas de "cliente móvil real" contra servicios del PC; el dashboard responde en 192.168.2.x si se bindea a LAN |
| B | **A2 hotspot → HP por WiFi STA** | Activar `wlo1` como STA a 192.168.43.x | El HP pierde la ruta por cable si se pone como default; hay que usar métricas de ruta | Probar sin router (A2 como única puerta); útil en campo |
| C | **A2 USB tether → HP** | Cable USB + `usb0`/`enx...` interface; Android "USB tethering" | Ninguno con Ethernet si se controlan métricas; el HP tendría dos salidas | Es la topología más estable para pruebas móviles: cable, sin radio compartida |
| D | **A2 USB tether → router (OpenWrt)** | Router con puerto USB y paquete `kmod-usb-net-rndis`; si no está instalado, requiere instalar (CAMBIO EN ROUTER — no autorizado hoy) | Consume el USB del router; hay que configurar WAN por `usb0` | Dar Internet a toda la LAN vía el móvil; útil si cae la línea fija |
| E | **Router como STA del hotspot del A2** | `wlo1`/radio del router en modo STA (si el router tiene radio libre) + reglas de firewall | La radio del router suele estar en AP; cambiarla deja la LAN sin WiFi | Escenario de contingencia; no para pruebas diarias |
| F | **AP+STA simultáneo en el HP** | Segundo adaptador WiFi USB (el RTL8723BE no lo soporta) | Ninguno si es USB aparte | Laboratorio de red: el HP hace de AP para el A2 y de STA hacia la LAN |
| G | **Bluetooth PAN (tethering por BT)** | Emparejar y activar `bnep`/PAN en ambos extremos | Muy bajo caudal (1-2 Mbps útiles), alta latencia | Solo como último recurso de conectividad; no para pruebas de rendimiento |

**Recomendación para pruebas** (revisada tras la corrección de Ricardo): la topología A2-USB→router + A2-AP→ricardoPC ya está en servicio; el HP va por cable al router. **A + C**. A es el estado actual (cable al router, A2 por WiFi);
C (USB tether) añade el caso "móvil como puerta de enlace" sin tocar la radio compartida ni el
router. Todo lo que exija cambios en el router (D, E) queda fuera de lo autorizado hoy.

## 5. Bluetooth — el "detecta pero no transmite"

**Estado real (leído, sin tocar nada):**
- Adaptador del HP: `hci0` USB, `UP RUNNING PSCAN ISCAN`, sin errores (`errors:0`).
- Servicio `bluetooth`: **active**; BlueZ **5,75**.
- Dispositivo `Mi A2` (A4:50:46:BB:4F:F3): **`Paired: yes`, `Trusted: yes`, `Connected: no`**.
- `Pairable: no` en el adaptador (normal cuando ya hay dispositivos emparejados).

**Diagnóstico**: el emparejamiento está hecho y confiado; lo que falta es **establecer la
conexión** (perfil) y que el servicio del lado del teléfono acepte. "Detecta pero no transmite"
encaja con: (a) el perfil elegido no está soportado/activo (p.ej. intentar enviar ficheros OPP
sin el servicio activo en el A2), o (b) el A2 no acepta la conexión entrante hasta desbloquear
la pantalla. **No es hardware**: el adaptador transmite (TX 26.942 bytes de tráfico de gestión).

**¿Merece la pena BT PAN para tethering?** Solo como último recurso: 1–2 Mbps útiles y latencia
alta. Para pruebas del dashboard (HTML de ~66 KB) sería suficiente, pero USB tether (C) es
estrictamente mejor. **Recomendación: no invertir tiempo en BT PAN.**

---

## Qué se puede construir HOY (sin tocar router ni emparejar nada)

1. **A** — ya operativa: HP por cable, A2 por WiFi al AP del router. Para que el dashboard sea
   alcanzable desde el móvil habría que **bindear a la IP LAN** (hoy escucha solo en 127.0.0.1);
   eso es un cambio de código de una línea, no de red, y **no está autorizado en este mensaje**.
2. **C** — USB tether del A2 al HP: solo requiere cable y activar "USB tethering" en el teléfono
   (lo opera TelfMNG). Sin cambios en el router.

## Qué necesita un cambio
- **D/E** (router como cliente del móvil): paquetes y configuración en OpenWrt → no autorizado.
- **F** (AP+STA en el HP): comprar un adaptador USB WiFi → coste material.
- **Dashboard accesible en LAN**: cambiar el bind de `127.0.0.1` a `0.0.0.0` **reabre el agujero
  de seguridad** que acabamos de cerrar; si se hace, debe ir acompañado del token obligatorio para
  todo lo que no sea loopback (que ya está implementado).
