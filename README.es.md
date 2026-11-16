# mistral-gateway

Un pequeño proxy local que permite a cualquier cliente de chat compatible con OpenAI (Open WebUI, editores, scripts) usar los modelos incluidos en tu suscripción de Mistral Vibe. Es un único fichero de Python sin dependencias más allá de la librería estándar.

Usa la misma clave que crea el [CLI oficial de Mistral Vibe](https://github.com/mistralai/mistral-vibe) al iniciar sesión, envía las peticiones a la API pública de Mistral y devuelve las respuestas en la forma exacta que los clientes OpenAI esperan.

> **Proyecto no oficial.** No está afiliado, respaldado ni soportado por Mistral AI. Lee la sección «Términos de servicio» antes de usarlo.

Versión en inglés: [README.md](./README.md).

## Configuración

Requisitos: Python 3.10+ y un plan de Mistral Vibe con código incluido (Pro, Team o Enterprise).

1. Consigue el gateway:

   ```sh
   git clone https://github.com/Classic298/mistral-gateway.git
   cd mistral-gateway
   ```

2. Consigue tu clave Vibe. Hay dos formas, elige una.

   **Opción A: inicia sesión con el CLI de Vibe.** Instala el CLI oficial de Vibe (ver el [repositorio de Mistral Vibe](https://github.com/mistralai/mistral-vibe) para otros métodos de instalación) e inicia sesión con tu cuenta de Mistral, eligiendo el login por navegador en el asistente de configuración:

   ```sh
   curl -LsSf https://mistral.ai/vibe/install.sh | bash
   vibe --setup
   ```

   El CLI guarda tu clave del plan en `~/.vibe/.env`. El gateway la lee de ahí, así que nunca copias la clave a mano.

   **Opción B: cópiala desde la web.** No hace falta el CLI. Abre [Code › Extensions](https://chat.mistral.ai/code/extensions) en Vibe, despliega **Advanced** en la tarjeta del Vibe CLI y copia la **Vibe API Key**. El mismo panel muestra tu uso mensual y permite rotar la clave. Luego crea `gateway.env` junto a `gateway.py`:

   ```sh
   VIBE_KEY=tu-clave-vibe
   ```

   ![Copiando la Vibe API Key desde Code › Extensions](assets/vibe-key.gif)

3. Opcional: añade una clave de API de Studio como fallback para cuando la clave Vibe esté limitada por tasa o su presupuesto mensual agotado. En el panel de administración de Mistral, abre **API › API Keys** y pulsa **New key**, luego añádela a `gateway.env`:

   ```sh
   STUDIO_API_KEY=tu-clave-studio
   ```

   ![Creando una clave de Studio bajo API › API Keys](assets/studio-key.png)

4. Arranca el gateway:

   ```sh
   python3 gateway.py
   ```

   Funciona igual en Linux, macOS y Windows (en Windows el comando suele ser `py gateway.py`). Mantén la terminal abierta mientras lo usas, o ver [ejecutarlo como servicio](#ejecutarlo-como-servicio-linux-opcional) en Linux.

   El log muestra el nombre de tu plan cuando la clave funciona, y lista `studio` también si añadiste uno:

   ```
   INFO vibe plan: ... (...)
   INFO mistral gateway on 127.0.0.1:8788 (keys: vibe)
   ```

5. Apunta tu cliente hacia él:

   - URL base: `http://127.0.0.1:8788/v1`
   - Clave de API: cualquier valor (o el valor de `GATEWAY_KEY` si configuraste uno)
   - Modelo: cualquier ID de `curl http://127.0.0.1:8788/v1/models`

   Las peticiones deben enviarse como `Content-Type: application/json`. Los navegadores no pueden llamar al gateway directamente; está pensado para clientes de servidor y escritorio.

   Prueba rápida:

   ```sh
   curl http://127.0.0.1:8788/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "mistral-small-latest", "messages": [{"role": "user", "content": "Hola"}]}'
   ```

### Open WebUI

1. Abre **Settings** y elige **Connections** en la parte **Admin** de la lista (versiones antiguas: **Admin Panel › Settings › Connections**). Pulsa ➕ (**Add Connection** junto a **Manage OpenAI API Connections**.
2. Introduce la URL para tu caso (elige la que corresponda más abajo). Como clave de API, introduce tu `GATEWAY_KEY` si configuraste uno, o cualquier placeholder como `none`.
3. Opcional pero recomendado: tu plan incluye docenas de modelos, incluidos modelos de embedding, OCR y transcripción que no pueden chatear. En la misma ventana, añade solo los que quieras bajo **Model IDs** (por ejemplo `zai-glm-5-3-flash`), para que el selector de modelos se mantenga corto. Déjalo vacío para obtenerlos todos.
4. Pulsa **Save** y abre el selector de modelos. Tus modelos aparecerán ahí.

Qué URL usar depende de cómo ejecutes Open WebUI. Pulsa la que corresponda:

<details>
<summary><b>Open WebUI instalado directamente (pip, uv, app de escritorio)</b></summary>

<br>

- URL: `http://127.0.0.1:8788/v1`
- Clave de API: cualquier valor

</details>

<details>
<summary><b>Open WebUI en Docker con <code>--network host</code></b></summary>

<br>

El contenedor comparte la red del host, así que la configuración por defecto funciona tal cual.

- URL: `http://127.0.0.1:8788/v1`
- Clave de API: cualquier valor

</details>

<details>
<summary><b>Open WebUI en Docker en Linux (red por defecto)</b></summary>

<br>

Dentro del contenedor, `127.0.0.1` es el propio contenedor, así que no puede alcanzar un gateway que solo escucha en el loopback del host. Haz que el gateway escuche también en el bridge de Docker, que solo pueden alcanzar los contenedores de esta máquina, y protégelo con una clave.

1. Encuentra la dirección del bridge (normalmente `172.17.0.1`):

   ```sh
   ip -4 addr show docker0
   ```

2. Añade a `gateway.env` y reinicia el gateway:

   ```sh
   BIND=172.17.0.1
   GATEWAY_KEY=elige-una-cadena-larga-aleatoria
   ```

3. Arranca el contenedor de Open WebUI con `--add-host=host.docker.internal:host-gateway` (en Docker Compose: `extra_hosts: ["host.docker.internal:host-gateway"]`).
4. En Open WebUI:
   - URL: `http://host.docker.internal:8788/v1`
   - Clave de API: tu `GATEWAY_KEY`

Los programas del host alcanzan entonces el gateway en `http://172.17.0.1:8788/v1` en lugar de `127.0.0.1`.

</details>

<details>
<summary><b>Open WebUI en Docker Desktop (macOS, Windows)</b></summary>

<br>

Docker Desktop redirige `host.docker.internal` al loopback de tu ordenador, así que el gateway puede quedarse en `127.0.0.1`. Aun así necesita una clave, porque solo responde a otros nombres de host cuando `GATEWAY_KEY` está configurado.

1. Añade a `gateway.env` y reinicia el gateway:

   ```sh
   GATEWAY_KEY=elige-una-cadena-larga-aleatoria
   ```

2. En Open WebUI:
   - URL: `http://host.docker.internal:8788/v1`
   - Clave de API: tu `GATEWAY_KEY`

</details>

### Actualizar

```sh
cd mistral-gateway
git pull
```

Luego reinicia el gateway (`systemctl --user restart mistral-gateway` si lo ejecutas como servicio). Tu `gateway.env` y `usage.db` no se tocan con la actualización.

### Ejecutarlo como servicio (Linux, opcional)

```sh
mkdir -p ~/.config/systemd/user
cp mistral-gateway.service.example ~/.config/systemd/user/mistral-gateway.service
# el ejemplo asume que el clon está en ~/mistral-gateway; si no, edita WorkingDirectory y ExecStart
systemctl --user daemon-reload
systemctl --user enable --now mistral-gateway
journalctl --user -u mistral-gateway -f
```

## Modelos

Todos los modelos siguientes fueron probados a través del gateway con tool calls y todos los niveles de razonamiento. `/v1/models` siempre lista lo que tu clave puede usar.

| Modelo | También disponible como | Contexto | Imágenes | Nivel de razonamiento |
|---|---|---|---|---|
| `mistral-large-4` | `mistral-large-4-0`, `mistral-large`, `mistral-large-latest` | 1M | sí | `none`, `high` |
| `mistral-medium-latest` | `mistral-medium-3-5`, `mistral-medium-2604`, `mistral-vibe-cli-latest` | 256K | sí | `none`, `high` |
| `mistral-small-latest` | `mistral-small-2603`, `mistral-vibe-cli-fast` | 256K | sí | `none`, `high` |
| `zai-glm-5-3` | `zai-glm-latest`, `zai-glm-5`, `zai-glm-5.3`, `glm-5.3` | 1M | no | `low`, `high`, `max` |
| `zai-glm-5-3-flash` | `zai-glm-5.3-flash`, `glm-5.3-flash` | 1M | sí | `low`, `high`, `max` |
| `deepseek-v4-1-flash-1017` | `deepseek-v4.1-flash`, `deepseek-v4.1-flash-1017`, `deepseek-v4-1-flash`, `deepseek-v4-flash-1017` | 1M | no | `none`, `low`, `high`, `xhigh`, `max` |
| `mistral-large-2512` | ninguno | 256K | sí | sin razonamiento |
| `codestral-latest` | `codestral-2508` | 128K | no | sin razonamiento |
| `ministral-14b-latest` | `ministral-14b-2512` | 256K | sí | sin razonamiento |
| `ministral-8b-latest` | `ministral-8b-2512` | 256K | sí | sin razonamiento |
| `ministral-3b-latest` | `ministral-3b-2512` | 256K | sí | sin razonamiento |
| `voxtral-small-latest` | `voxtral-small-2507` | 32K | no | sin razonamiento |

Todos manejan tool calls. Los clientes pueden enviar cualquier nivel estándar de `reasoning_effort` a cualquier modelo. Cuando un modelo no ofrece el nivel solicitado, el gateway usa el más cercano que sí ofrezca, y en caso de empate `minimal` y `low` bajan mientras todo lo demás sube: en Mistral Large 4, Medium y Small, `minimal` y `low` se convierten en `none` y el resto en `high`. Los modelos sin razonamiento reciben la petición sin él. Los nombres con puntos, `mistral-large`, `deepseek-v4-1-flash` y `deepseek-v4-flash-1017` (el nombre en la documentación de Mistral) son alias del gateway. `mistral-large-latest` apunta a Large 4 aquí, mientras que la propia API de Mistral todavía lo mapea a `mistral-large-2512`. Los modelos Labs como `labs-leanstral-1-5` solo responden una vez que un administrador habilita los modelos Labs en la configuración de la organización. También se listan los modelos de embedding, OCR y transcripción, pero el gateway solo sirve chat.

## Configuración

Los ajustes provienen de variables de entorno o de un fichero `gateway.env` junto a `gateway.py` (ver `gateway.env.example`; `gateway.env` gana sobre el entorno).

| Variable | Por defecto | Significado |
|---|---|---|
| `VIBE_KEY` | `MISTRAL_API_KEY` de `~/.vibe/.env` | Tu clave del plan Vibe. Configúrala si copiaste la clave desde Code › Extensions, o para sobrescribir el fichero del CLI. |
| `VIBE_ENV_FILE` | `~/.vibe/.env` | Dónde buscar la clave del CLI de Vibe. |
| `STUDIO_API_KEY` | sin configurar | Clave de fallback de pago por uso opcional de Mistral AI Studio. |
| `GATEWAY_KEY` | sin configurar | Si se configura, los clientes deben enviarla como `Authorization: Bearer <clave>`. Sin ella, el gateway solo responde a peticiones dirigidas a `localhost`, `127.0.0.1` o `[::1]`, así que configúrala si un cliente alcanza el gateway bajo otro nombre de host (p. ej. desde un contenedor Docker). |
| `BIND` | `127.0.0.1` | Dirección de escucha. Mantenla en loopback (ver más abajo). |
| `PORT` | `8788` | Puerto de escucha. |
| `RETRY_429_SECONDS` / `RETRY_429_INTERVAL` | `60` / `10` | Cuánto tiempo y con qué frecuencia reintentar una clave limitada por tasa. |
| `COOLDOWN_429` / `COOLDOWN_DEAD` | `60` / `21600` | Segundos que una clave se salta tras una limitación de tasa / tras un 401 o 402. |
| `LOG_LEVEL` | `INFO` | Nivel de logging de Python. |

Endpoints: `/v1/chat/completions`, `/v1/responses`, `/v1/models`, `/health`, `/pool/status` (qué clave está sirviendo, cooldowns), `/usage?days=N` y `/quota`.

## Qué hace

- Sirve `/v1/chat/completions`, `/v1/responses` y `/v1/models` en `127.0.0.1:8788` y los pasa a las APIs correspondientes de Mistral.
- Corrige los puntos donde las respuestas y campos aceptados de Mistral difieren de los de OpenAI, para que razonamiento, tool calls, conteos de tokens y respuestas largas funcionen en clientes OpenAI.
- Sustituye un nivel de razonamiento que un modelo no ofrece por el más cercano que sí ofrezca.
- Ante una limitación de tasa, reintenta la misma clave durante hasta 60 s. Si la clave Vibe sigue limitada o su presupuesto está agotado, hace fallback a tu clave de Studio si configuraste una.
- Registra el uso diario de tokens por modelo, consultable en `/usage`.
- Muestra tu plan y cuánto del cupo mensual de Vibe se ha usado, en `/quota` y en el log al arrancar.

La API de Responses de Mistral no guarda historial, así que los clientes deben enviar la conversación completa cada vez.

## Términos de servicio

Verificado contra los [Términos de servicio para consumidores de la UE de Mistral AI](https://legal.mistral.ai/terms/eu-consumers-terms-of-service) (vigentes desde el 7 de agosto de 2026) y los [Términos de servicio comerciales de Mistral AI](https://legal.mistral.ai/terms/commercial-terms-of-service) (vigentes desde el 5 de agosto de 2026). Los consumidores fuera de la UE tienen [términos separados](https://legal.mistral.ai/terms). Esta sección es la lectura del autor de esos documentos y **no es asesoramiento legal**.

**Por qué el gateway está diseñado para mantenerse dentro de esos términos:**

- **Clave oficial, API oficial.** La clave proviene del flujo de login propio de Mistral en el CLI oficial de Vibe. El gateway llama al mismo endpoint de la API pública con la misma cabecera estándar `Authorization: Bearer` que usa el CLI. No hace scraping, no suplanta al CLI, no hace ingeniería inversa de nada ni toca ningún mecanismo de seguridad. La [documentación de claves de API de Mistral](https://docs.mistral.ai/admin/identity-access/api-keys) lista las claves Vibe como «Keys used by Vibe Code» y afirma que «los usuarios solo de Vibe normalmente no necesitan claves de API a menos que también usen Studio, la API, Vibe Code u otra herramienta de desarrollador».
- **Los límites de tu plan siguen vigentes.** Cada petición cuenta contra tu plan exactamente igual que una petición del CLI de Vibe. Una limitación de tasa hace que el gateway espere y reintente la misma clave; nunca cambia a otra cuenta de Vibe para sortear el límite. El único fallback es tu propia clave opcional de Studio.
- **Una persona, una cuenta.** Los términos de consumidor de la UE afirman: «La creación o uso de múltiples cuentas de Mistral AI por un mismo individuo está estrictamente prohibido, incluyendo para sortear límites de tasa o cualquier otra restricción». Por eso el gateway soporta exactamente una clave Vibe.
- **Solo uso personal.** Los términos de consumidor también afirman: «Tu cuenta está destinada a tu uso individual únicamente, y no puedes poner las credenciales de tu cuenta a disposición de terceros, [...] ni revender o alquilar el acceso a tu cuenta». Los términos comerciales (sección 2.2) prohíben a los clientes «comprar, vender o transferir claves de API» y «conceder a terceros acceso a los Productos de Mistral AI sin nuestra autorización previa por escrito». Por eso el gateway escucha solo en `127.0.0.1`. **No lo expongas a internet ni lo compartas con otras personas**; hacerlo les daría acceso a tu cuenta.

**Mistral ha confirmado el uso por terceros.** En un [comentario fijado en el subreddit oficial r/MistralAI](https://www.reddit.com/r/MistralAI/comments/1ta8itv/comment/olccfnn/), un moderador con la insignia del equipo de Mistral escribió: «***actualmente puedes usar libremente la clave Vibe con cualquier software, incluidos Hermes y cualquier otro paquete o servicio de terceros. Siempre ha sido así, es decir, si usaste la clave de la API de Vibe a través de terceros, el presupuesto del plan Vibe se usaría primero antes que cualquier pago por uso (PAYG)***». En el mismo hilo, el usuario que preguntó reporta que el soporte de Mistral lo confirmó y reembolsó los cargos de API que le habían facturado.

**Tu responsabilidad.** Mistral puede cambiar sus términos en cualquier momento. Antes de usar este gateway, y de nuevo cada vez que Mistral anuncie un cambio, lee los términos vigentes tú mismo y deja de usar el gateway si ya no lo permiten. Mistral decide cómo hacer cumplir sus propios términos.

## Aviso

Este software se proporciona «tal cual» bajo la [PolyForm Noncommercial License 1.0.0](LICENSE), sin garantía de ningún tipo. El autor no acepta responsabilidad por ningún daño o pérdida derivado de su uso, incluida la suspensión, restricción o terminación de tu cuenta de Mistral, cuotas de suscripción perdidas o datos perdidos.

## Licencia

[PolyForm Noncommercial 1.0.0](LICENSE): gratis para uso personal, aficionado, de investigación y otro uso no comercial. No se permite el uso comercial.

Es no comercial porque una suscripción de Mistral Vibe es un plan de consumidor: los términos de consumidor de Mistral solo cubren «tu uso personal como consumidor», y el uso empresarial cae bajo sus [Términos de servicio comerciales](https://legal.mistral.ai/terms/commercial-terms-of-service) separados.
