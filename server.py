"""
Conector personalizado para Claude + API REST para MIT App Inventor.

Un solo servidor con dos entradas a los MISMOS datos:
  - /mcp...      -> servidor MCP remoto (Claude lo añade como conector)
  - /api/datos   -> API REST sencilla (la app de App Inventor la usa con el componente Web)

Los datos son pares clave/valor guardados en SQLite.
"""
import os
import sqlite3
import time

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

DB_PATH = os.environ.get("DB_PATH", "datos.db")
API_KEY = os.environ.get("API_KEY", "")          # clave para la API REST (obligatoria)
MCP_PATH = os.environ.get("MCP_PATH", "/mcp")    # usa una ruta larga y aleatoria en producción
PORT = int(os.environ.get("PORT", "8000"))

MAX_CLAVE = 100
MAX_VALOR = 5000


# ---------- Capa de datos ----------
def _sql(consulta, args=()):
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS datos ("
            "clave TEXT PRIMARY KEY, valor TEXT NOT NULL, actualizado REAL NOT NULL)"
        )
        cur = con.execute(consulta, args)
        filas = cur.fetchall()
        con.commit()
        return filas, cur.rowcount
    finally:
        con.close()


def guardar(clave: str, valor: str) -> None:
    _sql(
        "INSERT INTO datos (clave, valor, actualizado) VALUES (?, ?, ?) "
        "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, actualizado=excluded.actualizado",
        (clave, valor, time.time()),
    )


def leer(clave: str):
    filas, _ = _sql("SELECT valor FROM datos WHERE clave = ?", (clave,))
    return filas[0][0] if filas else None


def listar() -> dict:
    filas, _ = _sql("SELECT clave, valor FROM datos ORDER BY clave")
    return {c: v for c, v in filas}


def borrar(clave: str) -> bool:
    _, n = _sql("DELETE FROM datos WHERE clave = ?", (clave,))
    return n > 0


def validar(clave, valor=None):
    """Devuelve un mensaje de error o None si todo está bien."""
    if not isinstance(clave, str) or not clave.strip():
        return "La clave no puede estar vacía."
    if len(clave) > MAX_CLAVE:
        return f"La clave supera {MAX_CLAVE} caracteres."
    if valor is not None:
        if not isinstance(valor, str):
            return "El valor debe ser texto."
        if len(valor) > MAX_VALOR:
            return f"El valor supera {MAX_VALOR} caracteres."
    return None


# ---------- Servidor MCP (lo que ve Claude) ----------
mcp = FastMCP(
    "App Inventor",
    host="0.0.0.0",
    port=PORT,
    streamable_http_path=MCP_PATH,
    stateless_http=True,
)


@mcp.tool()
def guardar_dato(clave: str, valor: str) -> str:
    """Guarda o actualiza un dato (clave y valor en texto) que también puede leer la app de App Inventor."""
    error = validar(clave, valor)
    if error:
        return f"Error: {error}"
    guardar(clave.strip(), valor)
    return f"Guardado: {clave.strip()} = {valor}"


@mcp.tool()
def leer_dato(clave: str) -> str:
    """Lee el valor de un dato por su clave."""
    valor = leer(clave.strip())
    return valor if valor is not None else f"No existe ningún dato con la clave '{clave}'."


@mcp.tool()
def listar_datos() -> dict:
    """Devuelve todos los datos guardados como pares clave/valor."""
    return listar()


@mcp.tool()
def borrar_dato(clave: str) -> str:
    """Borra un dato por su clave."""
    return "Borrado." if borrar(clave.strip()) else f"No existe ningún dato con la clave '{clave}'."


# ---------- API REST (lo que usa App Inventor) ----------
def _no_autorizado(request: Request):
    if not API_KEY:
        return JSONResponse({"error": "El servidor no tiene API_KEY configurada."}, status_code=503)
    if request.headers.get("x-api-key") != API_KEY:
        return JSONResponse({"error": "Clave de API incorrecta."}, status_code=401)
    return None


@mcp.custom_route("/", methods=["GET"])
async def inicio(request: Request):
    return JSONResponse({"estado": "ok"})


@mcp.custom_route("/api/datos", methods=["GET", "POST"])
async def api_datos(request: Request):
    rechazo = _no_autorizado(request)
    if rechazo:
        return rechazo
    if request.method == "GET":
        return JSONResponse(listar())
    try:
        cuerpo = await request.json()
    except Exception:
        return JSONResponse({"error": "El cuerpo debe ser JSON: {\"clave\": \"...\", \"valor\": \"...\"}"}, status_code=400)
    clave, valor = cuerpo.get("clave"), cuerpo.get("valor")
    error = validar(clave, valor)
    if error:
        return JSONResponse({"error": error}, status_code=400)
    guardar(clave.strip(), valor)
    return JSONResponse({"ok": True, "clave": clave.strip(), "valor": valor})


@mcp.custom_route("/api/datos/{clave}", methods=["GET", "DELETE"])
async def api_dato(request: Request):
    rechazo = _no_autorizado(request)
    if rechazo:
        return rechazo
    clave = request.path_params["clave"]
    if request.method == "DELETE":
        return JSONResponse({"borrado": borrar(clave)})
    valor = leer(clave)
    if valor is None:
        return JSONResponse({"error": "No existe esa clave."}, status_code=404)
    return JSONResponse({"clave": clave, "valor": valor})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
