"""Cartola Mensual de Corredores de Bolsa SURA.

Páginas carta verticales: la p.1 con el cliente, el Resumen de Saldos por
Instrumento (en pesos y, si hay caja en dólares, en USD) y el Resumen de
Movimientos; el Detalle de Inversiones Previsionales y el de Financieras, cada
uno solo si tiene saldos y seguido siempre de sus movimientos, y una página
legal con el glosario. El formato está descrito en docs/instituciones/sura.md.

No trae RUT ni número de cuenta: el RUT queda vacío y las cuentas siguen una
convención (CUENTA_FINANCIERA y REGIMENES_APV). Tampoco trae el costo de las
posiciones ni folios.
"""

import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import product
from pathlib import Path

import pymupdf

from ..modelo import (
    Cartola,
    Control,
    Cuenta,
    MovimientoCaja,
    MovimientoTitulo,
    Posicion,
    SaldoCaja,
)
from ..numeros import leer_monto
from ..pdf import Span, leer_spans

FORMATO = "Sura"

_TITULO = "Cartola Mensual"
_SITIO = "sura.cl"
_PERIODO = re.compile(r"PER[IÍ]ODO (\d{2}/\d{2}/\d{4}) - (\d{2}/\d{2}/\d{4})")
# Arriba va el encabezado de página (título, subtítulo y período) y abajo, el
# pie (teléfono, número de página y sitio).
_Y_CONTENIDO = 80
_Y_PIE = 755

_NUMERO = re.compile(r"(US)?\$?-?\d[\d.]*(,\d+)?")
_FECHA = re.compile(r"\d{2}/\d{2}/\d{4}")
_MONEDAS = {"CLP", "USD"}

# Columnas de cada tabla: (nombre, borde derecho). Cada fragmento va a la primera
# columna cuyo borde pasa de su centro. Los bordes van entre los datos y no entre
# los encabezados: en Previsionales los datos están corridos unos 5–8 pt a la
# derecha, y en Cuentas de Inversiones los encabezados no calzan con los datos.
_COLUMNAS_DETALLE = (
    ("instrumento", 160),
    ("serie", 195),
    ("regimen", 250),
    ("moneda", 300),
    ("cantidad", 375),
    ("precio", 445),
    ("tc", 510),
    ("saldo", math.inf),
)
_COLUMNAS_TITULOS = (
    ("instrumento", 125),
    ("fecha", 166),
    ("concepto", 232),
    ("serie", 258),
    ("regimen", 300),
    ("moneda", 345),
    ("cantidad", 410),
    ("precio", 466),
    ("tc", 527),
    ("monto", math.inf),
)
# El encabezado dice Operación | Fecha | Concepto, pero los datos son el concepto,
# la fecha y la operación (Abono o Cargo).
_COLUMNAS_CAJA = (
    ("concepto", 135),
    ("fecha", 179),
    ("operacion", 240),
    ("regimen", 295),
    ("moneda", 345),
    ("cargo", 430),
    ("abono", 505),
    ("saldo", math.inf),
)
# Los encabezados de tabla ocupan 3 líneas; cada una trae alguna de estas palabras.
_ENCABEZADOS = {"Régimen", "Tributario", "Instrumento", "Instrumentos en Dólar", "Operación"}
# Un nombre de 2 líneas tiene la primera hasta 3,5 pt sobre la línea con los datos
# de su fila y la segunda, debajo: cada línea sin datos va con la última fila que
# empieza a menos de esta distancia bajo ella.
_DESFASE = 4.5

_SEGMENTOS = {
    "inversiones previsionales": "Previsionales",
    "inversiones financieras": "Financieras",
    "inversion total": "Total",
    "inversiones totales": "Total",
}
_CAJA = "Cuenta de Inversiones"
# Grupos de instrumentos con las variantes de escritura del resumen, el detalle y
# los movimientos (sin tildes ni mayúsculas).
_GRUPOS = {
    "acciones": "Acciones",
    "fondos de inversion": "Fondos de Inversión",
    "fondo de inversiones": "Fondos de Inversión",
    "fondos mutuos": "Fondos Mutuos",
    "cuenta de inversiones": _CAJA,
    "cuenta de inversiones usd": _CAJA,
    "cuentas inversiones usd": _CAJA,
    "cuentas de inversion usd": _CAJA,
}
_TABLAS = {
    "Acciones": "Acciones",
    "Fondos de Inversión": "CFI",
    "Fondos Mutuos": "Fondos Mutuos Otras AGF",
}
_PRODUCTOS_BOLSA = {"Acciones": "ACCIONES", "Fondos de Inversión": "CFI"}

# Cuenta de todo lo de Inversiones Financieras, sea cual sea su régimen (18Q, 18T,
# R.GRAL...). En Inversiones Previsionales cada régimen es una cuenta, con el
# código del régimen como número.
CUENTA_FINANCIERA = "0"
# Régimen previsional -> (tipo de APV, régimen tributario del export).
REGIMENES_APV = {
    "CVA_B": ("CV", "BONIFICACIÓN"),
    "CVN_A": ("CV", "APORTE"),
    "CVN_B": ("CV", "BONIFICACIÓN"),
    "DCA": ("DC", "BONIFICACIÓN"),
    "DCN": ("DC", "BONIFICACIÓN"),
    "DCR": ("DC", "BONIFICACIÓN"),
    # Bonificación fiscal: como las cuentas "BF" de BICE.
    "BON_F": ("DAPVC", "APORTE"),
}

