"""Uso: python -m cartolas.comparar <carpeta del export> <carpeta de salida> [opciones]

Compara fila por fila los archivos que escribió la skill con un export de BICE
del mismo día y deja un reporte con lo que no coincide.

Solo se comparan los clientes que están en la salida (el export trae todos los
clientes del asesor) y, en los movimientos, solo los de las fechas de proceso
del export (el export es diario; la cartola trae el mes completo). La carpeta
del export puede traer varios días: se juntan, y de los movimientos se comparan
solo los días dentro del período de la salida.
"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .formato import ARCHIVOS, Archivo

# Columnas que identifican el registro: entre las filas del export con la misma
# clave se elige la que coincide en más columnas.
_CLAVES = {
    "SALDOS_CAJA": ("RutCliente", "Cuenta", "MonedaValoracionPatrimonio"),
    "SALDOS_FFMM": ("RutCliente", "Cuenta", "Instrumento"),
    "CUSTODIA_ACCIONES": ("RutCliente", "Cuenta", "Instrumento"),
    "MOVIMIENTOS_DE_CAJA": ("RutCliente", "Cuenta", "nombreTipoMovimiento", "Moneda"),
    "MOVIMIENTOS_BOLSA": ("RutCliente", "Cuenta", "Instrumento", "NombreTipoMovimiento"),
    "MOVIMIENTOS_FFMM": ("RutCliente", "Cuenta", "Instrumento", "NombreTipoMovimiento"),
    "MOVIMIENTOS_PERSHING": ("CuentaPershing", "Instrumento", "NombreTipoMovimiento"),
}
_MOVIMIENTOS = {t for t in ARCHIVOS if t.startswith("MOVIMIENTOS_")}
# Diferencia que se acepta en columnas numéricas: la del último decimal que
# escribe el export, o una parte en un millón (tipos de cambio con 14 decimales).
_RELATIVA = Decimal("1e-6")
_EJEMPLOS = 5


@dataclass
class Comparacion:
    tipo: str
    filas_export: int = 0
    filas_salida: int = 0
    pares: int = 0
    iguales: Counter = field(default_factory=Counter)
    # columna -> ejemplos "clave: salida ≠ export"
    diferencias: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    distintas: Counter = field(default_factory=Counter)
    solo_export: list[str] = field(default_factory=list)
    solo_salida: list[str] = field(default_factory=list)

    @property
    def coincide(self) -> bool:
        return not (self.distintas or self.solo_export or self.solo_salida)


def leer(archivo: Archivo, ruta: Path) -> list[dict[str, str]]:
    with open(ruta, encoding=archivo.codificacion, newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _numero(texto: str) -> Decimal | None:
    try:
        return Decimal(texto.replace(",", ".")) if texto else None
    except InvalidOperation:
        return None


def iguales(archivo: Archivo, columna: str, a: str, b: str) -> bool:
    if a == b:
        return True
    decimales = next((c.decimales for c in archivo.columnas if c.nombre == columna), None)
    if decimales is None:
        # Texto: se ignoran espacios repetidos y mayúsculas.
        return re.sub(r"\s+", " ", a).strip().upper() == re.sub(r"\s+", " ", b).strip().upper()
    x, y = _numero(a), _numero(b)
    if x is None or y is None:
        return False
    return abs(x - y) <= max(Decimal(1).scaleb(-decimales), abs(y) * _RELATIVA)


def comparar(
    archivo: Archivo,
    export: list[dict],
    salida: list[dict],
    clientes: set[str],
    ignorar: set[str] = frozenset(),
) -> Comparacion:
    """Compara las filas de un tipo de archivo; del export, solo las de
    ``clientes`` (los RUT de toda la salida)."""
    r = Comparacion(archivo.tipo)
    if "RutCliente" in archivo.encabezados:
        export = [f for f in export if f["RutCliente"] in clientes]
    r.filas_export, r.filas_salida = len(export), len(salida)
    claves = _CLAVES[archivo.tipo]
    columnas = [c for c in archivo.encabezados if c not in ignorar]
    grupos: dict[tuple, tuple[list[dict], list[dict]]] = defaultdict(lambda: ([], []))
    for f in export:
        grupos[_clave(f, claves)][0].append(f)
    for f in salida:
        grupos[_clave(f, claves)][1].append(f)

    libres: dict[tuple, list[dict]] = {}
    for clave, (del_export, de_salida) in grupos.items():
        # Entre las filas con la misma clave se emparejan primero las que más
        # columnas comparten, para que una fila sin par no le quite el suyo a otra.
        candidatos = sorted(
            (
                (-sum(iguales(archivo, c, f[c], e[c]) for c in columnas), i, j)
                for i, f in enumerate(de_salida)
                for j, e in enumerate(del_export)
            ),
        )
        usadas_s, usadas_e = set(), set()
        for _, i, j in candidatos:
            if i in usadas_s or j in usadas_e:
                continue
            usadas_s.add(i)
            usadas_e.add(j)
            f, par = de_salida[i], del_export[j]
            r.pares += 1
            for c in columnas:
                if iguales(archivo, c, f[c], par[c]):
                    r.iguales[c] += 1
                else:
                    r.distintas[c] += 1
                    if len(r.diferencias[c]) < _EJEMPLOS:
                        r.diferencias[c].append(f"{_mostrar(f, claves)}: {f[c]!r} ≠ {par[c]!r}")
        r.solo_salida += [_mostrar(f, claves) for i, f in enumerate(de_salida) if i not in usadas_s]
        libres[clave] = [e for j, e in enumerate(del_export) if j not in usadas_e]
    r.solo_export = [_mostrar(e, claves) for resto in libres.values() for e in resto]
    return r


def _clave(fila: dict, claves: tuple[str, ...]) -> tuple:
    return tuple(re.sub(r"\s+", " ", fila[c]).strip().upper() for c in claves)


def _mostrar(fila: dict, claves: tuple[str, ...]) -> str:
    return " / ".join(fila[c] for c in claves)


def _archivos(carpeta: Path, codigo: str | None) -> dict[str, tuple[list[Path], str]]:
    """(archivos de todos los días, código del juego) de cada tipo en la
    carpeta; con ``codigo``, solo los de ese juego."""
    encontrados: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for ruta in sorted(carpeta.glob("*_V2.csv")):
        for tipo in ARCHIVOS:
            m = re.fullmatch(rf"{tipo}_(.+)_\d{{8}}_V2\.csv", ruta.name)
            if m and (codigo is None or m.group(1) == codigo):
                encontrados[tipo][m.group(1)].append(ruta)
    repetidos = {t: sorted(c) for t, c in encontrados.items() if len(c) > 1}
    if repetidos:
        juegos = ", ".join(sorted({c for cs in repetidos.values() for c in cs}))
        raise SystemExit(f"Hay más de un juego de archivos en {carpeta} ({juegos}): indica --codigo")
    return {t: next(iter(c.items()))[::-1] for t, c in encontrados.items()}


def reporte(comparaciones: list[Comparacion], export: Path, salida: Path) -> str:
    lineas = [
        "# Comparación con el export",
        "",
        f"Export: `{export}`. Salida: `{salida}`. Solo los clientes de la salida y, en movimientos, "
        "solo las fechas de proceso del export.",
        "",
        "| Archivo | Filas export | Filas salida | Pares | Solo export | Solo salida | Columnas con diferencias |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for c in comparaciones:
        distintas = ", ".join(f"{col} ({n})" for col, n in c.distintas.most_common()) or "ninguna"
        lineas.append(
            f"| {c.tipo} | {c.filas_export} | {c.filas_salida} | {c.pares} | {len(c.solo_export)} | "
            f"{len(c.solo_salida)} | {distintas} |"
        )
    for c in comparaciones:
        if c.coincide:
            continue
        lineas += ["", f"## {c.tipo}", ""]
        for col, n in c.distintas.most_common():
            lineas.append(f"- **{col}**: {n} de {c.pares} pares distintos (salida ≠ export)")
            lineas += [f"  - {e}" for e in c.diferencias[col]]
        if c.solo_export:
            lineas.append(f"- **Solo en el export** ({len(c.solo_export)}):")
            lineas += [f"  - {e}" for e in c.solo_export]
        if c.solo_salida:
            lineas.append(f"- **Solo en la salida** ({len(c.solo_salida)}):")
            lineas += [f"  - {e}" for e in c.solo_salida]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cartolas.comparar", description=__doc__.splitlines()[2])
    parser.add_argument("export", help="carpeta con los CSV del export de BICE")
    parser.add_argument("salida", help="carpeta con los CSV que escribió la skill")
    parser.add_argument(
        "--codigo", help="juego de archivos de la salida a comparar (por defecto, el del export)"
    )
    parser.add_argument("--ignorar", default="", help="columnas que no se comparan, separadas por coma")
    parser.add_argument(
        "--fecha-saldos",
        help="cierre de los saldos de la salida que se comparan, AAAA-MM-DD, si no es la fecha del export "
        "(entonces no se compara FechaProceso en los saldos)",
    )
    parser.add_argument("--reporte", help="dónde escribir el reporte (por defecto, en la carpeta de salida)")
    args = parser.parse_args(argv)

    export, salida = Path(args.export), Path(args.salida)
    del_export = _archivos(export, None)
    if not del_export:
        parser.error(f"no hay archivos del export en {export}")
    codigo = args.codigo or next(iter(del_export.values()))[1]
    de_salida = _archivos(salida, codigo)
    ignorar = {c.strip() for c in args.ignorar.split(",") if c.strip()}

    def todos(archivo: Archivo, rutas: list[Path]) -> list[dict[str, str]]:
        return [f for r in rutas for f in leer(archivo, r)]

    filas = {
        tipo: (todos(archivo, del_export[tipo][0]), todos(archivo, de_salida[tipo][0]))
        for tipo, archivo in ARCHIVOS.items()
        if tipo in del_export and tipo in de_salida
    }
    # El export es diario: los movimientos se comparan en los días del export
    # que caen dentro del período de la salida, y los saldos, en esos días o en
    # el cierre que se indique.
    periodo = [f["FechaProceso"] for _, s in filas.values() for f in s]
    desde, hasta = (min(periodo), max(periodo)) if periodo else ("", "")
    fechas = {f["FechaProceso"] for e, _ in filas.values() for f in e}
    for tipo, (e, s) in filas.items():
        if tipo in _MOVIMIENTOS:
            e = [f for f in e if desde <= f["FechaProceso"] <= hasta]
            filas[tipo] = (e, [f for f in s if f["FechaProceso"] in fechas])
        elif not args.fecha_saldos:
            filas[tipo] = (e, [f for f in s if f["FechaProceso"] in fechas])
        else:
            filas[tipo] = (e, [f for f in s if f["FechaProceso"] == args.fecha_saldos])
    clientes = {f["RutCliente"] for _, s in filas.values() for f in s if f.get("RutCliente")}
    if not clientes:
        print(
            f"La salida no tiene filas con fecha {', '.join(sorted(fechas))}, la del export: "
            "indica con --fecha-saldos el cierre de las cartolas."
        )
        return 1
    comparaciones = []
    for tipo, (e, s) in filas.items():
        sin_fecha = {"FechaProceso"} if args.fecha_saldos and tipo not in _MOVIMIENTOS else set()
        comparaciones.append(comparar(ARCHIVOS[tipo], e, s, clientes, ignorar | sin_fecha))
    destino = Path(args.reporte) if args.reporte else salida / f"COMPARACION_{codigo}.md"
    destino.write_text(reporte(comparaciones, export, salida), encoding="utf-8")
    for c in comparaciones:
        estado = (
            "coincide"
            if c.coincide
            else (
                f"{sum(c.distintas.values())} diferencias, {len(c.solo_export)} solo en el export, "
                f"{len(c.solo_salida)} solo en la salida"
            )
        )
        print(f"{c.tipo}: {c.pares} pares de {c.filas_export} filas del export; {estado}")
    print(f"Reporte: {destino}")
    return 0 if all(c.coincide for c in comparaciones) else 1


if __name__ == "__main__":
    sys.exit(main())
