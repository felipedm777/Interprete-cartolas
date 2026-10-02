"""Informe patrimonial mensual de Larrainvial: INFORME PROVISORIO PATRIMONIAL o
CARTOLA PATRIMONIAL (la definitiva).

Páginas carta giradas 90°, que se ven apaisadas: la p.1 y la p.2 con los
resúmenes (evolución del patrimonio, clases de activo, monedas y tipos de
producto), una página "PATRIMONIO POR CLASE DE ACTIVO" por clase (CAJA, RENTA
FIJA, ALTERNATIVOS), las de MOVIMIENTOS y GARANTIAS cuando hay, y las notas
legales. El formato está descrito en docs/instituciones/larrainvial.md.

No trae número de cuenta (el encabezado dice "Cuenta: 0") ni el monto de los
movimientos de títulos.
"""

import calendar
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
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
from ..pdf import Columna, Span, armar_columnas, columna_de, leer_spans

FORMATO = "Larrainvial"

_SITIO = "www.larrainvial.com"
# Título de la p.1 -> si es el informe provisorio.
_TITULOS = {"INFORME PROVISORIO PATRIMONIAL": True, "CARTOLA PATRIMONIAL": False}
# Arriba va el encabezado con el cliente; entre medio, el título de la página
# (y≈86), y abajo, el pie con los valores de referencia (y≈574).
_Y_ENCABEZADO = 75
_Y_CONTENIDO = 98
_Y_PIE = 565

_NUMERO = re.compile(r"-?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?%?|-?\d+\.\d{2}")
_FECHA = re.compile(r"\d{2}/\d{2}/\d{4}")
_RUT = re.compile(r"\d{1,2}\.\d{3}\.\d{3}-[\dkK]")
_MOVIMIENTOS = re.compile(r"MOVIMIENTOS DE (CAJA|TITULOS) EN (\w+)")
_MONEDAS = {"PESOS": "CLP", "DOLAR": "USD", "EURO": "EUR"}
_SALDO_CAJA = {"saldo caja peso": "CLP", "saldo caja dolar": "USD", "saldo caja euro": "EUR"}

_DETALLES = ("PATRIMONIO POR CLASE DE ACTIVO", "MOVIMIENTOS", "GARANTIAS")
_COLUMNAS_POSICION = {
    "nemotecnico",
    "descripcion",
    "moneda",
    "cantidad",
    "cotizacion compra",
    "cotizacion actual",
    "monto actual ($)",
}
_COLUMNAS_MOVIMIENTO = {"fecha", "referencia", "descripcion de movimiento", "nemo", "precio ($)", "cantidad"}

# Movimientos de caja con equivalente en el vocabulario del export (el de BICE):
# (descripción sin tildes ni mayúsculas, moneda de la sección) -> tipo. El resto
# queda con la descripción en mayúsculas.
TIPOS_CAJA = {
    ("factura compra rv", "CLP"): "FACTURA COMPRA RV",
    ("pago dividendo dolar cfi", "USD"): "DIVIDENDO EN DOLARES",
    # Una venta de dólares son dos filas: el abono en pesos y el cargo en dólares.
    ("venta de dolares formal", "CLP"): "OPERACION DOLAR",
    ("venta dolares formal", "CLP"): "OPERACION DOLAR",
    ("venta de dolares formal", "USD"): "CARGO EN DOLARES",
    ("venta dolares formal", "USD"): "CARGO EN DOLARES",
    ("aporte fondo mutuo", "CLP"): "CARGO COMPROMISO DE INVERSION $ OWP",
    ("retiro fondo mutuo", "CLP"): "ABONO ORIGINADO POR PAGO RESCATES $ OWP",
    ("retiro fondo mutuo dolares", "USD"): "ABONO ORIGINADO POR PAGO RESCATE US$ OWP",
}

# Movimientos de títulos: descripción -> (tipo, archivo de destino).
TIPOS_TITULOS = {
    "aporte fondos mutuos": ("INVERSION FM", "FFMM"),
    "retiro fondo mutuo": ("RESCATE FM", "FFMM"),
    "compra rv": ("COMPRA RV", "BOLSA"),
    "ingreso rv": ("INGRESO RV", "BOLSA"),
    "retiro por disminucion de capital": ("DISMINUCION DE CAPITAL", "BOLSA"),
}

_MESES = {
    m: i
    for i, m in enumerate(
        "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
        1,
    )
}

_CERO = Decimal(0)
_UNO = Decimal(1)
_CENTESIMO = Decimal("0.01")


def paginas(doc: pymupdf.Document) -> list[int]:
    """Todas las páginas, si la primera es un informe patrimonial de Larrainvial."""
    if doc.page_count == 0:
        return []
    texto = doc[0].get_text()
    if _SITIO in texto and any(t in texto for t in _TITULOS):
        return list(range(doc.page_count))
    return []


