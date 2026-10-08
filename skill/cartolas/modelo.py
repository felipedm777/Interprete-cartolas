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
    # Producto base, tipo de APV y régimen. Si quedan vacíos se deducen del número
    # de cuenta BICE (catalogo.tipo_cuenta); las cartolas de otras instituciones
    # los llenan porque sus números de cuenta no siguen esa regla.
    producto_base: str = ""
    tipo_apv: str = ""
    regimen: str = ""


@dataclass
class SaldoCaja:
    cuenta: str
    moneda: str
    monto: Decimal
    # Equivalente en pesos impreso en la cartola, si lo trae.
    monto_clp: Decimal | None = None
    # Pendiente de liquidación (cuentas por cobrar o por pagar): el export lo
    # trae como caja con EnTransito = SI.
    en_transito: bool = False


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
    # Nemotécnico, si la cartola lo trae; se usa para buscar en la tabla maestra.
    nemotecnico: str = ""
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
    # Nemotécnico del instrumento que originó el movimiento (p. ej. un dividendo).
    instrumento: str = ""


@dataclass
class MovimientoTitulo:
    fecha: date
    cuenta: str
    tipo: str
    instrumento: str
    moneda: str
    # Vacíos en movimientos sin cantidad o precio (p. ej. un dividendo Pershing).
    cantidad: Decimal | None
    precio: Decimal | None
    monto: Decimal | None
    referencia: str = ""
    nemotecnico: str = ""
    # Archivo de destino: "FFMM", "BOLSA" o "PERSHING". Vacío: se deduce del tipo
    # ("... FM" a fondos mutuos, "... RV" a bolsa; el resto no se exporta).
    destino: str = ""
    # Producto para instrumentos que no están en la tabla maestra, si la cartola
    # lo deja claro (p. ej. la clase del título en las tenencias Pershing).
    producto: str = ""


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
    # Institución que emite la cartola; la salida escribe un juego de archivos por institución.
    institucion: str = "BICE"
    tipo_cambio_eur: Decimal | None = None
    # Informe provisorio (Larrainvial): si llega también la definitiva del mismo
    # cliente y período, se usa la definitiva.
    provisoria: bool = False
    cuentas: dict[str, Cuenta] = field(default_factory=dict)
    saldos_caja: list[SaldoCaja] = field(default_factory=list)
    posiciones: list[Posicion] = field(default_factory=list)
    movimientos_caja: list[MovimientoCaja] = field(default_factory=list)
    movimientos_titulos: list[MovimientoTitulo] = field(default_factory=list)
    # Totales impresos en la cartola, para las cuadraturas.
    totales: dict[str, Decimal] = field(default_factory=dict)
    controles: list[Control] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