# Movimientos de caja con equivalente en el vocabulario del export (el de BICE):
# (concepto sin tildes ni mayúsculas, moneda) -> tipo. El resto queda con el
# concepto en mayúsculas, como "Retiro desde Cta Inversión", que puede ser un
# retiro o el pago de un aporte a un fondo mutuo.
TIPOS_CAJA = {
    ("dividendo en pesos", "CLP"): "DIVIDENDO EN PESOS",
    ("factura compra rv", "CLP"): "FACTURA COMPRA RV",
    ("abono a cuenta de inversiones", "CLP"): "ABONO CUENTA INVERSION $",
    ("abono a cta inv sura x rescate", "CLP"): "ABONO ORIGINADO POR PAGO RESCATES $ OWP",
}
# Movimientos de títulos de FI y acciones con equivalente en el export. Los de
# fondos mutuos son INVERSION FM en Aportes/Compras y RESCATE FM en Rescates/Ventas.
TIPOS_BOLSA = {"compra rv": "COMPRA RV"}

_CERO = Decimal(0)
_UNO = Decimal(1)
_CENTESIMO = Decimal("0.01")


def paginas(doc: pymupdf.Document) -> list[int]:
    """Todas las páginas, si la primera es una Cartola Mensual de SURA.

    El estado de cuenta Pershing que llega con algunas cartolas Sura es otro
    formato y lo lee su propio extractor.
    """
    if doc.page_count == 0:
        return []
    texto = doc[0].get_text()
    if _TITULO in texto and _SITIO in texto and _PERIODO.search(texto) and "Pershing" not in texto:
        return list(range(doc.page_count))
    return []


# --- Texto ---------------------------------------------------------------------


