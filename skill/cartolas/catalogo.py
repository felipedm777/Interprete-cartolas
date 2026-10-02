"""Tabla maestra de instrumentos y reglas por número de cuenta.

Las cartolas traen el nombre del instrumento, pero no su nemotécnico, emisor
ni el producto con que lo clasifica el export. La tabla `datos/instrumentos.csv`
tiene esos datos por instrumento y se arma desde un export de BICE con:

    python -m cartolas.catalogo "<carpeta del export>"

Solo guarda datos de los instrumentos (nombre, nemotécnico, moneda, emisor,
producto y precio de cierre del día del export), nunca datos de clientes.
"""

import csv
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .numeros import escribir_numero, leer_monto

RUTA_TABLA = Path(__file__).parent / "datos" / "instrumentos.csv"
# Instrumentos que la cartola nombra distinto que el export, identificados
# comparando cantidad y precio promedio de compra del mismo cliente y cuenta.
RUTA_ALIAS = Path(__file__).parent / "datos" / "alias.csv"

_COLUMNAS = (
    "Instrumento",
    "NemotecnicoInstrumento",
    "MonedaInstrumento",
    "Emisor",
    "Producto",
    "Archivo",
    "PrecioReferencia",
    "FechaReferencia",
)


@dataclass(frozen=True)
class Instrumento:
    nombre: str
    nemotecnico: str
    moneda: str
    emisor: str
    producto: str
    # Archivo de saldos al que va: SALDOS_FFMM o CUSTODIA_ACCIONES.
    archivo: str
    # Precio de cierre en la moneda del instrumento el día del export; sirve para
    # elegir entre series con el mismo nombre.
    precio_referencia: Decimal | None = None
    fecha_referencia: str = ""


def _clave(nombre: str) -> str:
    return re.sub(r"\s+", " ", nombre).strip().upper()


class Catalogo:
    def __init__(self, instrumentos: list[Instrumento], alias: dict[tuple[str, str], str] | None = None):
        self.instrumentos = instrumentos
        self._exacto: dict[str, list[Instrumento]] = defaultdict(list)
        self._normalizado: dict[str, list[Instrumento]] = defaultdict(list)
        self._nemotecnico: dict[tuple[str, str], Instrumento] = {}
        for i in instrumentos:
            self._exacto[i.nombre].append(i)
            self._normalizado[_clave(i.nombre)].append(i)
            self._nemotecnico.setdefault((i.nemotecnico, i.moneda), i)
        # (nombre en la cartola normalizado, moneda) -> nemotécnico
        self._alias = {(_clave(n), m): nemo for (n, m), nemo in (alias or {}).items()}

    @classmethod
    def cargar(cls, ruta: Path = RUTA_TABLA, ruta_alias: Path = RUTA_ALIAS) -> "Catalogo":
        if not ruta.exists():
            return cls([])
        with open(ruta, encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f, delimiter=";"))
        alias = {}
        if ruta_alias.exists():
            with open(ruta_alias, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f, delimiter=";"):
                    alias[(r["NombreCartola"], r["MonedaInstrumento"])] = r["NemotecnicoInstrumento"]
        return cls(
            [
                Instrumento(
                    nombre=r["Instrumento"],
                    nemotecnico=r["NemotecnicoInstrumento"],
                    moneda=r["MonedaInstrumento"],
                    emisor=r["Emisor"],
                    producto=r["Producto"],
                    archivo=r["Archivo"],
                    precio_referencia=leer_monto(r["PrecioReferencia"])
                    if r["PrecioReferencia"]
                    else None,
                    fecha_referencia=r["FechaReferencia"],
                )
                for r in filas
            ],
            alias,
        )

    def buscar(
        self, nombre: str, moneda: str | None = None, precio: Decimal | None = None
    ) -> Instrumento | None:
        """Instrumento con ese nombre; ignora mayúsculas y espacios repetidos si no
        hay coincidencia exacta, y después busca en los alias.

        Si hay varias series con el mismo nombre se prefiere la de la misma moneda
        y, entre ellas, la de precio de referencia más cercano a ``precio``.
        """
        candidatos = self._exacto.get(nombre) or self._normalizado.get(_clave(nombre), [])
        if not candidatos and moneda:
            nemo = self._alias.get((_clave(nombre), moneda))
            if nemo and (nemo, moneda) in self._nemotecnico:
                return self._nemotecnico[(nemo, moneda)]
        if moneda:
            candidatos = [c for c in candidatos if c.moneda == moneda] or candidatos
        if len(candidatos) > 1 and precio:
            con_precio = [c for c in candidatos if c.precio_referencia]
            if con_precio:
                return min(
                    con_precio,
                    key=lambda c: abs(math.log(float(precio) / float(c.precio_referencia))),
                )
        return candidatos[0] if candidatos else None


# --- Cuenta, producto base y APV ---------------------------------------------


@dataclass(frozen=True)
class TipoCuenta:
    producto_base: str
    tipo_apv: str
    regimen: str


