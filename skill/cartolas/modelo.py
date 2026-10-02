"""Datos extraídos de una cartola, antes de llevarlos al formato de salida."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Cuenta:
    numero: str
    portafolio: str
    # Grupo tal como lo muestra la cartola, p. ej. "Cuenta de Inversión" o "APV Prime".
    grupo: str


@dataclass
class SaldoCaja:
    cuenta: str
    moneda: str
    monto: Decimal
    # Equivalente en pesos impreso en la cartola, si lo trae.
    monto_clp: Decimal | None = None


@dataclass
class Posicion:
    cuenta: str
    seccion: str
    tabla: str
    previsional: bool
    instrumento: str
    moneda: str
    cantidad: Decimal | None
    precio_promedio: Decimal | None
    precio_actual: Decimal | None
    valor_clp: Decimal | None
    valor_usd: Decimal | None
    detalle: list[str] = field(default_factory=list)
    # Columnas de la cartola que no tienen destino en la salida (rentabilidad, % de activo...).
    otros: dict[str, str] = field(default_factory=dict)


@dataclass
class MovimientoCaja:
    fecha: date
    cuenta: str
    tipo: str
    moneda: str
    cargo: Decimal
    abono: Decimal
    folio: str = ""


@dataclass
class MovimientoTitulo:
    fecha: date
    cuenta: str
    tipo: str
    instrumento: str
    moneda: str
    cantidad: Decimal
    precio: Decimal
    monto: Decimal
    referencia: str = ""


@dataclass
class Control:
    """Resultado de una cuadratura: qué se comparó y si cuadró."""

    regla: str
    ok: bool
    detalle: str = ""


@dataclass
class Cartola:
    formato: str
    archivo: str
    rut: str
    nombre: str
    desde: date
    hasta: date
    tipo_cambio_usd: Decimal | None
    cuentas: dict[str, Cuenta] = field(default_factory=dict)
    saldos_caja: list[SaldoCaja] = field(default_factory=list)
    posiciones: list[Posicion] = field(default_factory=list)
    movimientos_caja: list[MovimientoCaja] = field(default_factory=list)
    movimientos_titulos: list[MovimientoTitulo] = field(default_factory=list)
    # Totales impresos en la cartola, para las cuadraturas.
    totales: dict[str, Decimal] = field(default_factory=dict)
    controles: list[Control] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
