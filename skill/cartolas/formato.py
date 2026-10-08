"""Formato de los archivos de salida, tomado del export de ejemplo de BICE.

Cada archivo es un CSV separado por ``;``, con fin de línea CRLF y números con
coma decimal, sin separador de miles y con una cantidad fija de decimales por
columna. El detalle está en docs/formato-salida.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Columna:
    nombre: str
    # None para columnas de texto; para columnas numéricas, decimales fijos.
    decimales: int | None = None


@dataclass(frozen=True)
class Archivo:
    tipo: str
    columnas: tuple[Columna, ...]
    codificacion: str = "cp1252"

    @property
    def encabezados(self) -> list[str]:
        return [c.nombre for c in self.columnas]

    def nombre_archivo(self, portafolio: str, fecha_proceso: str) -> str:
        """Nombre como en el ejemplo: SALDOS_CAJA_10038_20260922_V2.csv."""
        return f"{self.tipo}_{portafolio}_{fecha_proceso.replace('-', '')}_V2.csv"


def _texto(*nombres: str) -> tuple[Columna, ...]:
    return tuple(Columna(n) for n in nombres)


_CLIENTE = _texto(
    "FechaProceso", "RutCliente", "Cuenta", "Portafolio", "ProductoBase", "Producto"
)
_INSTRUMENTO = _texto("Instrumento", "NemotecnicoInstrumento", "MonedaInstrumento", "Emisor")
_PATRIMONIO = (
    Columna("MonedaValoracionPatrimonio"),
    Columna("PatrimonioEnMonedaValoracion", 6),
    Columna("patrimonioUSD", 6),
    Columna("patrimonioCLP", 6),
)
_APV = _texto("TipoAPV", "DescripcionTipoRegimenTributario")
_CIERRE = (
    Columna("EnTransito"),
    Columna("TipoCambioUSD", 14),
    Columna("TipoCambioEUR", 14),
)
_POSICION = (
    Columna("Cantidad", 6),
    Columna("PrecioCierreEnMonedaValoracion", 6),
    Columna("PrecioPromedioCompra", 4),
)
_OPERACION = (
    Columna("NombreTipoMovimiento"),
    Columna("Moneda"),
    Columna("Cantidad", 4),
    Columna("PrecioTIR", 4),
    Columna("MontoNeto", 2),
)

SALDOS_CAJA = Archivo("SALDOS_CAJA", _CLIENTE + _PATRIMONIO + _APV + _CIERRE)

SALDOS_FFMM = Archivo(
    "SALDOS_FFMM", _CLIENTE + _INSTRUMENTO + _POSICION + _PATRIMONIO + _APV + _CIERRE
)

CUSTODIA_ACCIONES = Archivo(
    "CUSTODIA_ACCIONES", _CLIENTE + _INSTRUMENTO + _POSICION + _PATRIMONIO + _APV + _CIERRE
)

MOVIMIENTOS_DE_CAJA = Archivo(
    "MOVIMIENTOS_DE_CAJA",
    _CLIENTE
    + (
        Columna("Instrumento"),
        Columna("nombreTipoMovimiento"),
        Columna("Moneda"),
        Columna("abono", 2),
        Columna("cargo", 2),
    )
    + _APV,
)

MOVIMIENTOS_BOLSA = Archivo("MOVIMIENTOS_BOLSA", _CLIENTE + _INSTRUMENTO + _OPERACION + _APV)

# "NumeroRerferencia" se escribe así en el export original.
MOVIMIENTOS_FFMM = Archivo(
    "MOVIMIENTOS_FFMM",
    _CLIENTE + _INSTRUMENTO + (Columna("NumeroRerferencia"),) + _OPERACION + _APV,
)

# El ejemplo trae este archivo sin filas, así que los decimales se asumen
# iguales a los de MOVIMIENTOS_BOLSA. El orden de columnas sí es el del ejemplo.
MOVIMIENTOS_PERSHING = Archivo(
    "MOVIMIENTOS_PERSHING",
    (
        Columna("Cantidad", 4),
        Columna("FechaProceso"),
        Columna("RutCliente"),
        Columna("Cuenta"),
        Columna("CuentaPershing"),
        Columna("Portafolio"),
        Columna("ProductoBase"),
        Columna("Producto"),
    )
    + _INSTRUMENTO
    + (
        Columna("NumeroRerferencia"),
        Columna("NombreTipoMovimiento"),
        Columna("Moneda"),
        Columna("PrecioTIR", 4),
        Columna("MontoNeto", 2),
    ),
    codificacion="utf-8",
)

ARCHIVOS = {
    a.tipo: a
    for a in (
        SALDOS_CAJA,
        SALDOS_FFMM,
        CUSTODIA_ACCIONES,
        MOVIMIENTOS_DE_CAJA,
        MOVIMIENTOS_BOLSA,
        MOVIMIENTOS_FFMM,
        MOVIMIENTOS_PERSHING,
    )
}