# --- Texto ---------------------------------------------------------------------


def _norma(texto: str) -> str:
    """Sin tildes, en minúsculas y con un solo espacio: el informe omite casi
    todos los acentos, pero no todos ("Dólar", "Nemotécnico")."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def _es_numero(texto: str) -> bool:
    return bool(_NUMERO.fullmatch(texto))


def _monto(texto: str | None) -> Decimal | None:
    if not texto:
        return None
    # La definitiva de julio de 2026 trae un porcentaje con punto decimal (100.00).
    if re.fullmatch(r"-?\d+\.\d{2}%?", texto):
        return leer_monto(texto, ".")
    return leer_monto(texto)


def _redondear(valor: Decimal, moneda: str) -> Decimal:
    return valor.quantize(_UNO if moneda == "CLP" else _CENTESIMO, rounding=ROUND_HALF_UP)


def _lineas(spans: list[Span]) -> list[list[Span]]:
    """Agrupa los fragmentos en filas, de arriba abajo y de izquierda a derecha.

    El RUT anonimizado y algunos montos quedan 1 pt más arriba o más abajo que
    el resto de su fila.
    """
    lineas: list[list[Span]] = []
    for s in sorted(spans, key=lambda s: s.yc):
        if lineas and abs(lineas[-1][0].yc - s.yc) <= 3:
            lineas[-1].append(s)
        else:
            lineas.append([s])
    return [sorted(l, key=lambda s: s.x0) for l in lineas]


def _titulo(spans: list[Span]) -> str:
    grandes = [s for s in spans if _Y_ENCABEZADO < s.yc < _Y_CONTENIDO and s.tamano >= 11]
    return " ".join(s.texto for s in sorted(grandes, key=lambda s: s.x0))


def _texto(linea: list[Span]) -> str:
    return " ".join(s.texto for s in linea)


def _fecha(texto: str) -> date:
    return datetime.strptime(texto, "%d/%m/%Y").date()


# --- Extracción ------------------------------------------------------------------


@dataclass
class _Lectura:
    """Lo leído del informe, incluidos los totales que solo sirven para cuadrar."""

    cartola: Cartola
    cuenta: str
    # Tablas de la p.1 y la p.2: bloque -> rótulo de la fila -> columna -> valor.
    resumen: dict[str, dict[str, dict[str, Decimal]]] = field(default_factory=lambda: defaultdict(dict))
    # Fila "Total ..." de cada página de detalle, por sección ("caja", "renta fija"...).
    totales: dict[str, Decimal] = field(default_factory=dict)
    suma_caja: Decimal = _CERO
    # Por moneda: saldo corrido, saldo final y filas que no cuadran.
    saldo: dict[str, Decimal] = field(default_factory=dict)
    saldo_final: dict[str, Decimal] = field(default_factory=dict)
    filas_caja: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    caja_mala: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    # Movimientos de caja de fondos mutuos con precio y cantidad: (movimiento, precio × cantidad).
    caja_fm: list[tuple[MovimientoCaja, Decimal]] = field(default_factory=list)
    # Cifras de las posiciones que no van a Posicion: (posición, impreso).
    rentabilidad: list[tuple[Posicion, Decimal]] = field(default_factory=list)
    distribucion: list[tuple[Posicion, Decimal]] = field(default_factory=list)
    garantias: list[tuple[str, Decimal]] = field(default_factory=list)
    controles: list[Control] = field(default_factory=list)


def extraer(ruta: str | Path, paginas: list[int] | None = None) -> Cartola:
    doc = pymupdf.open(ruta)
    indices = paginas if paginas is not None else list(range(doc.page_count))
    hojas = [leer_spans(doc[i]) for i in indices]
    lectura = _cabecera(hojas[0], str(ruta))
    anterior = ("", "")
    for numero, spans in zip(indices, hojas):
        titulo = _titulo(spans)
        contenido = [s for s in spans if _Y_CONTENIDO <= s.yc < _Y_PIE]
        if titulo in _TITULOS:
            _resumenes(contenido, lectura)
        elif titulo in _DETALLES:
            # Una tabla larga podría seguir en otra página con el mismo título y
            # sin subtítulo; hereda el de la página anterior.
            heredado = anterior[1] if anterior[0] == titulo else ""
            anterior = (titulo, _detalle(numero + 1, titulo, contenido, lectura, heredado))
        elif titulo:
            lectura.cartola.avisos.append(f"Página {numero + 1}: sección «{titulo}» desconocida, no se leyó")
        # Sin título: las notas legales.
    _completar(lectura)
    lectura.cartola.controles = lectura.controles + _controles(lectura)
    return lectura.cartola


def _cabecera(spans: list[Span], archivo: str) -> _Lectura:
    def valor(etiqueta: str) -> list[Span]:
        e = next((s for s in spans if s.yc < _Y_ENCABEZADO and s.texto == etiqueta), None)
        if e is None:
            return []
        return sorted((s for s in spans if abs(s.yc - e.yc) <= 3 and s.x0 > e.x1), key=lambda s: s.x0)

    titulo = _titulo(spans)
    rut = valor("R.U.T. Cliente:")
    periodo = valor("Periodo:")
    m = re.fullmatch(r"(\w+) (\d{4})", periodo[0].texto) if periodo else None
    if titulo not in _TITULOS or not (rut and _RUT.fullmatch(rut[0].texto) and m and _norma(m.group(1)) in _MESES):
        raise ValueError(f"{archivo}: no se encontró el título, el RUT o el período en la p.1")
    anio, mes = int(m.group(2)), _MESES[_norma(m.group(1))]
    pie = " ".join(s.texto for s in spans if s.yc >= _Y_PIE)
    dolar = re.search(r"Dolar \$([\d.,]+)", pie)
    euro = re.search(r"Euro \$([\d.,]+)", pie)
    cuenta = valor("Cuenta:")
    cartola = Cartola(
        formato=FORMATO,
        archivo=archivo,
        rut=rut[0].texto.replace(".", "").upper(),
        # A la derecha del RUT va el nombre, que el anonimizador dejó en varios fragmentos.
        nombre=" ".join(s.texto for s in rut[1:]),
        desde=date(anio, mes, 1),
        hasta=date(anio, mes, calendar.monthrange(anio, mes)[1]),
        tipo_cambio_usd=leer_monto(dolar.group(1)) if dolar else None,
        institucion="LARRAINVIAL",
        tipo_cambio_eur=leer_monto(euro.group(1)) if euro else None,
        provisoria=_TITULOS[titulo],
    )
    numero = cuenta[0].texto if cuenta else "0"
    cartola.cuentas[numero] = Cuenta(
        numero, portafolio="", grupo="Cuenta de Inversión", producto_base="CUENTA INVERSION"
    )
    if not dolar:
        cartola.avisos.append("No se encontró el dólar de referencia del pie de página")
    if cartola.provisoria:
        cartola.avisos.append("Es un informe provisorio: los saldos pueden cambiar en la cartola definitiva")
    return _Lectura(cartola, numero)


# --- p.1 y p.2: tablas de resumen ------------------------------------------------

_BLOQUES = {
    "evolucion de patrimonio": "evolucion",
    "rentabilidad": "rentabilidad",
    "patrimonio por clase de activo": "clases",
    "patrimonio por monedas": "monedas",
    "patrimonio por tipo de producto": "productos",
}
# La evolución tiene dos tablas lado a lado: el mes, y el año anterior y el actual.
_COLUMNAS_EVOLUCION = ("mes", "anterior", "ytd")


def _resumenes(contenido: list[Span], lectura: _Lectura) -> None:
    bloque, anclas = "", {}
    for linea in _lineas(contenido):
        rotulo = _norma(linea[0].texto)
        if rotulo in _BLOQUES:
            bloque, anclas = _BLOQUES[rotulo], {}
            continue
        numeros = [s for s in linea if _es_numero(s.texto)]
        if not numeros:
            # Encabezado: los números van alineados a la derecha de su columna.
            if bloque == "evolucion":
                anclas = dict(zip(_COLUMNAS_EVOLUCION, sorted(s.x1 for s in linea)))
            else:
                anclas = {_norma(s.texto): s.x1 for s in linea}
            continue
        if bloque in ("", "rentabilidad"):
            continue
        if not anclas:
            lectura.cartola.avisos.append(f"Resumen: fila sin encabezado «{_texto(linea)}»")
            continue
        fila = lectura.resumen[bloque].setdefault(rotulo, {})
        for s in numeros:
            fila[min(anclas, key=lambda c: abs(anclas[c] - s.x1))] = _monto(s.texto)


# --- Páginas de detalle -----------------------------------------------------------


@dataclass
class _Tabla:
    subtitulo: str
    columnas: list[Columna]
    filas: list[list[Span]]

    @property
    def etiquetas(self) -> dict[str, str]:
        return {_norma(c.etiqueta): c.etiqueta for c in self.columnas}

    def celdas(self, linea: list[Span]) -> dict[str, str]:
        """Texto de cada columna de la fila; lo que queda a la izquierda de la
        primera columna (el rótulo de las filas de CAJA) va en ""."""
        x0 = min(c.x0 for c in self.columnas)
        celdas: dict[str, list[str]] = defaultdict(list)
        for s in linea:
            clave = "" if s.x1 < x0 else _norma(columna_de(s, self.columnas))
            celdas[clave].append(s.texto)
        return {k: " ".join(v) for k, v in celdas.items()}


def _detalle(numero: int, titulo: str, contenido: list[Span], lectura: _Lectura, heredado: str) -> str:
    """Lee una página de detalle y devuelve su subtítulo."""
    lineas = _lineas(contenido)
    subtitulo = heredado
    if lineas and len(lineas[0]) == 1 and lineas[0][0].x0 < 60 and lineas[0][0].texto.isupper():
        subtitulo = lineas[0][0].texto
        lineas = lineas[1:]
    encabezado = []
    for linea in lineas:
        if any(_es_numero(s.texto) or _FECHA.fullmatch(s.texto) for s in linea):
            break
        encabezado.append(linea)
    filas = lineas[len(encabezado) :]
    if not filas:
        return subtitulo  # página MOVIMIENTOS vacía o tabla sin filas
    tabla = _Tabla(subtitulo, armar_columnas([s for l in encabezado for s in l]), filas)
    nombres = set(tabla.etiquetas)
    m = _MOVIMIENTOS.fullmatch(subtitulo)
    if subtitulo == "CAJA" and {"moneda de origen", "monto ($)"} <= nombres:
        _caja(tabla, lectura)
    elif m and m.group(2) in _MONEDAS and _COLUMNAS_MOVIMIENTO <= nombres:
        if m.group(1) == "CAJA":
            _movimientos_caja(tabla, _MONEDAS[m.group(2)], lectura)
        else:
            _movimientos_titulos(tabla, _MONEDAS[m.group(2)], lectura)
    elif subtitulo == "INSTRUMENTOS EN GARANTIA" and {"nemotecnico", "cantidad en garantia"} <= nombres:
        _garantias(tabla, lectura)
    elif titulo == "PATRIMONIO POR CLASE DE ACTIVO" and subtitulo and _COLUMNAS_POSICION <= nombres:
        # Cualquier clase con las columnas de RENTA FIJA y ALTERNATIVOS.
        _posiciones(tabla, lectura)
    else:
        columnas = ", ".join(c.etiqueta for c in tabla.columnas)
        lectura.cartola.avisos.append(
            f"Página {numero}: tabla desconocida «{subtitulo or titulo}» ({columnas}), no se leyó"
        )
    return subtitulo


def _caja(tabla: _Tabla, lectura: _Lectura) -> None:
    cartola = lectura.cartola
    tc = {"USD": cartola.tipo_cambio_usd, "EUR": cartola.tipo_cambio_eur}
    for linea in tabla.filas:
        c = tabla.celdas(linea)
        rotulo = _norma(c.get("", ""))
        monto_clp = _monto(c.get("monto ($)"))
        if rotulo == "total caja":
            lectura.totales["caja"] = monto_clp
            continue
        moneda = _SALDO_CAJA.get(rotulo)
        if moneda is None or monto_clp is None:
            cartola.avisos.append(f"CAJA: fila no reconocida «{_texto(linea)}»")
            continue
        lectura.suma_caja += monto_clp
        monto = monto_clp if moneda == "CLP" else _monto(c.get("moneda de origen"))
        if monto is None:
            cartola.avisos.append(f"CAJA: «{c['']}» sin monto en moneda de origen")
            continue
        if moneda != "CLP" and tc[moneda]:
            regla = f"{c['']} × cambio de referencia = monto en pesos"
            lectura.controles.append(_comparar(regla, monto * tc[moneda], monto_clp, Decimal(5)))
        if monto:
            cartola.saldos_caja.append(SaldoCaja(lectura.cuenta, moneda, monto, monto_clp))


def _posiciones(tabla: _Tabla, lectura: _Lectura) -> None:
    cartola = lectura.cartola
    seccion = tabla.subtitulo.capitalize()
    etiquetas = tabla.etiquetas
    for linea in tabla.filas:
        c = tabla.celdas(linea)
        if _norma(linea[0].texto).startswith("total"):
            lectura.totales[_norma(seccion)] = _monto(c.get("monto actual ($)"))
            continue
        nemo, moneda = c.get("nemotecnico", ""), c.get("moneda", "")
        columnas = ("cantidad", "cotizacion compra", "cotizacion actual", "monto actual ($)")
        try:
            cantidad, compra, actual, valor, rentabilidad, distribucion = (
                _monto(c.get(k)) for k in columnas + ("rentabilidad (%)", "distribucion (%)")
            )
        except ValueError:
            cantidad = None
        if not nemo or not moneda or None in (cantidad, actual, valor):
            cartola.avisos.append(f"{seccion}: fila no reconocida «{_texto(linea)}»")
            continue
        p = Posicion(
            cuenta=lectura.cuenta,
            seccion=seccion,
            tabla="CFI" if nemo.startswith("CFI") else "Fondos Mutuos Otras AGF",
            previsional=False,
            instrumento=c.get("descripcion", nemo),
            moneda=moneda,
            cantidad=cantidad,
            precio_promedio=compra,
            precio_actual=actual,
            valor_clp=valor,
            valor_usd=cantidad * actual if moneda == "USD" else None,
            nemotecnico=nemo,
            otros={etiquetas[k]: v for k, v in c.items() if k and k not in _COLUMNAS_POSICION},
        )
        cartola.posiciones.append(p)
        if rentabilidad is not None:
            lectura.rentabilidad.append((p, rentabilidad))
        if distribucion is not None:
            lectura.distribucion.append((p, distribucion))


def _movimientos_caja(tabla: _Tabla, moneda: str, lectura: _Lectura) -> None:
    cartola = lectura.cartola
    tolerancia = _CERO if moneda == "CLP" else _CENTESIMO
    for linea in tabla.filas:
        c = tabla.celdas(linea)
        descripcion = c.get("descripcion de movimiento", "")
        saldo = _monto(c.get("saldo en caja ($)"))
        if _norma(linea[0].texto) == "saldo final":
            lectura.saldo_final[moneda] = saldo
            if moneda in lectura.saldo:
                regla = f"Movimientos de caja en {moneda}: saldo final = último saldo"
                lectura.controles.append(_comparar(regla, lectura.saldo[moneda], saldo, tolerancia))
            continue
        if _norma(descripcion) == "saldo inicial":
            lectura.saldo[moneda] = saldo
            continue
        if not _FECHA.fullmatch(c.get("fecha", "")) or saldo is None:
            cartola.avisos.append(f"Movimientos de caja en {moneda}: fila no reconocida «{_texto(linea)}»")
            continue
        cargo = _monto(c.get("cargo ($)")) or _CERO
        abono = _monto(c.get("abono ($)")) or _CERO
        anterior = lectura.saldo.get(moneda)
        lectura.filas_caja[moneda] += 1
        if anterior is None or abs(anterior + abono - cargo - saldo) > tolerancia:
            lectura.caja_mala[moneda].append(f"{c['fecha']} {descripcion}: saldo anterior {anterior}, saldo {saldo}")
        lectura.saldo[moneda] = saldo
        movimiento = MovimientoCaja(
            fecha=_fecha(c["fecha"]),
            cuenta=lectura.cuenta,
            tipo=TIPOS_CAJA.get((_norma(descripcion), moneda), descripcion.upper()),
            moneda=moneda,
            cargo=cargo,
            abono=abono,
            folio=c.get("referencia", ""),
            instrumento=c.get("nemo", ""),
        )
        cartola.movimientos_caja.append(movimiento)
        precio, cantidad = _monto(c.get("precio ($)")), _monto(c.get("cantidad"))
        if precio is not None and cantidad is not None:
            lectura.caja_fm.append((movimiento, precio * cantidad))


def _movimientos_titulos(tabla: _Tabla, moneda: str, lectura: _Lectura) -> None:
    cartola = lectura.cartola
    for linea in tabla.filas:
        c = tabla.celdas(linea)
        descripcion = c.get("descripcion de movimiento", "")
        precio, cantidad = _monto(c.get("precio ($)")), _monto(c.get("cantidad"))
        if not _FECHA.fullmatch(c.get("fecha", "")) or precio is None or cantidad is None:
            cartola.avisos.append(
                f"Movimientos de títulos en {moneda}: fila no reconocida «{_texto(linea)}»"
            )
            continue
        tipo, destino = TIPOS_TITULOS.get(_norma(descripcion), (descripcion.upper(), ""))
        if not destino:
            cartola.avisos.append(
                f"Movimiento de títulos «{descripcion}» sin equivalente en el export: va como {tipo}"
            )
        nemo = c.get("nemo", "")
        cartola.movimientos_titulos.append(
            MovimientoTitulo(
                fecha=_fecha(c["fecha"]),
                cuenta=lectura.cuenta,
                tipo=tipo,
                instrumento=nemo,
                moneda=moneda,
                cantidad=cantidad,
                precio=precio,
                monto=_redondear(precio * cantidad, moneda),
                referencia=c.get("referencia", ""),
                nemotecnico=nemo,
                destino=destino,
            )
        )


def _garantias(tabla: _Tabla, lectura: _Lectura) -> None:
    for linea in tabla.filas:
        c = tabla.celdas(linea)
        cantidad = _monto(c.get("cantidad en garantia"))
        if c.get("nemotecnico") and cantidad is not None:
            lectura.garantias.append((c["nemotecnico"], cantidad))
        else:
            lectura.cartola.avisos.append(f"Instrumentos en garantía: fila no reconocida «{_texto(linea)}»")


def _completar(lectura: _Lectura) -> None:
    """Los movimientos de títulos solo traen el nemotécnico: si el instrumento
    está entre las posiciones, se usa su descripción. Avisa además lo deducido
    sobre el monto de las compras."""
    cartola = lectura.cartola
    descripciones = {p.nemotecnico: p.instrumento for p in cartola.posiciones}
    for m in cartola.movimientos_titulos:
        m.instrumento = descripciones.get(m.nemotecnico, m.instrumento)
    if cartola.movimientos_titulos:
        cartola.avisos.append(
            "El informe no trae el monto de los movimientos de títulos: se calculó como precio × cantidad"
        )
    compras: dict[str, Decimal] = defaultdict(Decimal)
    for m in cartola.movimientos_titulos:
        if m.tipo == "COMPRA RV":
            compras[m.referencia] += m.precio * m.cantidad
    for m in cartola.movimientos_caja:
        if m.tipo != "FACTURA COMPRA RV":
            continue
        if m.folio not in compras:
            cartola.avisos.append(f"Factura compra RV {m.folio}: no hay compras de títulos con esa referencia")
            continue
        suma = _redondear(compras[m.folio], m.moneda)
        diferencia = m.cargo - suma
        if not suma:
            continue
        cartola.avisos.append(
            f"Factura compra RV {m.folio}: {m.cargo} en caja y {suma} en las compras de títulos "
            f"(precio × cantidad); la diferencia de {diferencia} "
            f"({diferencia / suma * 100:.2f} %) son los costos de la compra"
        )


# --- Cuadraturas -------------------------------------------------------------------


def _comparar(regla: str, calculado: Decimal | None, impreso: Decimal | None, tolerancia: Decimal) -> Control:
    if calculado is None or impreso is None:
        return Control(regla, False, "no se encontró el valor impreso")
    diferencia = calculado - impreso
    detalle = "" if diferencia == 0 else f"calculado {calculado}, impreso {impreso}, diferencia {diferencia}"
    return Control(regla, abs(diferencia) <= tolerancia, detalle)


def _por_fila(regla: str, malas: list[str], revisadas: int) -> list[Control]:
    if not revisadas:
        return []
    return [Control(f"{regla} ({revisadas})", not malas, "; ".join(malas))]


def _dv_valido(rut: str) -> bool:
    cuerpo, dv = rut.split("-")
    suma = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    esperado = {10: "K", 11: "0"}.get(11 - suma % 11, str(11 - suma % 11))
    return dv == esperado


def _controles(lectura: _Lectura) -> list[Control]:
    cartola, resumen = lectura.cartola, lectura.resumen
    tc = {"USD": cartola.tipo_cambio_usd, "EUR": cartola.tipo_cambio_eur}
    controles = [Control("RUT con dígito verificador válido", _dv_valido(cartola.rut), cartola.rut)]

    # Evolución del patrimonio, en las 3 columnas.
    evolucion = resumen.get("evolucion", {})
    filas = ("patrimonio inicio periodo", "aportes", "retiros", "cambio valor cartera", "patrimonio fin del periodo")
    for columna, nombre in zip(_COLUMNAS_EVOLUCION, ("del mes", "del año anterior", "del año actual")):
        valores = [evolucion.get(f, {}).get(columna) for f in filas]
        calculado = None if None in valores[:4] else sum(valores[:4])
        regla = f"Evolución {nombre}: inicio + aportes + retiros + cambio de valor = fin"
        controles.append(_comparar(regla, calculado, valores[4], _UNO))
    fin = evolucion.get("patrimonio fin del periodo", {})
    controles.append(_comparar("Patrimonio fin del mes = fin del año actual", fin.get("mes"), fin.get("ytd"), _CERO))
    patrimonio = fin.get("mes")
    inicio = evolucion.get("patrimonio inicio periodo", {}).get("mes")
    if patrimonio is not None and inicio is not None:
        cartola.totales["patrimonio_inicio"] = inicio
        cartola.totales["patrimonio_fin"] = patrimonio

    # Clases de activo, monedas y tipos de producto contra el patrimonio.
    clases = dict(resumen.get("clases", {}))
    total_clases = clases.pop("patrimonio fin del periodo", {})
    controles.append(
        _comparar(
            "Suma de clases de activo = patrimonio fin (p.1)",
            sum((v.get("monto ($)", _CERO) for v in clases.values()), _CERO),
            total_clases.get("monto ($)"),
            _UNO,
        )
    )
    # Cada porcentaje viene redondeado a 2 decimales.
    controles.append(
        _comparar(
            "Suma de la distribución de clases de activo = 100 %",
            sum((v.get("distribucion (%)", _CERO) for v in clases.values()), _CERO),
            total_clases.get("distribucion (%)", Decimal(100)),
            max(_CENTESIMO, Decimal("0.005") * len(clases)),
        )
    )
    monedas = dict(resumen.get("monedas", {}))
    total_monedas = monedas.pop("total", {}).get("en pesos ($)")
    productos = dict(resumen.get("productos", {}))
    total_productos = productos.pop("patrimonio fin del periodo", {}).get("monto ($)")
    for nombre, valor in (
        ("de la evolución", patrimonio),
        ("por monedas", total_monedas),
        ("por tipo de producto", total_productos),
    ):
        regla = f"Patrimonio fin por clase de activo = patrimonio fin {nombre}"
        controles.append(_comparar(regla, total_clases.get("monto ($)"), valor, _UNO))
    controles.append(
        _comparar(
            "Suma por monedas = total por monedas",
            sum((v.get("en pesos ($)", _CERO) for v in monedas.values()), _CERO),
            total_monedas,
            _UNO,
        )
    )
    controles.append(
        _comparar(
            "Suma por tipo de producto = patrimonio fin por tipo de producto",
            sum((v.get("monto ($)", _CERO) for v in productos.values()), _CERO),
            total_productos,
            _UNO,
        )
    )

    # Por moneda: posiciones y caja contra "Patrimonio por monedas".
    por_moneda: dict[str, dict[str, Decimal]] = {}
    for rotulo, valores in monedas.items():
        m = re.search(r"\((usd|eur)\)", rotulo)
        por_moneda[m.group(1).upper() if m else "CLP"] = valores
    presentes = {p.moneda if p.moneda in tc else "CLP" for p in cartola.posiciones}
    presentes |= {s.moneda for s in cartola.saldos_caja} | set(por_moneda)
    for moneda in sorted(presentes):
        impreso = por_moneda.get(moneda, {})
        if moneda == "CLP":
            calculado = sum((p.valor_clp for p in cartola.posiciones if p.moneda not in tc), _CERO)
            calculado += sum((s.monto for s in cartola.saldos_caja if s.moneda == "CLP"), _CERO)
            regla = "Peso ($) y UF = posiciones y caja en pesos"
            controles.append(_comparar(regla, calculado, impreso.get("en pesos ($)", _CERO), _CERO))
            continue
        calculado = sum((p.cantidad * p.precio_actual for p in cartola.posiciones if p.moneda == moneda), _CERO)
        calculado += sum((s.monto for s in cartola.saldos_caja if s.moneda == moneda), _CERO)
        controles.append(
            _comparar(
                f"Monto en {moneda} = cantidad × cotización de las posiciones + caja en {moneda}",
                calculado,
                impreso.get("monto", _CERO),
                Decimal("0.005"),
            )
        )
        if tc[moneda] and "monto" in impreso:
            controles.append(
                _comparar(
                    f"Monto en {moneda} × cambio de referencia = en pesos",
                    impreso["monto"] * tc[moneda],
                    impreso.get("en pesos ($)"),
                    Decimal(5),
                )
            )

    # Caja.
    total_caja = lectura.totales.get("caja")
    controles.append(_comparar("Suma de líneas de CAJA = Total caja", lectura.suma_caja, total_caja, _CERO))
    caja_p1 = clases.get("caja", {}).get("monto ($)", _CERO)
    controles.append(_comparar("Total caja = Caja de la p.1", total_caja, caja_p1, _CERO))

    # Posiciones.
    malas, revisadas = [], 0
    for p in cartola.posiciones:
        cambio = tc[p.moneda] if p.moneda in tc else _UNO
        if cambio is None:
            continue
        revisadas += 1
        calculado = p.cantidad * p.precio_actual * cambio
        if abs(calculado - p.valor_clp) > Decimal("0.5"):
            malas.append(f"{p.nemotecnico}: {calculado:.2f} vs {p.valor_clp}")
    controles += _por_fila("Cantidad × cotización actual × cambio = monto actual en pesos", malas, revisadas)
    secciones: dict[str, list[Decimal]] = defaultdict(list)
    for p in cartola.posiciones:
        secciones[_norma(p.seccion)].append(p.valor_clp)
    for seccion in sorted(set(secciones) | {k for k in lectura.totales if k != "caja"}):
        suma = sum(secciones.get(seccion, []), _CERO)
        total = lectura.totales.get(seccion)
        controles.append(_comparar(f"Suma de posiciones = Total {seccion}", suma, total, _UNO))
        clase = clases.get(seccion, {}).get("monto ($)")
        controles.append(_comparar(f"Total {seccion} = fila de la clase en la p.1", total, clase, _UNO))
    for seccion in sorted(set(clases) - set(secciones) - {"caja"}):
        controles.append(
            Control(f"Clase {seccion} de la p.1 con posiciones", False, "la clase no tiene página de detalle")
        )
    malas = [
        f"{p.nemotecnico}: {(p.precio_actual / p.precio_promedio - 1) * 100:.4f} vs {impreso}"
        for p, impreso in lectura.rentabilidad
        if not p.precio_promedio or abs((p.precio_actual / p.precio_promedio - 1) * 100 - impreso) > _CENTESIMO
    ]
    regla = "Rentabilidad = (cotización actual / compra − 1) × 100"
    controles += _por_fila(regla, malas, len(lectura.rentabilidad))
    if patrimonio:
        malas = [
            f"{p.nemotecnico}: {p.valor_clp / patrimonio * 100:.4f} vs {impreso}"
            for p, impreso in lectura.distribucion
            if abs(p.valor_clp / patrimonio * 100 - impreso) > _CENTESIMO
        ]
        regla = "Distribución de la posición = monto / patrimonio × 100"
        controles += _por_fila(regla, malas, len(lectura.distribucion))
    for nombre, es_fi in (("fondos de inversion", True), ("fondos mutuos", False)):
        suma = sum((p.valor_clp for p in cartola.posiciones if p.nemotecnico.startswith("CFI") == es_fi), _CERO)
        impreso = productos.get(nombre, {}).get("monto ($)", _CERO)
        controles.append(_comparar(f"Posiciones = {nombre} por tipo de producto", suma, impreso, _UNO))
    for rotulo in sorted(set(productos) - {"caja", "fondos de inversion", "fondos mutuos"}):
        cartola.avisos.append(f"Patrimonio por tipo de producto: «{rotulo}» no se cuadra con las posiciones")

    # Movimientos de caja.
    for moneda, filas_caja in lectura.filas_caja.items():
        regla = f"Movimientos de caja en {moneda}: saldo anterior + abono − cargo = saldo"
        controles += _por_fila(regla, lectura.caja_mala[moneda], filas_caja)
    for moneda, final in lectura.saldo_final.items():
        caja = sum((s.monto for s in cartola.saldos_caja if s.moneda == moneda), _CERO)
        regla = f"Saldo final de los movimientos en {moneda} = Saldo Caja de CAJA"
        controles.append(_comparar(regla, final, caja, _CERO))
    malas = [
        f"{m.fecha} {m.instrumento}: {calculado} vs {m.cargo or m.abono}"
        for m, calculado in lectura.caja_fm
        if abs(calculado - (m.cargo or m.abono)) > abs(m.cargo or m.abono) * Decimal("2e-6")
    ]
    regla = "Movimientos de caja con precio: precio × cantidad = cargo o abono"
    controles += _por_fila(regla, malas, len(lectura.caja_fm))

    # Caja frente a títulos: los fondos mutuos por referencia y las disminuciones
    # de capital por fecha y nemotécnico (en títulos traen referencia 0).
    caja_por_referencia = {(m.folio, m.moneda): m for m in cartola.movimientos_caja}
    malas, revisadas = [], 0
    for t in cartola.movimientos_titulos:
        calculado = t.precio * t.cantidad
        if t.destino == "FFMM":
            m = caja_por_referencia.get((t.referencia, t.moneda))
            tolerancia = None if m is None else abs(m.cargo or m.abono) * Decimal("2e-6")
        elif t.tipo == "DISMINUCION DE CAPITAL":
            m = next(
                (
                    m
                    for m in cartola.movimientos_caja
                    if (m.fecha, m.instrumento, m.moneda) == (t.fecha, t.nemotecnico, t.moneda) and m.abono
                ),
                None,
            )
            tolerancia = Decimal("0.5") if t.moneda == "CLP" else Decimal("0.005")
        else:
            continue
        revisadas += 1
        if m is None:
            malas.append(f"{t.fecha} {t.tipo} {t.nemotecnico}: sin movimiento de caja")
        elif abs(calculado - (m.cargo or m.abono)) > tolerancia:
            malas.append(f"{t.fecha} {t.tipo} {t.nemotecnico}: {calculado} vs {m.cargo or m.abono}")
    controles += _por_fila("Movimientos de títulos: precio × cantidad = cargo o abono de caja", malas, revisadas)

    # Las garantías repiten una posición: deben estar entre las posiciones.
    cantidades = defaultdict(Decimal)
    for p in cartola.posiciones:
        cantidades[p.nemotecnico] += p.cantidad or _CERO
    malas = [
        f"{nemo}: {cantidad} en garantía y {cantidades[nemo]} en cartera"
        for nemo, cantidad in lectura.garantias
        if cantidades[nemo] < cantidad
    ]
    controles += _por_fila("Instrumentos en garantía incluidos en las posiciones", malas, len(lectura.garantias))
    return controles
