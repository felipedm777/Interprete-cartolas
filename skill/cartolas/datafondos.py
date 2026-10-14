"""Consulta a DataFondos por su API, para mantener al día la tabla de eventos de capital.

DataFondos (el repositorio DataFondosv2) publica los repartos de los fondos en
su API de solo lectura `/api/v1`, la misma que usa su MCP:

- `GET /dividendos/resumen` dice qué fondos sigue y hasta cuándo tiene sus
  repartos (la herramienta `resumen_dividendos`). Va a la cobertura de la skill,
  `datos/datafondos_cobertura.csv`.
- `GET /fondos/{rut}/dividendos?nemo=` trae los repartos de un fondo (la
  herramienta `dividendos`). Van a la tabla, `datos/eventos_capital.csv`.

La skill la consulta sola cuando encuentra la URL y una API key en las
variables de entorno DATAFONDOS_API_URL y DATAFONDOS_API_KEY, las mismas que
usa el MCP de DataFondosv2 (DATAFONDOS_TIMEOUT, opcional, son los segundos por
consulta). Basta una key con el scope `valores:read`. Sin ellas no consulta
nada y el reporte lista los fondos por consultar.

A DataFondos solo se le envían el RUT y el nemotécnico de fondos, nunca datos de
clientes. La key se lee del entorno y no se escribe en ningún archivo.

    python -m cartolas.datafondos [--fondo RUT NEMOTECNICO]...
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import eventos_capital as ec

VARIABLE_URL = "DATAFONDOS_API_URL"
VARIABLE_KEY = "DATAFONDOS_API_KEY"
VARIABLE_TIMEOUT = "DATAFONDOS_TIMEOUT"

# DataFondos identifica cada fondo por su número en la CMF (p. ej. 9911).
_RUT = re.compile(r"^\d{1,12}$")


class DataFondosError(Exception):
    """Una consulta a DataFondos que no se pudo hacer, con el motivo legible."""


def base_url(url: str) -> str:
    """La base de la API lista para agregarle rutas: acepta la URL con o sin
    `/api/v1` y con o sin barra al final."""
    base = (url or "").strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise DataFondosError(f"{VARIABLE_URL} tiene que ser una URL http(s): {base!r}")
    return base if base.endswith("/api/v1") else f"{base}/api/v1"


def _mensaje(codigo: int, cuerpo: str) -> str:
    try:
        detalle = json.loads(cuerpo).get("error") or ""
    except (ValueError, AttributeError):
        detalle = ""
    motivo = {
        401: f"DataFondos no reconoce la API key: revisar {VARIABLE_KEY}",
        403: "la API key no tiene permiso para esa consulta: pedir una con el scope valores:read",
        404: "DataFondos no tiene ese fondo",
        429: "se pasó el límite de consultas de DataFondos: volver a correr en unos minutos",
    }.get(codigo, f"DataFondos respondió {codigo}")
    return f"{motivo} ({detalle})" if detalle else motivo


@dataclass
class Cliente:
    """Lector de la API de DataFondos. Solo hace GET."""

    url: str
    clave: str = field(repr=False)
    timeout: float = 20.0

    def __post_init__(self):
        self.url = base_url(self.url)
        if not self.clave.strip():
            raise DataFondosError(f"falta la API key en {VARIABLE_KEY}")

    def _get(self, ruta: str, parametros: dict[str, str] | None = None) -> dict:
        consulta = urllib.parse.urlencode({k: v for k, v in (parametros or {}).items() if v})
        pedido = urllib.request.Request(
            f"{self.url}{ruta}" + (f"?{consulta}" if consulta else ""),
            headers={"X-API-Key": self.clave.strip(), "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as r:
                cuerpo = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise DataFondosError(_mensaje(e.code, e.read().decode("utf-8", "replace"))) from None
        except (urllib.error.URLError, OSError) as e:
            raise DataFondosError(f"no se pudo conectar con DataFondos: {e}") from None
        try:
            datos = json.loads(cuerpo)
        except ValueError:
            raise DataFondosError(
                f"DataFondos no respondió JSON: revisar que {VARIABLE_URL} sea la URL de la API"
            ) from None
        if not isinstance(datos, dict) or datos.get("ok") is False:
            detalle = datos.get("error") if isinstance(datos, dict) else ""
            raise DataFondosError(f"DataFondos respondió con un error: {detalle or cuerpo[:200]}")
        return datos

    def resumen(self) -> dict:
        """Qué fondos sigue DataFondos (`resumen_dividendos`)."""
        return self._get("/dividendos/resumen")

    def dividendos(self, rut: str, nemotecnico: str) -> dict:
        """Repartos de un fondo (`dividendos`)."""
        rut = rut.strip()
        if not _RUT.match(rut):
            raise DataFondosError(f"RUT de fondo inválido: {rut!r}")
        return self._get(f"/fondos/{urllib.parse.quote(rut)}/dividendos", {"nemo": nemotecnico.strip()})


def desde_entorno(entorno: dict[str, str] | None = None) -> Cliente | None:
    """El cliente configurado en las variables de entorno, o None si faltan."""
    entorno = os.environ if entorno is None else entorno
    url, clave = entorno.get(VARIABLE_URL, ""), entorno.get(VARIABLE_KEY, "")
    if not url.strip() or not clave.strip():
        return None
    try:
        timeout = float(entorno.get(VARIABLE_TIMEOUT) or 20)
    except ValueError:
        raise DataFondosError(f"{VARIABLE_TIMEOUT} tiene que ser un número de segundos") from None
    return Cliente(url, clave, timeout)


def _guardar(datos: dict, carpeta: Path | None, nombre: str) -> None:
    """Deja la respuesta tal cual, para poder rastrear de dónde salió la tabla."""
    if carpeta is None:
        return
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', nombre)}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def actualizar_cobertura(
    cliente: Cliente, ruta: Path = ec.RUTA_COBERTURA, guardar: Path | None = None
) -> ec.Cobertura:
    """Pide `resumen_dividendos` y agrega lo que devuelve a la cobertura."""
    datos = cliente.resumen()
    _guardar(datos, guardar, "resumen")
    seguidos = ec._cobertura_json(datos)
    if not seguidos:
        raise DataFondosError("el resumen de DataFondos no trae fondos")
    return ec.agregar_cobertura(seguidos, ruta)


@dataclass
class Consulta:
    """Lo que dejó una ronda de consultas de fondos."""

    # Fondos consultados (nemotécnico como lo escribe DataFondos).
    consultados: list[str] = field(default_factory=list)
    # Eventos que devolvieron y cuántos eran nuevos para la tabla.
    leidos: int = 0
    agregados: int = 0
    # Fondos que no se pudieron consultar, con el motivo.
    fallas: list[str] = field(default_factory=list)


def fondos_por_consultar(
    pendientes: set[tuple[str, str]], cobertura: ec.Cobertura
) -> tuple[list[ec.Seguido], list[str]]:
    """Los fondos pendientes que sigue DataFondos, con el RUT y el nemotécnico
    con que hay que pedirlos, y los que no están en la cobertura (sin RUT no se
    pueden pedir)."""
    seguidos: dict[str, ec.Seguido] = {}
    sin_rut = set()
    for nemo, _ in pendientes:
        seguido = cobertura.buscar(nemo)
        if seguido and seguido.rut_fondo:
            seguidos[seguido.nemotecnico] = seguido
        else:
            sin_rut.add(nemo)
    return [seguidos[n] for n in sorted(seguidos)], sorted(sin_rut)


def consultar(
    cliente: Cliente,
    fondos: list[ec.Seguido],
    ruta: Path = ec.RUTA_TABLA,
    desde: date | None = None,
    guardar: Path | None = None,
) -> Consulta:
    """Pide `dividendos` de cada fondo y agrega los eventos a la tabla. Un fondo
    que falla no detiene los demás."""
    consulta = Consulta()
    nuevos: list[ec.Evento] = []
    for f in fondos:
        try:
            datos = cliente.dividendos(f.rut_fondo, f.nemotecnico)
            eventos = ec._desde_json(datos)
        except (DataFondosError, ValueError) as e:
            consulta.fallas.append(f"{f.nemotecnico}: {e}")
            continue
        _guardar(datos, guardar, f.nemotecnico)
        consulta.consultados.append(f.nemotecnico)
        nuevos += eventos
    consulta.leidos = len(nuevos)
    if consulta.consultados:
        _, consulta.agregados = ec.agregar_eventos(nuevos, ruta, desde)
    return consulta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cartolas.datafondos",
        description="Actualiza desde la API de DataFondos la cobertura de la skill (qué fondos sigue "
        "y hasta cuándo) y, con --fondo, agrega a la tabla los repartos de esos fondos. Necesita "
        f"{VARIABLE_URL} y {VARIABLE_KEY}.",
    )
    parser.add_argument(
        "--fondo",
        nargs=2,
        action="append",
        default=[],
        metavar=("RUT", "NEMOTECNICO"),
        help="fondo cuyos repartos agregar a la tabla (se puede repetir)",
    )
    parser.add_argument("--tabla", default=str(ec.RUTA_TABLA), help="tabla a actualizar")
    parser.add_argument("--cobertura", default=str(ec.RUTA_COBERTURA), help="cobertura a actualizar")
    parser.add_argument(
        "--desde",
        help="no agregar los eventos pagados antes de esta fecha, AAAA-MM-DD (por defecto, el 1 de "
        "enero del año anterior)",
    )
    parser.add_argument("--guardar", help="carpeta donde dejar las respuestas JSON de DataFondos")
    args = parser.parse_args(argv)

    try:
        cliente = desde_entorno()
    except DataFondosError as e:
        parser.error(str(e))
    if cliente is None:
        parser.error(f"faltan {VARIABLE_URL} y {VARIABLE_KEY} en las variables de entorno")
    guardar = Path(args.guardar) if args.guardar else None
    try:
        cobertura = actualizar_cobertura(cliente, Path(args.cobertura), guardar)
    except DataFondosError as e:
        print(f"No se pudo actualizar la cobertura: {e}", file=sys.stderr)
        return 1
    print(f"Cobertura: {len(cobertura)} fondos en {args.cobertura}, actualizada al {cobertura.actualizada()}")
    if not args.fondo:
        return 0

    hoy = date.today()
    desde = date.fromisoformat(args.desde) if args.desde else date(hoy.year - 1, 1, 1)
    fondos = [ec.Seguido(nemotecnico=nemo, rut_fondo=rut) for rut, nemo in args.fondo]
    consulta = consultar(cliente, fondos, Path(args.tabla), desde, guardar)
    print(
        f"{len(consulta.consultados)} fondos consultados: {consulta.leidos} eventos, "
        f"{consulta.agregados} nuevos en {args.tabla}."
    )
    for falla in consulta.fallas:
        print(f"  No se pudo consultar {falla}", file=sys.stderr)
    return 1 if consulta.fallas else 0


if __name__ == "__main__":
    sys.exit(main())