# Tal como aparecen en el export de ejemplo (docs/formato-salida.md).
_CUENTAS_APV = {
    "80": TipoCuenta("APV FFMM", "DAPV", "BONIFICACIÓN"),
    "81": TipoCuenta("APV FFMM", "CV", "BONIFICACIÓN"),
    "82": TipoCuenta("APV FFMM", "DC", "BONIFICACIÓN"),
    "83": TipoCuenta("APV FFMM", "DAPV", "APORTE"),
    "84": TipoCuenta("APV FFMM", "CV", "APORTE"),
    "85": TipoCuenta("APV FFMM", "DAPV", "APORTE"),
    "90": TipoCuenta("APV PRIME", "DAPV", "BONIFICACIÓN"),
    "91": TipoCuenta("APV PRIME", "CV", "BONIFICACIÓN"),
    "92": TipoCuenta("APV PRIME", "DC", "BONIFICACIÓN"),
    "93": TipoCuenta("APV PRIME", "DAPV", "APORTE"),
    "94": TipoCuenta("APV PRIME", "CV", "APORTE"),
    "95": TipoCuenta("APV PRIME", "DAPVC", "APORTE"),
    "96": TipoCuenta("APV PRIME", "DAPVC", "APORTE"),
}


def tipo_cuenta(numero: str) -> TipoCuenta | None:
    """Producto base, tipo de APV y régimen según el número de cuenta BICE.

    None si el número no es de los que usa el export (p. ej. una cuenta Pershing).
    """
    if numero in _CUENTAS_APV:
        return _CUENTAS_APV[numero]
    if numero.isdigit() and int(numero) <= 9:
        return TipoCuenta("CUENTA INVERSION", "", "")
    return None


# --- Construcción de la tabla desde un export ---------------------------------


def construir_desde_export(carpeta: Path) -> list[Instrumento]:
    """Un instrumento por (nombre, nemotécnico, moneda) de los saldos y movimientos
    del export, con el emisor, producto, archivo y precio más frecuentes."""
    datos: dict[tuple[str, str, str], dict[str, Counter]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    fechas = set()
    for tipo, archivo in (
        ("SALDOS_FFMM", "SALDOS_FFMM"),
        ("CUSTODIA_ACCIONES", "CUSTODIA_ACCIONES"),
        ("MOVIMIENTOS_FFMM", "SALDOS_FFMM"),
        ("MOVIMIENTOS_BOLSA", "CUSTODIA_ACCIONES"),
    ):
        for ruta in sorted(carpeta.glob(f"{tipo}_*.csv")):
            with open(ruta, encoding="cp1252", newline="") as f:
                for r in csv.DictReader(f, delimiter=";"):
                    d = datos[(r["Instrumento"], r["NemotecnicoInstrumento"], r["MonedaInstrumento"])]
                    d["filas"][""] += 1
                    d["emisor"][r["Emisor"]] += 1
                    d["producto"][r["Producto"]] += 1
                    d["archivo"][archivo] += 1
                    fechas.add(r["FechaProceso"])
                    precio = _precio_en_moneda_instrumento(r)
                    if precio is not None:
                        d["precio"][precio] += 1
    fecha = max(fechas) if fechas else ""
    instrumentos = []
    for (nombre, nemo, moneda), d in datos.items():
        precio = d["precio"].most_common(1)[0][0] if d["precio"] else None
        instrumentos.append(
            (
                -d["filas"][""],
                Instrumento(
                    nombre=nombre,
                    nemotecnico=nemo,
                    moneda=moneda,
                    emisor=d["emisor"].most_common(1)[0][0],
                    producto=d["producto"].most_common(1)[0][0],
                    archivo=d["archivo"].most_common(1)[0][0],
                    precio_referencia=precio,
                    fecha_referencia=fecha,
                ),
            )
        )
    # Por nombre y, dentro del mismo nombre, la serie más frecuente primero.
    instrumentos.sort(key=lambda x: (x[1].nombre, x[0], x[1].nemotecnico))
    return [i for _, i in instrumentos]


def _precio_en_moneda_instrumento(fila: dict[str, str]) -> Decimal | None:
    """Precio de cierre de una fila de saldos en la moneda del instrumento.

    En CUSTODIA_ACCIONES casi todos los instrumentos en USD valorizados en pesos
    traen el precio en USD, pero algunos lo traen en pesos; se distingue viendo
    cuál cuadra con cantidad × precio = patrimonio.
    """
    if not fila.get("PrecioCierreEnMonedaValoracion"):
        return None
    precio = leer_monto(fila["PrecioCierreEnMonedaValoracion"])
    if fila["MonedaInstrumento"] != "USD" or fila["MonedaValoracionPatrimonio"] != "CLP":
        return precio
    cantidad = leer_monto(fila["Cantidad"])
    patrimonio = leer_monto(fila["PatrimonioEnMonedaValoracion"])
    tc = leer_monto(fila["TipoCambioUSD"])
    if abs(cantidad * precio - patrimonio) < abs(cantidad * precio * tc - patrimonio):
        return (precio / tc).quantize(Decimal("0.000001"))
    return precio


def guardar(instrumentos: list[Instrumento], ruta: Path = RUTA_TABLA) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(_COLUMNAS)
        for i in instrumentos:
            w.writerow(
                (
                    i.nombre,
                    i.nemotecnico,
                    i.moneda,
                    i.emisor,
                    i.producto,
                    i.archivo,
                    escribir_numero(i.precio_referencia, 6),
                    i.fecha_referencia,
                )
            )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python -m cartolas.catalogo <carpeta del export>")
    tabla = construir_desde_export(Path(sys.argv[1]))
    guardar(tabla)
    print(f"{len(tabla)} instrumentos en {RUTA_TABLA}")
