# Conector de Claude + App Inventor

Un único servidor Python que ofrece:

- **Servidor MCP remoto** → lo añades a Claude como conector personalizado.
- **API REST** (`/api/datos`) → la usa tu app de MIT App Inventor con el componente `Web`.

Los dos comparten los mismos datos (pares clave/valor). Lo que guarda Claude lo lee la app, y al revés.

## Herramientas que verá Claude

| Herramienta | Qué hace |
|---|---|
| `guardar_dato(clave, valor)` | Guarda o actualiza un dato |
| `leer_dato(clave)` | Lee un dato |
| `listar_datos()` | Devuelve todos los datos |
| `borrar_dato(clave)` | Borra un dato |

## 1. Probar en tu ordenador

```bash
pip install -r requirements.txt
export API_KEY="pon-aqui-una-clave-larga"      # Windows (PowerShell): $env:API_KEY="..."
python server.py
```

Comprueba la API REST:

```bash
curl -H "x-api-key: pon-aqui-una-clave-larga" http://localhost:8000/api/datos
```

Para probar las herramientas MCP antes de conectar Claude:

```bash
npx @modelcontextprotocol/inspector
```

Elige transporte *Streamable HTTP* y la URL `http://localhost:8000/mcp`.

## 2. Publicarlo en internet

Claude se conecta desde la nube de Anthropic, así que `localhost` no sirve: el servidor necesita una URL pública con HTTPS. Por ejemplo, en Render (hay plan gratuito):

1. Sube esta carpeta a un repositorio de GitHub.
2. En Render: **New → Web Service** y elige el repositorio.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python server.py`
5. Variables de entorno:
   - `API_KEY` = una clave larga y aleatoria (para la API REST).
   - `MCP_PATH` = una ruta larga y aleatoria, por ejemplo `/mcp-7f3a9c1e5b2d4a60` (ver nota de seguridad).

Render te dará una URL tipo `https://tu-servicio.onrender.com`.

> **Datos en el plan gratuito:** el disco es temporal y los datos se pierden al reiniciar o redesplegar. Para guardarlos de forma permanente, añade un disco persistente y pon `DB_PATH` apuntando a él, o cambia SQLite por una base de datos externa. Además, el servicio gratuito se "duerme" tras un rato sin uso, así que la primera petición puede tardar.

## 3. Añadirlo a Claude

1. En claude.ai: **Ajustes → Conectores → Añadir conector personalizado**.
2. Nombre: `App Inventor`.
3. URL: `https://tu-servicio.onrender.com/mcp-7f3a9c1e5b2d4a60` (tu `MCP_PATH`).
4. En un chat, pulsa **+ → Conectores** y activa el conector.
5. Pruébalo: *«Guarda el dato temperatura con valor 23»* y luego *«Lista todos los datos»*.

En planes Team y Enterprise, un propietario debe añadirlo primero desde los ajustes de la organización.

## 4. Usarlo desde App Inventor

Componentes: un `Web` (llámalo `Web1`), dos botones y una etiqueta.

**Al iniciar la pantalla** (`Screen1.Initialize`):

- Pon `Web1.Url` = `https://tu-servicio.onrender.com/api/datos`
- Pon `Web1.RequestHeaders` = lista de listas:
  - `("x-api-key", "pon-aqui-una-clave-larga")`
  - `("Content-Type", "application/json")`

**Leer todos los datos** (`BotonLeer.Click`):

- Llama a `Web1.Get`.

**Guardar un dato** (`BotonGuardar.Click`):

- Llama a `Web1.PostText` con este texto (bloque `unir`):
  `{"clave":"temperatura","valor":"` + (el valor) + `"}`

**Recibir la respuesta** (`Web1.GotText`, parámetros `url`, `responseCode`, `responseType`, `responseContent`):

- Si `responseCode` = 200, usa `Web1.JsonTextDecodeWithDictionaries(responseContent)` para convertir el JSON en un diccionario.
- Muestra el resultado en la etiqueta con `Etiqueta.Text` = el diccionario o el valor que quieras.

Para leer una sola clave, cambia `Web1.Url` a `.../api/datos/temperatura` y llama a `Web1.Get`. Para borrarla, usa `Web1.Delete`.

## Seguridad

- La **API REST** exige la cabecera `x-api-key`. Sin `API_KEY` configurada, el servidor la rechaza.
- La clave de `RequestHeaders` queda dentro de la app, así que cualquiera que consiga el archivo `.apk` podría extraerla. Úsalo para proyectos de clase o personales, no para datos sensibles.
- El **endpoint MCP** de este ejemplo no tiene autenticación: la única protección es que la ruta sea larga y secreta. No guardes datos privados. Para uso serio, añade OAuth al servidor MCP.
- Los datos que guarda Claude se escriben tal cual y los puede leer la app; no almacenes contraseñas ni datos personales.