def _norma(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def _es_numero(texto: str) -> bool:
    return bool(_NUMERO.fullmatch(texto))


def _monto(texto: str | None) -> Decimal | None:
    if not texto or texto == "-":
        return None
    return leer_monto(texto)


def _fecha(texto: str) -> date:
    return datetime.strptime(texto, "%d/%m/%Y").date()


def _texto(linea: list[Span]) -> str:
    return " ".join(s.texto for s in linea)


def _tolerancia(moneda: str) -> Decimal:
    return _UNO if moneda == "CLP" else _CENTESIMO


def _lineas(spans: list[Span]) -> list[list[Span]]:
    """Agrupa los fragmentos en líneas, de arriba abajo y de izquierda a derecha.

    La tolerancia es chica porque las líneas de un nombre de 2 líneas quedan a
    solo 2–3,5 pt de la línea con los datos.
    """
    lineas: list[list[Span]] = []
    for s in sorted(spans, key=lambda s: s.yc):
        if lineas and abs(lineas[-1][0].yc - s.yc) <= 1.2:
            lineas[-1].append(s)
        else:
            lineas.append([s])
    return [sorted(l, key=lambda s: s.x0) for l in lineas]


def _instrumento(nombre: str, serie: str) -> str:
    # En los fondos mutuos la serie va en su columna; en los FI viene en el nombre.
    return f"{nombre} SERIE {serie}" if serie not in ("", "-") else nombre


# --- Cuadraturas ------------------------------------------------------------------


class _Cuadraturas:
    """Junta las comparaciones de cada regla y entrega un Control por regla."""

    def __init__(self) -> None:
        self.reglas: dict[str, tuple[int, list[str]]] = {}

    def revisar(self, regla: str, ok: bool, que: str) -> None:
        n, malas = self.reglas.get(regla, (0, []))
        self.reglas[regla] = (n + 1, malas if ok else malas + [que])

    def comparar(
        self,
        regla: str,
        calculado: Decimal | None,
        impreso: Decimal | None,
        tolerancia: Decimal,
        que: str = "",
    ) -> None:
        prefijo = f"{que}: " if que else ""
        if impreso is None or calculado is None:
            falta = "impreso" if impreso is None else "para calcular"
            self.revisar(regla, False, f"{prefijo}no se encontró el valor {falta}")
            return
        diferencia = calculado - impreso
        self.revisar(
            regla,
            abs(diferencia) <= tolerancia,
            f"{prefijo}calculado {calculado}, impreso {impreso}, diferencia {diferencia}",
        )

    def controles(self) -> list[Control]:
        return [
            Control(regla if n == 1 else f"{regla} ({n})", not malas, "; ".join(malas))
            for regla, (n, malas) in self.reglas.items()
        ]


# --- Extracción ------------------------------------------------------------------


@dataclass
class _Bloque:
    """Una sección de la cartola: desde su título hasta el siguiente."""

    tipo: str
    segmento: str = ""
    moneda: str = "CLP"
    # "Aportes/Compras" o "Rescates/Ventas" en los movimientos de títulos.
    nombre: str = ""
    # Grupo de instrumentos en curso (Fondos Mutuos, Acciones...).
    grupo: str = ""

    @property
    def donde(self) -> str:
        usd = " USD" if self.moneda == "USD" else ""
        if self.tipo == "detalle":
            return f"Detalle de Inversiones {self.segmento}{usd}"
        if self.tipo == "caja":
            return f"Cuentas de Inversiones{usd} ({self.segmento})"
        return f"{self.nombre} ({self.segmento})"


@dataclass
class _Rotulo:
    """Línea en negrita del margen izquierdo: un grupo, un subtotal o un saldo."""

    texto: str
    valor: Decimal | None


@dataclass
class _Lectura:
    """Lo leído de la cartola, incluidos los totales que solo sirven para cuadrar."""

    cartola: Cartola
    # Resumen de Saldos: (moneda, fila, segmento, fecha) -> valor. La fila es un
    # grupo o "Total" y el segmento, Previsionales, Financieras o Total.
    saldos: dict[tuple[str, str, str, date], Decimal] = field(default_factory=dict)
    # Resumen de Movimientos: (fila, segmento) -> valor.
    resumen_movimientos: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    # Detalle de Inversiones: por (segmento, moneda, grupo), la suma de los saldos
    # de las filas y el SUBTOTAL; por (segmento, moneda), el TOTAL INVERSIONES.
    suma_grupos: dict[tuple[str, str, str], Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    subtotales: dict[tuple[str, str, str], Decimal | None] = field(default_factory=dict)
    totales_detalle: dict[tuple[str, str], Decimal | None] = field(default_factory=dict)
    # Tipo Cambio Observado de las filas en USD del detalle.
    cambios: Counter = field(default_factory=Counter)
    # Movimientos de títulos, por (segmento, tabla): Montos en CLP y su TOTAL.
    montos: dict[tuple[str, str], list[Decimal]] = field(default_factory=lambda: defaultdict(list))
    totales_titulos: dict[tuple[str, str], Decimal | None] = field(default_factory=dict)
    # Cuentas de Inversiones, por (segmento, moneda): Saldo Inicial y Final, y
    # suma de abonos y de cargos. El saldo corrido va por régimen.
    saldos_caja: dict[tuple[str, str], dict[str, Decimal | None]] = field(
        default_factory=lambda: defaultdict(dict)
    )
    flujos: dict[tuple[str, str], list[Decimal]] = field(
        default_factory=lambda: defaultdict(lambda: [_CERO, _CERO])
    )
    corrido: dict[tuple[str, str, str], Decimal] = field(default_factory=dict)
    cuadraturas: _Cuadraturas = field(default_factory=_Cuadraturas)


def extraer(ruta: str | Path, paginas: list[int] | None = None) -> Cartola:
    doc = pymupdf.open(ruta)
    indices = paginas if paginas is not None else list(range(doc.page_count))
    if not indices:
        raise ValueError(f"{ruta}: no trae páginas de la cartola Sura")
    hojas = [leer_spans(doc[i]) for i in indices]
    lectura = _cabecera(hojas[0], str(ruta))
    bloque = None
    for numero, spans in zip(indices, hojas):
        if any(s.texto == "Glosario:" for s in spans):
            continue  # texto legal
        contenido = [s for s in spans if _Y_CONTENIDO < s.yc < _Y_PIE]
        bloque = _pagina(numero + 1, contenido, lectura, bloque)
    _completar(lectura)
    lectura.cartola.controles = _controles(lectura)
    return lectura.cartola


def _cabecera(spans: list[Span], archivo: str) -> _Lectura:
    periodo = next(
        (m for s in spans if s.yc < _Y_CONTENIDO and (m := _PERIODO.search(s.texto))),
        None,
    )
    etiqueta = next((s for s in spans if s.texto == "Cliente:"), None)
    if periodo is None or etiqueta is None:
        raise ValueError(f"{archivo}: no se encontró el período o el cliente en la p.1")
    # El nombre puede venir en varios fragmentos y con fuentes distintas.
    nombre = sorted(
        (s for s in spans if abs(s.yc - etiqueta.yc) <= 3 and etiqueta.x1 - 1 <= s.x0 < 300),
        key=lambda s: s.x0,
    )
    cartola = Cartola(
        formato=FORMATO,
        archivo=archivo,
        rut="",
        nombre=" ".join(s.texto for s in nombre),
        desde=_fecha(periodo.group(1)),
        hasta=_fecha(periodo.group(2)),
        tipo_cambio_usd=None,
        institucion="SURA",
    )
    cartola.avisos.append(
        "La cartola no trae RUT ni número de cuenta: el RUT queda vacío y las cuentas siguen la "
        f"convención del extractor ({CUENTA_FINANCIERA} para Inversiones Financieras y el régimen "
        "tributario para las previsionales)"
    )
    return _Lectura(cartola)


def _pagina(numero: int, contenido: list[Span], lectura: _Lectura, bloque: _Bloque | None) -> _Bloque | None:
    """Lee una página y devuelve la sección en que termina: si la página siguiente
    empieza sin título, sigue en ella."""
    tramos: list[tuple[_Bloque | None, list[list[Span]]]] = [(bloque, [])]
    for linea in _lineas(contenido):
        primero = linea[0]
        if len(linea) == 1 and primero.x0 < 22 and primero.tamano >= 9:
            bloque = _titulo(primero.texto, bloque)
            if bloque is None:
                lectura.cartola.avisos.append(
                    f"Página {numero}: sección «{primero.texto}» desconocida, no se leyó"
                )
            tramos.append((bloque, []))
        else:
            tramos[-1][1].append(linea)
    for tramo, lineas in tramos:
        if not lineas:
            continue
        if tramo is None:
            # En la p.1, el encabezado con el cliente.
            if numero != 1:
                lectura.cartola.avisos.append(f"Página {numero}: texto fuera de las secciones conocidas")
            continue
        _LECTORES[tramo.tipo](tramo, lineas, lectura)
    return bloque


def _titulo(texto: str, anterior: _Bloque | None) -> _Bloque | None:
    t = _norma(texto)
    if t == "resumen de saldos por instrumento":
        return _Bloque("saldos")
    if t == "resumen de movimientos":
        return _Bloque("resumen de movimientos")
    if m := re.fullmatch(r"detalle de inversiones (previsionales|financieras)( usd)?", t):
        return _Bloque("detalle", m.group(1).capitalize(), "USD" if m.group(2) else "CLP")
    if m := re.fullmatch(r"movimientos inversiones (previsionales|financieras)", t):
        return _Bloque("movimientos", m.group(1).capitalize())
    segmento = anterior.segmento if anterior else ""
    if t in ("aportes/compras", "rescates/ventas") and segmento:
        nombre = "Aportes/Compras" if t == "aportes/compras" else "Rescates/Ventas"
        return _Bloque("titulos", segmento, nombre=nombre)
    if (m := re.fullmatch(r"cuentas de inversiones( usd)?", t)) and segmento:
        return _Bloque("caja", segmento, "USD" if m.group(1) else "CLP")
    return None


def _tabla(lineas: list[list[Span]], columnas: tuple, es_fila, bloque: _Bloque, lectura: _Lectura) -> list:
    """Rótulos y filas (columna -> texto) de una tabla, en orden.

    Cada fila se arma desde la línea con sus datos (es_fila), a la que se pegan
    las líneas de un nombre o concepto de 2 líneas.
    """
    partes: list = []
    filas: list[tuple[float, list[list[Span]]]] = []
    sueltas: list[list[Span]] = []

    def cerrar() -> None:
        for linea in sueltas:
            fila = next((f for f in reversed(filas) if f[0] <= linea[0].yc + _DESFASE), None)
            if fila is None:
                lectura.cartola.avisos.append(f"{bloque.donde}: texto sin fila «{_texto(linea)}»")
            else:
                fila[1].append(linea)
        partes.extend(_celdas(f[1], columnas) for f in filas)
        filas.clear()
        sueltas.clear()

    for linea in lineas:
        if {s.texto for s in linea} & _ENCABEZADOS or _norma(_texto(linea)).startswith("no se registran"):
            continue
        if linea[0].negrita and linea[0].x0 < 30:
            cerrar()
            numeros = [s for s in linea if _es_numero(s.texto)]
            etiqueta = " ".join(s.texto for s in linea if s.x1 < 300 and not _es_numero(s.texto))
            partes.append(_Rotulo(etiqueta, leer_monto(numeros[-1].texto) if numeros else None))
        elif es_fila(_celdas([linea], columnas)):
            filas.append((linea[0].yc, [linea]))
        else:
            sueltas.append(linea)
    cerrar()
    return partes


def _celdas(lineas: list[list[Span]], columnas: tuple) -> dict[str, str]:
    celdas: dict[str, list[str]] = defaultdict(list)
    for linea in sorted(lineas, key=lambda l: l[0].yc):
        for s in linea:
            nombre = next(n for n, borde in columnas if s.xc < borde)
            celdas[nombre].append(s.texto)
    return {k: " ".join(v) for k, v in celdas.items()}


def _con_datos(celdas: dict[str, str]) -> bool:
    return any(k != "instrumento" for k in celdas)


def _con_fecha(celdas: dict[str, str]) -> bool:
    return bool(_FECHA.fullmatch(celdas.get("fecha", "")))


def _cuenta(lectura: _Lectura, segmento: str, regimen: str) -> str:
    cuentas = lectura.cartola.cuentas
    if segmento == "Financieras":
        if CUENTA_FINANCIERA not in cuentas:
            cuentas[CUENTA_FINANCIERA] = Cuenta(
                CUENTA_FINANCIERA,
                portafolio="",
                grupo="Inversiones Financieras",
                producto_base="CUENTA INVERSION",
            )
        return CUENTA_FINANCIERA
    if regimen not in cuentas:
        if regimen not in REGIMENES_APV:
            lectura.cartola.avisos.append(
                f"Régimen previsional {regimen} desconocido: su cuenta va sin tipo de APV ni régimen"
            )
        tipo_apv, descripcion = REGIMENES_APV.get(regimen, ("", ""))
        cuentas[regimen] = Cuenta(
            regimen,
            portafolio="",
            grupo="Inversiones Previsionales",
            producto_base="APV PRIME",
            tipo_apv=tipo_apv,
            regimen=descripcion,
        )
    return regimen


# --- p.1: resúmenes ----------------------------------------------------------------


def _resumen_saldos(bloque: _Bloque, lineas: list[list[Span]], lectura: _Lectura) -> None:
    """Resumen de Saldos por Instrumento, en pesos y en USD.

    Los valores se asignan por coordenadas: en el orden del texto los encabezados
    "del 31/08" salen antes que "del 31/07", al revés de como se ven.
    """
    segmentos: list[tuple[float, str]] = []
    columnas: list[tuple[float, str, date]] = []
    moneda = "CLP"
    for linea in lineas:
        normas = [_norma(s.texto) for s in linea]
        if any(n in _SEGMENTOS for n in normas):
            segmentos = [(s.xc, _SEGMENTOS[n]) for s, n in zip(linea, normas) if n in _SEGMENTOS]
            continue
        fechas = [(s, m) for s in linea if (m := re.fullmatch(r"del (\d{2}/\d{2}/\d{4})", s.texto))]
        if fechas and segmentos:
            moneda = "USD" if "dolar" in normas[0] else "CLP"
            columnas = [
                (s.x1, min(segmentos, key=lambda g: abs(g[0] - s.xc))[1], _fecha(m.group(1)))
                for s, m in fechas
            ]
            continue
        valores = [s for s in linea[1:] if _es_numero(s.texto)]
        n = normas[0]
        fila = "Total" if n in ("total", "total usd") else _GRUPOS.get(n)
        if not columnas or not valores or fila is None:
            lectura.cartola.avisos.append(f"Resumen de Saldos: fila no reconocida «{_texto(linea)}»")
            continue
        for s in valores:
            _, segmento, fecha = min(columnas, key=lambda c: abs(c[0] - s.x1))
            lectura.saldos[(moneda, fila, segmento, fecha)] = leer_monto(s.texto)


def _resumen_movimientos(bloque: _Bloque, lineas: list[list[Span]], lectura: _Lectura) -> None:
    segmentos: list[tuple[float, str]] = []
    for linea in lineas:
        normas = [_norma(s.texto) for s in linea]
        if any(n in _SEGMENTOS for n in normas):
            segmentos = [(s.x1, _SEGMENTOS[n]) for s, n in zip(linea, normas) if n in _SEGMENTOS]
            continue
        valores = [s for s in linea[1:] if _es_numero(s.texto)]
        if not segmentos or not valores:
            lectura.cartola.avisos.append(f"Resumen de Movimientos: fila no reconocida «{_texto(linea)}»")
            continue
        fila = _norma(_FECHA.sub("", linea[0].texto))
        for s in valores:
            segmento = min(segmentos, key=lambda g: abs(g[0] - s.x1))[1]
            lectura.resumen_movimientos[(fila, segmento)] = leer_monto(s.texto)


# --- Detalle de Inversiones ---------------------------------------------------------


def _detalle(bloque: _Bloque, lineas: list[list[Span]], lectura: _Lectura) -> None:
    clave = (bloque.segmento, bloque.moneda)
    for parte in _tabla(lineas, _COLUMNAS_DETALLE, _con_datos, bloque, lectura):
        if isinstance(parte, _Rotulo):
            n = _norma(parte.texto)
            if n.startswith("subtotal "):
                grupo = _GRUPOS.get(n.removeprefix("subtotal "), parte.texto)
                lectura.subtotales[clave + (grupo,)] = parte.valor
            elif n.startswith("total inversiones "):
                lectura.totales_detalle[clave] = parte.valor
            elif n in _GRUPOS:
                bloque.grupo = _GRUPOS[n]
            else:
                bloque.grupo = ""
                lectura.cartola.avisos.append(f"{bloque.donde}: grupo desconocido «{parte.texto}»")
            continue
        _fila_detalle(bloque, parte, lectura)


def _fila_detalle(bloque: _Bloque, c: dict[str, str], lectura: _Lectura) -> None:
    cartola = lectura.cartola
    nombre, serie, regimen, moneda = (c.get(k, "") for k in ("instrumento", "serie", "regimen", "moneda"))
    try:
        cantidad, precio, cambio, saldo = (_monto(c.get(k)) for k in ("cantidad", "precio", "tc", "saldo"))
    except ValueError:
        cantidad = None
    grupo = bloque.grupo
    if not (grupo and nombre and regimen) or moneda not in _MONEDAS or cantidad is None:
        cartola.avisos.append(f"{bloque.donde}: fila no reconocida «{' '.join(c.values())}»")
        return
    instrumento = _instrumento(nombre, serie)
    lectura.suma_grupos[(bloque.segmento, bloque.moneda, grupo)] += saldo or _CERO
    if cambio is not None:
        lectura.cambios[cambio] += 1
    if precio is not None and saldo is not None:
        calculado = cantidad * precio
        if bloque.moneda == "USD":
            tolerancia = _CENTESIMO
        elif moneda == "USD":
            calculado = calculado * cambio if cambio is not None else None
            tolerancia = max(Decimal(5), abs(saldo) * Decimal("1e-5"))
        else:
            tolerancia = _UNO
        lectura.cuadraturas.comparar(
            "Detalle de Inversiones: cantidad × precio (× tipo de cambio) = saldo",
            calculado,
            saldo,
            tolerancia,
            f"{instrumento} ({regimen})",
        )
    cuenta = _cuenta(lectura, bloque.segmento, regimen)
    if grupo == _CAJA:
        if saldo:
            cartola.saldos_caja.append(SaldoCaja(cuenta, moneda, saldo))
        return
    if bloque.moneda != "CLP":
        cartola.avisos.append(f"{bloque.donde}: «{instrumento}» no es caja y no se leyó")
        return
    # Un fondo mutuo listado entre los FI (el LarrainVial Enfoque) queda como CFI,
    # igual que en el export BICE.
    tabla = _TABLAS[grupo]
    otros = {"Régimen Tributario": regimen}
    if cambio is not None:
        otros["Tipo Cambio Observado"] = c["tc"]
    cartola.posiciones.append(
        Posicion(
            cuenta=cuenta,
            seccion=grupo,
            tabla=tabla,
            previsional=bloque.segmento == "Previsionales",
            instrumento=instrumento,
            moneda=moneda,
            cantidad=cantidad,
            precio_promedio=None,
            precio_actual=precio,
            valor_clp=saldo,
            valor_usd=cantidad * precio if moneda == "USD" and precio is not None else None,
            nemotecnico=nombre if grupo == "Acciones" else "",
            otros=otros,
        )
    )
    if precio is None or saldo is None:
        cartola.avisos.append(
            f"{instrumento} ({regimen}): la cartola no trae su precio ni su saldo (puede ser una compra "
            "reciente); se exporta sin valor"
        )


# --- Movimientos ------------------------------------------------------------------


def _titulos(bloque: _Bloque, lineas: list[list[Span]], lectura: _Lectura) -> None:
    """Aportes/Compras o Rescates/Ventas."""
    clave = (bloque.segmento, bloque.nombre)
    for parte in _tabla(lineas, _COLUMNAS_TITULOS, _con_fecha, bloque, lectura):
        if isinstance(parte, _Rotulo):
            n = _norma(parte.texto)
            if n.startswith("total "):
                lectura.totales_titulos[clave] = parte.valor
            elif n in _GRUPOS and _GRUPOS[n] != _CAJA:
                bloque.grupo = _GRUPOS[n]
            else:
                bloque.grupo = ""
                lectura.cartola.avisos.append(f"{bloque.donde}: grupo desconocido «{parte.texto}»")
            continue
        _movimiento_titulo(bloque, parte, lectura)


def _movimiento_titulo(bloque: _Bloque, c: dict[str, str], lectura: _Lectura) -> None:
    cartola = lectura.cartola
    nombre, concepto, serie, regimen, moneda = (
        c.get(k, "") for k in ("instrumento", "concepto", "serie", "regimen", "moneda")
    )
    try:
        cantidad, precio, cambio, monto_clp = (
            _monto(c.get(k)) for k in ("cantidad", "precio", "tc", "monto")
        )
    except ValueError:
        cantidad = None
    grupo = bloque.grupo
    if (
        not (grupo and nombre and concepto and regimen)
        or moneda not in _MONEDAS
        or None in (cantidad, precio)
    ):
        cartola.avisos.append(f"{bloque.donde}: fila no reconocida «{' '.join(c.values())}»")
        return
    instrumento = _instrumento(nombre, serie)
    que = f"{c['fecha']} {concepto} {instrumento}"
    lectura.montos[(bloque.segmento, bloque.nombre)].append(monto_clp or _CERO)
    if monto_clp is not None:
        lectura.cuadraturas.comparar(
            "Movimientos de títulos: cantidad × precio (× tipo de cambio de operación) = Monto en CLP",
            cantidad * precio * (cambio or _UNO),
            monto_clp,
            _UNO if cambio is None else max(Decimal(5), abs(monto_clp) * Decimal("1e-5")),
            que,
        )
    if grupo == "Fondos Mutuos":
        tipo = "INVERSION FM" if bloque.nombre == "Aportes/Compras" else "RESCATE FM"
        destino, producto = "FFMM", ""
    else:
        tipo = TIPOS_BOLSA.get(_norma(concepto), concepto.upper())
        destino, producto = "BOLSA", _PRODUCTOS_BOLSA[grupo]
        if _norma(concepto) not in TIPOS_BOLSA:
            cartola.avisos.append(
                f"Movimiento de títulos «{concepto}» sin equivalente en el export: va como {tipo}"
            )
    if moneda == "USD":
        monto = (cantidad * precio).quantize(_CENTESIMO, ROUND_HALF_UP)
        cartola.avisos.append(
            f"{que}: el monto va en USD (cantidad × precio); la cartola trae {c.get('monto', '')} "
            f"en pesos al tipo de cambio de operación {c.get('tc', '')}"
        )
    elif monto_clp is None:
        monto = (cantidad * precio).quantize(_CENTESIMO, ROUND_HALF_UP)
        cartola.avisos.append(f"{que}: sin Monto en CLP, se usó cantidad × precio")
    else:
        monto = monto_clp
    cartola.movimientos_titulos.append(
        MovimientoTitulo(
            fecha=_fecha(c["fecha"]),
            cuenta=_cuenta(lectura, bloque.segmento, regimen),
            tipo=tipo,
            instrumento=instrumento,
            moneda=moneda,
            cantidad=cantidad,
            precio=precio,
            monto=monto,
            nemotecnico=nombre if grupo == "Acciones" else "",
            destino=destino,
            producto=producto,
        )
    )


def _movimientos_caja(bloque: _Bloque, lineas: list[list[Span]], lectura: _Lectura) -> None:
    """Cuentas de Inversiones y Cuentas de Inversiones USD."""
    saldos = lectura.saldos_caja[(bloque.segmento, bloque.moneda)]
    for parte in _tabla(lineas, _COLUMNAS_CAJA, _con_fecha, bloque, lectura):
        if isinstance(parte, _Rotulo):
            n = _norma(parte.texto)
            if n in ("saldo inicial", "saldo final"):
                saldos[n] = parte.valor
            elif n == "saldo en garantia":
                if parte.valor:
                    lectura.cartola.avisos.append(
                        f"{bloque.donde}: Saldo en Garantía de {parte.valor}, no se exporta"
                    )
            else:
                lectura.cartola.avisos.append(f"{bloque.donde}: fila no reconocida «{parte.texto}»")
            continue
        _movimiento_caja(bloque, parte, lectura)


def _movimiento_caja(bloque: _Bloque, c: dict[str, str], lectura: _Lectura) -> None:
    cartola = lectura.cartola
    concepto, operacion, regimen, moneda = (
        c.get(k, "") for k in ("concepto", "operacion", "regimen", "moneda")
    )
    try:
        cargo, abono, saldo = (_monto(c.get(k)) for k in ("cargo", "abono", "saldo"))
    except ValueError:
        cargo = None
    if not concepto or not regimen or moneda != bloque.moneda or None in (cargo, abono, saldo):
        cartola.avisos.append(f"{bloque.donde}: fila no reconocida «{' '.join(c.values())}»")
        return
    que = f"{c['fecha']} {concepto} ({regimen})"
    clave = (bloque.segmento, moneda)
    lectura.flujos[clave][0] += abono
    lectura.flujos[clave][1] += cargo
    lectura.cuadraturas.revisar(
        "Cuentas de Inversiones: la operación (Abono o Cargo) calza con la columna del monto",
        (operacion == "Abono" and abono > 0 and not cargo)
        or (operacion == "Cargo" and cargo > 0 and not abono),
        f"{que}: {operacion}, cargo {cargo}, abono {abono}",
    )
    # La columna Saldo es un saldo corrido por régimen que no parte del Saldo
    # Inicial impreso: solo se revisa la diferencia con la fila anterior.
    corrido = clave + (regimen,)
    if corrido in lectura.corrido:
        lectura.cuadraturas.comparar(
            "Cuentas de Inversiones: saldo anterior del régimen + abono − cargo = saldo",
            lectura.corrido[corrido] + abono - cargo,
            saldo,
            _tolerancia(moneda),
            que,
        )
    lectura.corrido[corrido] = saldo
    cartola.movimientos_caja.append(
        MovimientoCaja(
            fecha=_fecha(c["fecha"]),
            cuenta=_cuenta(lectura, bloque.segmento, regimen),
            tipo=TIPOS_CAJA.get((_norma(concepto), moneda), concepto.upper()),
            moneda=moneda,
            cargo=cargo,
            abono=abono,
        )
    )


def _sin_tabla(bloque: _Bloque, lineas: list[list[Span]], lectura: _Lectura) -> None:
    for linea in lineas:
        lectura.cartola.avisos.append(
            f"Movimientos Inversiones {bloque.segmento}: texto no reconocido «{_texto(linea)}»"
        )


_LECTORES = {
    "saldos": _resumen_saldos,
    "resumen de movimientos": _resumen_movimientos,
    "detalle": _detalle,
    "movimientos": _sin_tabla,
    "titulos": _titulos,
    "caja": _movimientos_caja,
}


def _completar(lectura: _Lectura) -> None:
    """Tipo de cambio, equivalente en pesos de la caja en USD y totales impresos."""
    cartola = lectura.cartola
    if lectura.cambios:
        cartola.tipo_cambio_usd = lectura.cambios.most_common(1)[0][0]
        if len(lectura.cambios) > 1:
            otros = ", ".join(str(c) for c in lectura.cambios if c != cartola.tipo_cambio_usd)
            cartola.avisos.append(
                "El Detalle trae más de un tipo de cambio observado: se usó "
                f"{cartola.tipo_cambio_usd} (también {otros})"
            )
    for s in cartola.saldos_caja:
        if s.moneda == "USD" and cartola.tipo_cambio_usd:
            s.monto_clp = s.monto * cartola.tipo_cambio_usd
    t = cartola.totales
    for (moneda, fila, segmento, fecha), valor in lectura.saldos.items():
        t[f"resumen:{moneda}:{fila}:{segmento}:{fecha.isoformat()}"] = valor
    for (fila, segmento), valor in lectura.resumen_movimientos.items():
        t[f"resumen movimientos:{fila}:{segmento}"] = valor
    for (segmento, moneda, grupo), valor in lectura.subtotales.items():
        if valor is not None:
            t[f"detalle:{segmento}:{moneda}:{grupo}"] = valor
    for (segmento, moneda), valor in lectura.totales_detalle.items():
        if valor is not None:
            t[f"detalle:{segmento}:{moneda}:TOTAL"] = valor


def _controles(lectura: _Lectura) -> list[Control]:
    """Las cuadraturas de docs/instituciones/sura.md §6.

    Las de cada fila (cantidad × precio, saldo corrido) se juntan al leer; aquí
    van las de sumas y totales.
    """
    c = lectura.cuadraturas
    cierre = lectura.cartola.hasta
    inicio = lectura.cartola.desde - timedelta(days=1)
    saldos = lectura.saldos

    # Detalle: filas -> SUBTOTAL -> TOTAL INVERSIONES, y contra el Resumen de Saldos.
    for clave in sorted(set(lectura.suma_grupos) | set(lectura.subtotales)):
        c.comparar(
            "Detalle de Inversiones: suma de las filas del grupo = SUBTOTAL",
            lectura.suma_grupos.get(clave, _CERO),
            lectura.subtotales.get(clave),
            _tolerancia(clave[1]),
            " ".join(clave),
        )
    sumas: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for (segmento, moneda, _), valor in lectura.subtotales.items():
        sumas[(segmento, moneda)] += valor or _CERO
    for clave in sorted(set(sumas) | set(lectura.totales_detalle)):
        c.comparar(
            "Detalle de Inversiones: suma de los SUBTOTAL = TOTAL INVERSIONES",
            sumas.get(clave, _CERO),
            lectura.totales_detalle.get(clave),
            _tolerancia(clave[1]),
            " ".join(clave),
        )
    al_cierre = {
        (segmento, moneda, fila): valor
        for (moneda, fila, segmento, fecha), valor in saldos.items()
        if fecha == cierre and segmento != "Total"
    }
    grupos = set(lectura.subtotales) | {k for k, v in al_cierre.items() if v and k[2] != "Total"}
    for clave in sorted(grupos):
        c.comparar(
            "SUBTOTAL del Detalle = fila del Resumen de Saldos al cierre",
            lectura.subtotales.get(clave, _CERO),
            al_cierre.get(clave, _CERO),
            _tolerancia(clave[1]),
            " ".join(clave),
        )
    totales = set(lectura.totales_detalle) | {k[:2] for k, v in al_cierre.items() if v and k[2] == "Total"}
    for clave in sorted(totales):
        c.comparar(
            "TOTAL INVERSIONES del Detalle = Total del Resumen de Saldos al cierre",
            lectura.totales_detalle.get(clave, _CERO),
            al_cierre.get(clave + ("Total",), _CERO),
            _tolerancia(clave[1]),
            " ".join(clave),
        )

    # Resumen de Saldos: por fila y por columna.
    filas: dict[tuple[str, str, date], dict[str, Decimal]] = defaultdict(dict)
    columnas: dict[tuple[str, str, date], list] = defaultdict(lambda: [_CERO, None])
    for (moneda, fila, segmento, fecha), valor in saldos.items():
        filas[(moneda, fila, fecha)][segmento] = valor
        if fila == "Total":
            columnas[(moneda, segmento, fecha)][1] = valor
        else:
            columnas[(moneda, segmento, fecha)][0] += valor
    for (moneda, fila, fecha), valores in filas.items():
        partes = [valores.get(s) for s in ("Previsionales", "Financieras")]
        c.comparar(
            "Resumen de Saldos: Previsionales + Financieras = Inversión Total",
            None if None in partes else sum(partes),
            valores.get("Total"),
            _tolerancia(moneda),
            f"{fila} {moneda} {fecha:%d/%m/%Y}",
        )
    for (moneda, segmento, fecha), (suma, total) in columnas.items():
        c.comparar(
            "Resumen de Saldos: suma de las filas = Total",
            suma,
            total,
            _tolerancia(moneda),
            f"{segmento} {moneda} {fecha:%d/%m/%Y}",
        )
    if not saldos:
        c.revisar("Resumen de Saldos: suma de las filas = Total", False, "no se leyó el Resumen de Saldos")

    # Resumen de Movimientos, en pesos.
    movimientos = lectura.resumen_movimientos
    for segmento in ("Previsionales", "Financieras", "Total"):
        inicial, abonos, cargos, utilidad, final = (
            movimientos.get((f, segmento))
            for f in ("saldo inicial", "abonos", "cargos", "utilidad o perdida", "saldo final")
        )
        calculado = (
            None if None in (inicial, abonos, cargos, utilidad) else inicial + abonos - cargos + utilidad
        )
        c.comparar(
            "Resumen de Movimientos: saldo inicial + abonos − cargos + utilidad = saldo final",
            calculado,
            final,
            _UNO,
            segmento,
        )
        c.comparar(
            "Resumen de Movimientos: saldo inicial = Total del Resumen de Saldos al inicio",
            inicial,
            saldos.get(("CLP", "Total", segmento, inicio)),
            _UNO,
            segmento,
        )
        c.comparar(
            "Resumen de Movimientos: saldo final = Total del Resumen de Saldos al cierre",
            final,
            saldos.get(("CLP", "Total", segmento, cierre)),
            _UNO,
            segmento,
        )

    # Movimientos: las 4 tablas de cada segmento salen siempre, aunque estén vacías.
    for segmento, tabla in product(("Previsionales", "Financieras"), ("Aportes/Compras", "Rescates/Ventas")):
        clave = (segmento, tabla)
        c.comparar(
            "Movimientos de títulos: suma de Montos en CLP = TOTAL",
            sum(lectura.montos.get(clave, []), _CERO),
            lectura.totales_titulos.get(clave),
            _UNO,
            f"{tabla} {segmento}",
        )
    for segmento, moneda in product(("Previsionales", "Financieras"), ("CLP", "USD")):
        clave = (segmento, moneda)
        que = f"{segmento} {moneda}"
        inicial = lectura.saldos_caja.get(clave, {}).get("saldo inicial")
        final = lectura.saldos_caja.get(clave, {}).get("saldo final")
        abonos, cargos = lectura.flujos.get(clave, (_CERO, _CERO))
        # Se observaron diferencias de hasta 4 pesos en una caja con 3 regímenes.
        c.comparar(
            "Cuentas de Inversiones: saldo inicial + abonos − cargos = saldo final",
            None if inicial is None else inicial + abonos - cargos,
            final,
            Decimal(5) if moneda == "CLP" else _CENTESIMO,
            que,
        )
        c.comparar(
            "Cuentas de Inversiones: saldo final = SUBTOTAL Cuenta de Inversiones del Detalle",
            final,
            lectura.subtotales.get((segmento, moneda, _CAJA), _CERO),
            _tolerancia(moneda),
            que,
        )
        for nombre, valor, fecha in (("inicial", inicial, inicio), ("final", final, cierre)):
            c.comparar(
                f"Cuentas de Inversiones: saldo {nombre} = Cuenta de inversiones del Resumen de Saldos",
                valor,
                saldos.get((moneda, _CAJA, segmento, fecha), _CERO),
                _tolerancia(moneda),
                que,
            )
    return c.controles()
