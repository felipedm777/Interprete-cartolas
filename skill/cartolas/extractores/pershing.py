"""Estado de cuenta de Pershing LLC (BNY Pershing) en español: la custodia
internacional que se contrata a través de BICE Inversiones o de Sura.

Páginas carta apaisadas con la misma plantilla en ambos corredores, pero con
distinta configuración: columnas del año, orden de las secciones, bloques por
moneda y transacciones ordenadas por fecha o por tipo de actividad. La p.1 trae
el titular, el período, el número de cuenta y los resúmenes de la cartera y de
activos; después vienen las tenencias (por moneda, categoría y título, con una
fila por lote), el resumen de actividad, las transacciones, el detalle del
fondo money market donde se barre la caja, el resumen de ingresos y gastos y
las notas legales. El formato está descrito en docs/instituciones/pershing.md.

No trae RUT ni tipo de cambio a pesos, y los números vienen en formato de
EE.UU. (-$1,234.56).
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pymupdf

from ..modelo import Cartola, Control, Cuenta, MovimientoTitulo, Posicion, SaldoCaja
from ..pdf import Columna, Span, armar_columnas, leer_spans

FORMATO = "Pershing"

_MARCA = "Pershing LLC"
# Arriba de la p.1 van el titular con su dirección, el período y la cuenta; al
# pie de cada página, el número de página, la cuenta y el código del documento.
_Y_CABECERA = 188
_Y_PIE = 565
# Los superíndices de las notas miden 5,3 pt; los encabezados de columna, 7,8;
# el texto, 9; la moneda y los totales mayores, 10, y los títulos de sección, 11.
_TAM_MINIMO = 6
_TAM_ENCABEZADO = 8.5
_TAM_SUBTITULO = 9.8
_TAM_TITULO = 10.5

_PERIODO = re.compile(r"(\d{1,2}) de (\w+) de (\d{4}) - (\d{1,2}) de (\w+) de (\d{4})")
_NUMERO = re.compile(r"-?\$?\d{1,3}(,\d{3})*(\.\d+)?%?")
_FECHA = re.compile(r"\d{2}/\d{2}/\d{2}")
_DIVISA = re.compile(r"[A-Z]{3}")
_NO_DISPONIBLE = "No disponible"
_CONTINUACION = re.compile(r"\s*\(continuación\s*\)")
_SUFIJO_CATEGORIA = re.compile(r"\s*(-?[\d.,]+% de Cartera.*|\(.*\))$")
_ISIN = re.compile(r"\s*ISIN#(\S+)$")
_CODIGO = "Código de Identificación de Títulos:"
_CUSIP = "CUSIP:"
_ATRIBUTOS = ("Opción de", "Base de Costo Original:", "Precio estimado partir de:")

# Título de sección -> lector. Las demás secciones son texto legal o informativo.
_SECCIONES = {
    "Resumen de la Cartera": "cartera",
    "Resumen de Activos": "activos",
    "Tenencias en Cartera": "tenencias",
    "Resumen de tenencias por divisa": "divisas",
    "Tabla de Tipos de Cambio": "cambio",
    "Resumen de Actividad": "actividad",
    "Transacciones Ordenadas por Fecha": "transacciones",
    "Transacciones por Tipo de Actividad": "transacciones",
    "Detalles del Fondo de Money Market": "money_market",
    "Resumen de Ingresos y Gastos": "ingresos",
}
_INFORMATIVAS = {
    "Divulgación y Notas al pie sobre Resumen de Activos",
    "Divulgaciones de tenencias de cartera",
    "Información de Atención a Clientes",
    "Información de su cuenta",
    "Mensajes",
    "Declaraciones e información importantes",
}

# Categoría de las tenencias -> tabla de la posición. El efectivo es el fondo
# money market del sweep, que va a los saldos de caja.
_EFECTIVO = "Efectivo, Fondos de Dinero y Depósitos Bancarios"
_CATEGORIAS = {
    _EFECTIVO: "Money Market",
    "Acciones": "Acciones",
    "Productos Negociados en Bolsa": "ETF",
    "Títulos de deuda/ingresos fijos": "Bonos",
}
_PRODUCTOS = {"Acciones": "ACCIONES", "ETF": "ETF", "Money Market": "MONEY MARKET", "Bonos": "BONOS"}
# Subtítulo de moneda de las tenencias -> código. "Resumen de tenencias por
# divisa" agrega los que trae cada estado ("BRITISH POUND (GBP)").
_MONEDAS = {"U.S. DOLLARS": "USD", "BRITISH POUND": "GBP"}

# Encabezado de columna (sin tildes y en minúsculas) -> clave.
_CLAVES = {
    "fecha de adquisicion": "fecha",
    "fecha inicial": "fecha",
    "fecha de proces. o liquid.": "fecha",
    "costo por unidad": "costo_unitario",
    "base de costo actual": "costo",
    "precio de mercado": "precio",
    "valor de mercado": "valor",
    "ganancia o perdida no realizada": "gp",
    "intereses devengado": "interes",
    "intereses devengados": "interes",
    "intereses acumulados": "interes",
    "ingresos anuales estimados": "eai",
    "redito estimado": "redito",
    "redito estim.": "redito",
    "numero de cuenta": "numero_cuenta",
    "actividades finalizando el": "finalizando",
    "saldo de apertura": "apertura",
    "saldo al cierre": "cierre",
    # En el money market de las tenencias: no suman a los intereses de la cuenta.
    "ingresos devengados": "devengado",
    # Los totales de la cuenta suman los ingresos del año del money market a los
    # ingresos anuales estimados de los títulos.
    "ingresos en este ano": "eai",
    "redito a 30 dias": "redito_30",
    "redito actual": "redito",
    "tipo de actividad": "tipo",
    "equivalente en usd": "equivalente",
    "unidades por usd": "unidades",
}
_NUMERICAS = {
    "cantidad", "costo_unitario", "costo", "precio", "valor", "gp", "interes", "eai", "redito",
    "apertura", "cierre", "devengado", "redito_30", "monto", "saldo", "equivalente", "unidades",
}  # fmt: skip
# Columnas que los totales de las tenencias suman.
_MEDIDAS = ("cantidad", "costo", "valor", "gp", "interes", "eai", "apertura", "cierre", "devengado")
_NOMBRES_MEDIDAS = {
    "cantidad": "cantidad",
    "costo": "base de costo",
    "valor": "valor de mercado",
    "gp": "ganancia o pérdida",
    "interes": "intereses",
    "eai": "ingresos anuales estimados",
    "apertura": "saldo de apertura",
    "cierre": "saldo al cierre",
    "devengado": "ingresos devengados",
}
_COLUMNAS_INGRESOS = ("gravable", "no_gravable", "gravable_anio", "no_gravable_anio")
_NOMBRES_COLUMNAS = {
    "creditos": "créditos del período",
    "debitos": "débitos del período",
    "neto": "neto del período",
    "creditos_anio": "créditos del año",
    "debitos_anio": "débitos del año",
    "neto_anio": "neto del año",
    "gravable": "gravable del período",
    "no_gravable": "no gravable del período",
    "gravable_anio": "gravable del año",
    "no_gravable_anio": "no gravable del año",
}

_MESES = {
    m: i
    for i, m in enumerate(
        "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
        1,
    )
} | {"setiembre": 9}

_CERO = Decimal(0)
_CENTESIMO = Decimal("0.01")


def paginas(doc: pymupdf.Document) -> list[int]:
    """Todas las páginas, si la primera es la de un estado de cuenta Pershing.

    El pie "Clearing through Pershing LLC" es una imagen; en el texto queda
    "Pershing LLC" en las declaraciones del final.
    """
    if doc.page_count == 0:
        return []
    portada = doc[0].get_text()
    if not (
        "Número de Cuenta:" in portada
        and "Resumen de la Cartera" in portada
        and "VALOR INICIAL DE LA CUENTA" in portada
        and _PERIODO.search(portada)
    ):
        return []
    if not any(_MARCA in pagina.get_text() for pagina in doc):
        return []
    return list(range(doc.page_count))


# --- Texto y números --------------------------------------------------------------


def _norma(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def _es_valor(texto: str) -> bool:
    return bool(_NUMERO.fullmatch(texto) or _FECHA.fullmatch(texto)) or texto == _NO_DISPONIBLE


def _monto(texto: str | None) -> Decimal | None:
    """Número en formato de EE.UU. (-$1,234.56, 1.50%); None si viene vacío o "No disponible"."""
    if not texto or texto == _NO_DISPONIBLE:
        return None
    if not _NUMERO.fullmatch(texto):
        raise ValueError(f"número no reconocido: {texto!r}")
    return Decimal(re.sub(r"[$,%]", "", texto))


def _fecha(texto: str) -> date:
    return datetime.strptime(texto, "%m/%d/%y").date()


@dataclass
class _Linea:
    spans: list[Span]

    @property
    def texto(self) -> str:
        return " ".join(s.texto for s in self.spans)

    @property
    def rotulo(self) -> str:
        """El texto que no es un valor ni un código de moneda, sin "(continuación)"."""
        texto = " ".join(s.texto for s in self.spans if not (_es_valor(s.texto) or _DIVISA.fullmatch(s.texto)))
        return _CONTINUACION.sub("", texto).strip()

    @property
    def encabezado(self) -> bool:
        return all(s.tamano < _TAM_ENCABEZADO for s in self.spans)

    @property
    def continuacion(self) -> bool:
        return "(continuación" in self.texto

    def valores(self) -> list[Span]:
        return [s for s in self.spans if _es_valor(s.texto)]

    def empieza_con_fecha(self) -> bool:
        primero = self.spans[0]
        return primero.x0 < 100 and bool(_FECHA.fullmatch(primero.texto))


def _lineas(spans: list[Span]) -> list[_Linea]:
    """Agrupa los fragmentos en filas. En Sura el tipo de actividad de las
    transacciones queda 1 pt más abajo que el resto de su fila."""
    lineas: list[list[Span]] = []
    for s in sorted(spans, key=lambda s: s.yc):
        if lineas and abs(lineas[-1][0].yc - s.yc) <= 3:
            lineas[-1].append(s)
        else:
            lineas.append([s])
    return [_Linea(sorted(l, key=lambda s: s.x0)) for l in lineas]


def _clave(etiqueta: str) -> str:
    return _CLAVES.get(_norma(etiqueta), _norma(etiqueta))


def _celdas(linea: _Linea, columnas: list[Columna]) -> dict[str, str]:
    """Texto de cada columna de la fila. Los valores van alineados a la derecha
    y se asignan por el borde derecho del encabezado; el texto, por solape. Lo
    que no cae bajo ninguna columna de texto (rótulos, nombres) queda en ""."""
    celdas: dict[str, list[str]] = defaultdict(list)
    for s in linea.spans:
        if _es_valor(s.texto):
            clave = _clave(min(columnas, key=lambda c: abs(c.x1 - s.x1)).etiqueta)
        else:
            c = max(columnas, key=lambda c: min(s.x1, c.x1) - max(s.x0, c.x0))
            clave = _clave(c.etiqueta) if min(s.x1, c.x1) > max(s.x0, c.x0) else ""
            if clave in _NUMERICAS:
                clave = ""
        celdas[clave].append(s.texto)
    return {k: " ".join(v) for k, v in celdas.items()}


def _fila(celdas: dict[str, str]) -> dict:
    return {k: _monto(v) if k in _NUMERICAS else v for k, v in celdas.items()}


class _Tabla:
    """Columnas de una tabla, armadas con su encabezado de 1 a 3 líneas. Las
    tablas que cruzan de página repiten el encabezado."""

    def __init__(self) -> None:
        self.columnas: list[Columna] = []
        self._pendiente: list[Span] = []

    def leer(self, linea: _Linea) -> bool:
        """True si la línea es parte de un encabezado."""
        if linea.encabezado:
            self._pendiente += linea.spans
            return True
        if self._pendiente:
            self.columnas, self._pendiente = armar_columnas(self._pendiente), []
        return False

    def fila(self, linea: _Linea) -> dict:
        return _fila(_celdas(linea, self.columnas))


# --- Extracción ------------------------------------------------------------------


@dataclass
class _Titulo:
    """Un título de las tenencias con sus lotes; el money market tiene una sola fila."""

    nombre: str
    moneda: str
    bloque: str
    categoria: str
    subcategoria: str
    ticker: str = ""
    cusip: str = ""
    lotes: list[dict] = field(default_factory=list)
    total: dict | None = None
    # Equivalente en USD de una posición en otra moneda (la línea de abajo).
    usd: dict = field(default_factory=dict)
    detalle: list[str] = field(default_factory=list)
    otros: dict[str, str] = field(default_factory=dict)

    @property
    def tabla(self) -> str:
        if self.categoria == _EFECTIVO and not any("cierre" in l for l in self.lotes):
            return ""
        return _CATEGORIAS.get(self.categoria, self.categoria)

    def medida(self, clave: str, en_usd: bool) -> Decimal | None:
        """La fila Total del título si la hay; si no, la suma de los lotes."""
        if en_usd and self.moneda != "USD":
            return self.usd.get(clave)
        if self.total and self.total.get(clave) is not None:
            return self.total[clave]
        valores = [l[clave] for l in self.lotes if l.get(clave) is not None]
        return sum(valores, _CERO) if valores else None


@dataclass
class _Total:
    """Fila "Total de ..." de las tenencias, con su 2.ª línea si la tiene
    (cantidad nominal o equivalente en USD)."""

    rotulo: str
    moneda: str
    bloque: str | None
    categoria: str | None
    subcategoria: str | None
    filas: list[dict]

    def incluye(self, t: _Titulo) -> bool:
        return all(
            v is None or v == getattr(t, k)
            for k, v in (("bloque", self.bloque), ("categoria", self.categoria), ("subcategoria", self.subcategoria))
        )


@dataclass
class _Transaccion:
    movimiento: MovimientoTitulo
    grupo: str
    descripcion: str
    interes: Decimal | None
    identificador: str = ""


@dataclass
class _Fondo:
    """Un fondo de los Detalles del Fondo de Money Market."""

    nombre: str
    saldo: Decimal | None = None
    cierre: Decimal | None = None


@dataclass
class _Lectura:
    """Lo leído del estado, incluidos los resúmenes que solo sirven para cuadrar."""

    cartola: Cartola
    cuenta: str
    # Resumen de la Cartera: (rótulo, {"periodo", "anio"}), en orden.
    cartera: list[tuple[str, dict[str, Decimal]]] = field(default_factory=list)
    activos: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    titulos: list[_Titulo] = field(default_factory=list)
    totales: list[_Total] = field(default_factory=list)
    total_tenencias: dict = field(default_factory=dict)
    monedas: dict[str, str] = field(default_factory=lambda: dict(_MONEDAS))
    divisas: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    # Equivalente en USD de una unidad de cada moneda, y la fecha de la tabla.
    cambio: dict[str, Decimal] = field(default_factory=dict)
    fecha_cambio: str = ""
    actividad: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    transacciones: list[_Transaccion] = field(default_factory=list)
    total_transacciones: dict[str, dict] = field(default_factory=dict)
    fondos: list[_Fondo] = field(default_factory=list)
    total_fondos: Decimal | None = None
    ingresos: dict[str, dict[str, Decimal]] = field(default_factory=dict)
    controles: list[Control] = field(default_factory=list)

    def aviso(self, texto: str) -> None:
        if texto not in self.cartola.avisos:
            self.cartola.avisos.append(texto)


def extraer(ruta: str | Path, paginas: list[int] | None = None) -> Cartola:
    doc = pymupdf.open(ruta)
    indices = paginas if paginas is not None else list(range(doc.page_count))
    lectura: _Lectura | None = None
    secciones: dict[str, list[_Linea]] = defaultdict(list)
    vistas: list[str] = []
    seccion = ""
    for i in indices:
        spans = [s for s in leer_spans(doc[i], blancos=True) if s.tamano >= _TAM_MINIMO]
        pie = [s for s in spans if s.yc >= _Y_PIE]
        spans = [s for s in spans if s.yc < _Y_PIE]
        if lectura is None:
            lectura = _cabecera([s for s in spans if s.yc < _Y_CABECERA], str(ruta))
            spans = [s for s in spans if s.yc >= _Y_CABECERA]
        else:
            _revisar_pie(pie, i + 1, lectura)
            spans = _sin_encabezado(spans)
        for linea in _lineas(spans):
            primero = linea.spans[0]
            if primero.tamano >= _TAM_TITULO and (primero.x0 < 60 or primero.texto in _SECCIONES):
                seccion = _CONTINUACION.sub("", primero.texto).strip()
                if seccion not in vistas:
                    vistas.append(seccion)
            elif seccion in _SECCIONES:
                secciones[_SECCIONES[seccion]].append(linea)
    if lectura is None:
        raise ValueError(f"{ruta}: sin páginas")
    for titulo in vistas:
        if titulo not in _SECCIONES and titulo not in _INFORMATIVAS:
            lectura.aviso(f"Sección «{titulo}» desconocida: no se leyó")
    for nivel, titulo, pagina in doc.get_toc():
        if nivel > 1 and pagina - 1 in indices and titulo.strip() not in vistas:
            lectura.aviso(f"La sección «{titulo}» del índice del PDF no se encontró en sus páginas")
    for nombre, lector in _LECTORES:
        if secciones.get(nombre):
            lector(secciones[nombre], lectura)
    _posiciones(lectura)
    _completar_movimientos(lectura)
    lectura.cartola.controles = lectura.controles + _controles(lectura)
    return lectura.cartola


def _cabecera(spans: list[Span], archivo: str) -> _Lectura:
    periodo = next((m for s in spans if (m := _PERIODO.fullmatch(s.texto))), None)
    cuenta = _a_la_derecha(spans, "Número de Cuenta:")
    if periodo is None or not cuenta or _norma(periodo.group(2)) not in _MESES or _norma(periodo.group(5)) not in _MESES:
        raise ValueError(f"{archivo}: no se encontró el período o el número de cuenta en la p.1")
    d1, m1, a1, d2, m2, a2 = periodo.groups()
    # A la izquierda va el titular en una o más líneas y después la dirección,
    # que empieza con la calle y su número.
    bloque = [l.texto for l in _lineas([s for s in spans if s.x1 < 400])]
    nombre = bloque[:1]
    for texto in bloque[1 : max(1, len(bloque) - 3)]:
        if any(c.isdigit() for c in texto):
            break
        nombre.append(texto)
    cartola = Cartola(
        formato=FORMATO,
        archivo=archivo,
        rut="",
        nombre=" ".join(nombre),
        desde=date(int(a1), _MESES[_norma(m1)], int(d1)),
        hasta=date(int(a2), _MESES[_norma(m2)], int(d2)),
        tipo_cambio_usd=None,
        institucion="PERSHING",
    )
    cartola.cuentas[cuenta] = Cuenta(cuenta, portafolio="", grupo="Pershing", producto_base="CUENTA INVERSION")
    cartola.avisos.append("El estado Pershing no trae RUT: RutCliente queda vacío")
    return _Lectura(cartola, cuenta)


def _a_la_derecha(spans: list[Span], etiqueta: str) -> str:
    e = next((s for s in spans if s.texto == etiqueta), None)
    if e is None:
        return ""
    derecha = sorted((s for s in spans if abs(s.yc - e.yc) < 3 and s.x0 >= e.x1 - 1), key=lambda s: s.x0)
    return derecha[0].texto if derecha else ""


def _revisar_pie(pie: list[Span], numero: int, lectura: _Lectura) -> None:
    cuenta = _a_la_derecha(pie, "Número de Cuenta:")
    if cuenta and cuenta != lectura.cuenta:
        lectura.aviso(f"Página {numero}: el pie trae otro número de cuenta que la p.1")


def _sin_encabezado(spans: list[Span]) -> list[Span]:
    """Quita el encabezado de las páginas impares: el período y, abajo, el titular."""
    periodo = next((s for s in spans if s.yc < 100 and _PERIODO.fullmatch(s.texto)), None)
    if periodo is None:
        return spans
    return [s for s in spans if s.yc > periodo.yc + 20]


# --- Resúmenes ----------------------------------------------------------------------


def _anclas(linea: _Linea, nombres: dict[str, str]) -> dict[str, float]:
    """Borde derecho de cada columna del encabezado: {clave: x1} para los textos de ``nombres``."""
    return {nombres[s.texto]: s.x1 for s in linea.spans if s.texto in nombres}


def _por_ancla(valores: list[Span], anclas: dict[str, float]) -> dict[str, Decimal]:
    return {min(anclas, key=lambda c: abs(anclas[c] - s.x1)): _monto(s.texto) for s in valores}


def _cartera(lineas: list[_Linea], lectura: _Lectura) -> None:
    anclas: dict[str, float] = {}
    for linea in lineas:
        # A la izquierda, a la altura del valor inicial, va el ejecutivo (BICE).
        linea = _Linea([s for s in linea.spans if s.x0 >= 400])
        if not linea.spans:
            continue
        if linea.encabezado:
            anclas = _anclas(linea, {"Este Período": "periodo", "Año hasta la Fecha": "anio"})
            continue
        valores = linea.valores()
        if valores and anclas:
            lectura.cartera.append((linea.rotulo, _por_ancla(valores, anclas)))


def _activos(lineas: list[_Linea], lectura: _Lectura) -> None:
    anclas: dict[str, float] = {}
    for linea in lineas:
        if linea.encabezado:
            anclas = _anclas(linea, {"Período Anterior": "anterior", "Período Actual": "actual"})
            continue
        # A la izquierda va el porcentaje de la clase.
        valores = [s for s in linea.valores() if not s.texto.endswith("%")]
        if valores and anclas:
            lectura.activos[linea.rotulo] = _por_ancla(valores, anclas)


def _divisas(lineas: list[_Linea], lectura: _Lectura) -> None:
    anclas: dict[str, float] = {}
    for linea in lineas:
        if linea.encabezado:
            for s in linea.spans:
                if m := re.fullmatch(r"(.+) \(([A-Z]{3})\)", s.texto):
                    anclas[m.group(2)] = s.x1
                    lectura.monedas[m.group(1).upper()] = m.group(2)
            continue
        # La etiqueta del efectivo ocupa 2 líneas; el monto va en la primera.
        valores = linea.valores()
        if valores and anclas:
            lectura.divisas[linea.rotulo] = _por_ancla(valores, anclas)


def _cambio(lineas: list[_Linea], lectura: _Lectura) -> None:
    tabla = _Tabla()
    for linea in lineas:
        if tabla.leer(linea):
            continue
        if not linea.valores():
            if m := re.search(r"al (\d{2}/\d{2}/\d{4})", linea.texto):
                lectura.fecha_cambio = m.group(1)
            continue
        fila = tabla.fila(linea)
        if fila.get("equivalente") is None:
            lectura.aviso(f"Tabla de Tipos de Cambio: fila no reconocida «{linea.texto}»")
            continue
        nombre = fila.get("divisa", linea.rotulo).upper()
        lectura.cambio[lectura.monedas.get(nombre, nombre)] = fila["equivalente"]


def _actividad(lineas: list[_Linea], lectura: _Lectura) -> None:
    anclas: dict[str, float] = {}
    for linea in lineas:
        if linea.encabezado:
            anclas = {}
            for s in linea.spans:
                t = _norma(s.texto)
                tipo = next((x for x in ("creditos", "debitos", "neto") if t.startswith(x)), None)
                if tipo:
                    anclas[tipo + ("_anio" if t.endswith("este ano") else "")] = s.x1
            continue
        valores = linea.valores()
        if valores and anclas:
            lectura.actividad[linea.rotulo] = _por_ancla(valores, anclas)


def _ingresos(lineas: list[_Linea], lectura: _Lectura) -> None:
    anclas: dict[str, float] = {}
    filas: list[dict[str, Decimal]] = []
    for linea in lineas:
        if linea.encabezado:
            gravables = sorted(s.x1 for s in linea.spans if s.texto in ("Gravable", "No Gravable"))
            if len(gravables) == len(_COLUMNAS_INGRESOS):
                anclas = dict(zip(_COLUMNAS_INGRESOS, gravables))
            continue
        valores = linea.valores()
        if not valores:
            if not linea.continuacion:
                filas = []  # título de grupo: Ingresos por Dividendos, Distribuciones, Gastos
            continue
        if not anclas:
            lectura.aviso(f"Resumen de Ingresos y Gastos: fila sin encabezado «{linea.texto}»")
            continue
        fila = _por_ancla(valores, anclas)
        if not linea.rotulo.startswith("Total de"):
            filas.append(fila)
            continue
        lectura.ingresos[linea.rotulo] = fila
        regla = f"Resumen de Ingresos y Gastos: suma de filas = {linea.rotulo}"
        lectura.controles.append(_cuadrar(regla, filas, fila))
        filas = []


# --- Tenencias ------------------------------------------------------------------


def _tenencias(lineas: list[_Linea], lectura: _Lectura) -> None:
    """Máquina de estados: moneda -> categoría -> subcategoría -> título ->
    atributos -> lotes -> totales."""
    tabla = _Tabla()
    bloque, moneda = "", "USD"
    categoria = subcategoria = ""
    titulo: _Titulo | None = None
    # Filas del último total, por si trae una 2.ª línea sin rótulo.
    segunda: list[dict] | None = None

    def nuevo(nombre: str, moneda_titulo: str) -> _Titulo:
        isin = _ISIN.search(nombre)
        t = _Titulo(_ISIN.sub("", nombre), moneda_titulo, bloque, categoria, subcategoria)
        if isin:
            t.otros["ISIN"] = isin.group(1)
        lectura.titulos.append(t)
        return t

    for i, linea in enumerate(lineas):
        if tabla.leer(linea):
            continue
        rotulo, primero = linea.rotulo, linea.spans[0]
        if primero.tamano >= _TAM_SUBTITULO and not rotulo.lower().startswith("total"):
            if not linea.continuacion:
                bloque, categoria, subcategoria, titulo = rotulo, "", "", None
                moneda = lectura.monedas.get(rotulo.upper(), "")
                if not moneda:
                    lectura.aviso(f"Tenencias: moneda «{rotulo}» sin código conocido")
            continue
        if not tabla.columnas:
            lectura.aviso(f"Tenencias: fila sin encabezado «{linea.texto}»")
            continue
        try:
            fila = tabla.fila(linea)
        except ValueError:
            lectura.aviso(f"Tenencias: fila no reconocida «{linea.texto}»")
            continue
        anterior, segunda = segunda, None
        if rotulo.lower().startswith("total"):
            total = _total(rotulo, fila, titulo, bloque, moneda, categoria, subcategoria, lectura)
            if total is None:
                continue
            segunda = total.filas
            if total.categoria is None:
                if total.bloque is None:
                    lectura.total_tenencias = fila
                    break  # lo que sigue son notas
                bloque = ""
            elif total.subcategoria is None:
                categoria = subcategoria = ""
            else:
                subcategoria = ""
            titulo = None
            continue
        if linea.empieza_con_fecha():
            if titulo is None:
                lectura.aviso(f"Tenencias: lote sin título «{linea.texto}»")
                continue
            if "cierre" in fila:
                # Money market: su costo y su valor son el saldo al cierre.
                fila["costo"] = fila["valor"] = fila["cierre"]
            titulo.lotes.append(fila)
            continue
        if not rotulo:
            if anterior is not None:
                anterior.append(fila)
            elif titulo and titulo.moneda != "USD" and not titulo.usd:
                titulo.usd = fila
            else:
                lectura.aviso(f"Tenencias: fila sin rótulo no reconocida «{linea.texto}»")
            continue
        codigo = next((s for s in linea.spans if s.texto.startswith(_CODIGO)), None)
        if codigo is not None:
            nombre = " ".join(s.texto for s in linea.spans if s.x1 <= codigo.x0 and not _es_valor(s.texto))
            if nombre:
                titulo = nuevo(nombre, moneda)
            elif titulo is None:
                lectura.aviso(f"Tenencias: código sin título «{linea.texto}»")
                continue
            elif linea.valores():
                titulo.usd = fila
            titulo.ticker = codigo.texto.removeprefix(_CODIGO).strip()
            continue
        cusip = next((s for s in linea.spans if s.texto.startswith(_CUSIP)), None)
        if cusip is not None or rotulo.startswith(_ATRIBUTOS):
            if titulo is None:
                lectura.aviso(f"Tenencias: atributo sin título «{linea.texto}»")
                continue
            if cusip is not None:
                titulo.cusip = cusip.texto.removeprefix(_CUSIP).strip()
            for s in linea.spans:
                if s is not cusip:
                    etiqueta, _, valor = s.texto.partition(":")
                    if etiqueta.startswith(("Base de Costo Original", "Precio estimado")) and valor:
                        titulo.otros[etiqueta.strip()] = valor.strip()
                    else:
                        titulo.detalle.append(s.texto)
            continue
        if linea.valores():
            # Posición en otra moneda: nombre, cantidad, precio y valor en la misma fila.
            if "descripcion" not in fila:
                lectura.aviso(f"Tenencias: fila no reconocida «{linea.texto}»")
                continue
            titulo = nuevo(fila["descripcion"], fila.get("divisa") or moneda)
            titulo.lotes.append(fila)
            continue
        if linea.continuacion:
            continue
        if titulo is not None and not titulo.lotes:
            titulo.detalle.append(rotulo)  # condiciones del bono, "Efectivo" de la opción de ganancias
            continue
        if i + 1 < len(lineas) and lineas[i + 1].empieza_con_fecha():
            titulo = nuevo(rotulo, moneda)  # fondo money market: sin código ni CUSIP
            continue
        nombre = _SUFIJO_CATEGORIA.sub("", rotulo).strip()
        titulo = None
        if nombre in _CATEGORIAS or not categoria:
            if nombre not in _CATEGORIAS:
                lectura.aviso(f"Tenencias: categoría «{nombre}» sin equivalente; sus posiciones quedan con esa tabla")
            categoria, subcategoria = nombre, ""
        else:
            subcategoria = nombre


def _total(
    rotulo: str,
    fila: dict,
    titulo: _Titulo | None,
    bloque: str,
    moneda: str,
    categoria: str,
    subcategoria: str,
    lectura: _Lectura,
) -> _Total | None:
    """La fila Total del título o un total de subcategoría, categoría, moneda o
    de toda la cartera. None si es el total de un título o no se reconoce."""
    bajo = rotulo.lower()
    if bajo in ("total cubierto", "total no cubierto"):
        return None
    if bajo == "total":
        if titulo is None:
            lectura.aviso("Tenencias: fila Total sin título")
        else:
            titulo.total = fila
        return None
    if bajo.startswith("total tenencias en cartera"):
        alcance, moneda = (None, None, None), "USD"
    elif bajo.startswith("total de "):
        nombre = bajo.removeprefix("total de ")
        if subcategoria and nombre == subcategoria.lower():
            alcance = (bloque, categoria, subcategoria)
        elif categoria and nombre == categoria.lower():
            alcance = (bloque, categoria, None)
        elif bloque and nombre == bloque.lower():
            alcance = (bloque, None, None)
        else:
            lectura.aviso(f"Tenencias: total «{rotulo}» no reconocido")
            return None
    else:
        lectura.aviso(f"Tenencias: total «{rotulo}» no reconocido")
        return None
    total = _Total(rotulo, moneda, *alcance, filas=[fila])
    lectura.totales.append(total)
    return total


def _posiciones(lectura: _Lectura) -> None:
    cartola = lectura.cartola
    for t in lectura.titulos:
        if t.tabla == "Money Market":
            saldo = t.medida("cierre", False)
            if saldo:
                cartola.saldos_caja.append(SaldoCaja(lectura.cuenta, t.moneda, saldo))
            continue
        if not t.tabla:
            lectura.aviso(f"Tenencias: «{t.nombre}» en {t.categoria} sin el formato del money market, no se leyó")
            continue
        cantidad = t.medida("cantidad", False)
        costo = t.medida("costo", False)
        precio = next((l["precio"] for l in t.lotes if l.get("precio") is not None), None)
        otros = {"CUSIP": t.cusip} if t.cusip else {}
        otros |= t.otros
        sufijo = f" ({t.moneda})" if t.moneda != "USD" else ""
        for clave, etiqueta in (
            ("costo", "Base de Costo Actual"),
            ("gp", "Ganancia o Pérdida No Realizada"),
            ("interes", "Intereses Devengados"),
            ("eai", "Ingresos Anuales Estimados"),
        ):
            if (valor := t.medida(clave, False)) is not None:
                otros[etiqueta + sufijo] = f"{valor}"
        redito = next((l["redito"] for l in t.lotes if l.get("redito") is not None), None)
        if redito is not None:
            otros["Rédito Estimado"] = f"{redito}%"
        if t.moneda != "USD":
            if (valor := t.medida("valor", False)) is not None:
                otros[f"Valor de Mercado ({t.moneda})"] = f"{valor}"
            if (eai := t.medida("eai", True)) is not None:
                otros["Ingresos Anuales Estimados (USD)"] = f"{eai}"
            if t.moneda in lectura.cambio:
                otros["Equivalente en USD"] = f"{lectura.cambio[t.moneda]}"
                if lectura.fecha_cambio:
                    otros["Tipo de cambio al"] = lectura.fecha_cambio
        promedio = None
        if costo is not None and cantidad:
            promedio = (costo / cantidad).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        cartola.posiciones.append(
            Posicion(
                cuenta=lectura.cuenta,
                seccion=t.categoria,
                tabla=t.tabla,
                previsional=False,
                instrumento=t.nombre,
                moneda=t.moneda,
                cantidad=cantidad,
                precio_promedio=promedio,
                precio_actual=precio,
                valor_clp=None,
                valor_usd=t.medida("valor", True),
                detalle=t.detalle,
                nemotecnico=t.ticker,
                otros=otros,
            )
        )


# --- Transacciones y money market ------------------------------------------------


def _transacciones(lineas: list[_Linea], lectura: _Lectura) -> None:
    """Cada transacción ocupa 2 líneas: en la 2.ª, bajo el tipo de actividad, va
    el identificador del título y, bajo la descripción, su continuación. En
    Sura se agrupan por tipo, con subtítulo y subtotal."""
    tabla = _Tabla()
    grupo = ""
    abierta: _Transaccion | None = None
    for linea in lineas:
        if tabla.leer(linea):
            continue
        if not tabla.columnas:
            lectura.aviso(f"Transacciones: fila sin encabezado «{linea.texto}»")
            continue
        rotulo = linea.rotulo
        try:
            fila = tabla.fila(linea)
        except ValueError:
            lectura.aviso(f"Transacciones: fila no reconocida «{linea.texto}»")
            continue
        if linea.empieza_con_fecha():
            if fila.get("monto") is None or not fila.get("tipo"):
                lectura.aviso(f"Transacciones: fila sin monto o sin tipo «{linea.texto}»")
            movimiento = MovimientoTitulo(
                fecha=_fecha(fila["fecha"]),
                cuenta=lectura.cuenta,
                tipo=fila.get("tipo", "").upper(),
                instrumento=fila.get("descripcion", ""),
                moneda=fila.get("divisa", ""),
                cantidad=fila.get("cantidad"),
                precio=fila.get("precio"),
                monto=fila.get("monto"),
                destino="PERSHING",
            )
            abierta = _Transaccion(movimiento, grupo, fila.get("descripcion", ""), fila.get("interes"))
            lectura.transacciones.append(abierta)
            lectura.cartola.movimientos_titulos.append(movimiento)
            continue
        if abierta is not None and linea.spans[0].x0 > 90:
            abierta.identificador = fila.get("tipo", "")
            if fila.get("descripcion"):
                abierta.movimiento.instrumento = f"{abierta.movimiento.instrumento} {fila['descripcion']}".strip()
            abierta = None
            continue
        abierta = None
        if rotulo.startswith("Valor Total de las Transacciones"):
            lectura.total_transacciones[fila.get("divisa", "")] = fila
        elif rotulo.startswith("Total de "):
            del_grupo = [t for t in lectura.transacciones if t.grupo == rotulo.removeprefix("Total de ")]
            if not del_grupo:
                lectura.aviso(f"Transacciones: subtotal «{rotulo}» sin grupo")
                continue
            for clave, nombre in (("monto", "monto"), ("interes", "intereses devengados")):
                if fila.get(clave) is not None:
                    calculado = sum((_valor_transaccion(t, clave) for t in del_grupo), _CERO)
                    regla = f"Transacciones: suma de {nombre} = {rotulo}"
                    lectura.controles.append(_comparar(regla, calculado, fila[clave], _CERO))
        elif rotulo.startswith("Es posible que"):
            break
        elif not linea.valores():
            if not linea.continuacion:
                grupo = rotulo
        else:
            lectura.aviso(f"Transacciones: fila no reconocida «{linea.texto}»")


def _valor_transaccion(t: _Transaccion, clave: str) -> Decimal:
    valor = t.movimiento.monto if clave == "monto" else t.interes
    return valor or _CERO


def _money_market(lineas: list[_Linea], lectura: _Lectura) -> None:
    """Detalles del Fondo de Money Market: duplica los barridos de las
    transacciones, así que solo se usa para cuadrar."""
    tabla = _Tabla()
    fondo: _Fondo | None = None
    malas: list[str] = []
    revisadas = 0
    for linea in lineas:
        if tabla.leer(linea):
            continue
        rotulo = linea.rotulo
        if not linea.valores():
            if not (linea.continuacion or rotulo.startswith(("Fondo de Money Market", "Rédito actual"))):
                fondo = _Fondo(rotulo)
                lectura.fondos.append(fondo)
            continue
        if not tabla.columnas:
            lectura.aviso(f"Detalles del Fondo de Money Market: fila sin encabezado «{linea.texto}»")
            continue
        fila = tabla.fila(linea)
        if rotulo.startswith("Total de Todos los Fondos"):
            lectura.total_fondos = fila.get("saldo")
            break
        tipo, monto, saldo = fila.get("tipo", ""), fila.get("monto"), fila.get("saldo")
        if fondo is None:
            lectura.aviso(f"Detalles del Fondo de Money Market: fila sin fondo «{linea.texto}»")
            continue
        if tipo == "Saldo de Apertura":
            fondo.saldo = saldo
        elif tipo == "Saldo al Cierre":
            fondo.cierre = saldo
        elif tipo in ("Depósito", "Retiro") and monto is not None and fondo.saldo is not None:
            # Los retiros no aparecen en las muestras: se restan con el signo que traigan.
            fondo.saldo += -abs(monto) if tipo == "Retiro" else monto
            revisadas += 1
            if saldo is not None and fondo.saldo != saldo:
                malas.append(f"{fila.get('fecha')} {tipo}: {fondo.saldo} vs {saldo}")
                fondo.saldo = saldo
        else:
            lectura.aviso(f"Detalles del Fondo de Money Market: actividad «{tipo}» no reconocida")
            if saldo is not None:
                fondo.saldo = saldo
    if revisadas:
        regla = f"Detalles del Fondo de Money Market: saldo anterior ± monto = saldo ({revisadas} filas)"
        lectura.controles.append(Control(regla, not malas, "; ".join(malas)))
    for f in lectura.fondos:
        regla = f"Detalles del Fondo de Money Market: saldos de {f.nombre} = Saldo al Cierre"
        lectura.controles.append(_comparar(regla, f.saldo, f.cierre, _CERO))


def _completar_movimientos(lectura: _Lectura) -> None:
    """Ticker y producto de cada transacción, por el CUSIP o el código del título
    en las tenencias; el sweep tiene un código propio y se reconoce por el nombre."""
    por_codigo: dict[str, _Titulo] = {}
    for t in lectura.titulos:
        for codigo in (t.cusip, t.ticker):
            if codigo:
                por_codigo.setdefault(codigo, t)
    nombres = [(_norma(t.nombre), t.tabla) for t in lectura.titulos]
    nombres += [(_norma(f.nombre), "Money Market") for f in lectura.fondos]
    for tr in lectura.transacciones:
        m, codigo = tr.movimiento, tr.identificador
        t = por_codigo.get(codigo)
        m.nemotecnico = t.ticker if t and codigo == t.cusip and t.ticker else codigo
        if t is not None:
            tablas = {t.tabla}
        else:
            descripcion = _norma(tr.descripcion)
            tablas = {
                tabla
                for nombre, tabla in nombres
                if len(descripcion) >= 10 and (nombre.startswith(descripcion) or descripcion.startswith(nombre))
            }
        m.producto = _PRODUCTOS.get(tablas.pop(), "") if len(tablas) == 1 else ""
        if not m.producto:
            que = f"el título {codigo}" if codigo else "sin identificador de título"
            lectura.aviso(f"Transacción {m.fecha} {m.tipo} {m.instrumento}: {que} no está en las tenencias, va sin producto")


_LECTORES = (
    ("divisas", _divisas),
    ("cambio", _cambio),
    ("tenencias", _tenencias),
    ("money_market", _money_market),
    ("cartera", _cartera),
    ("activos", _activos),
    ("actividad", _actividad),
    ("transacciones", _transacciones),
    ("ingresos", _ingresos),
)


# --- Cuadraturas -------------------------------------------------------------------


def _comparar(regla: str, calculado: Decimal | None, impreso: Decimal | None, tolerancia: Decimal) -> Control:
    if calculado is None or impreso is None:
        return Control(regla, False, "no se encontró el valor impreso")
    diferencia = calculado - impreso
    detalle = "" if diferencia == 0 else f"calculado {calculado}, impreso {impreso}, diferencia {diferencia}"
    return Control(regla, abs(diferencia) <= tolerancia, detalle)


def _cuadrar(regla: str, filas: list[dict[str, Decimal]], total: dict[str, Decimal]) -> Control:
    """Suma de las filas = fila de totales, en todas sus columnas."""
    malas = []
    for columna, impreso in total.items():
        calculado = _suma(f.get(columna) for f in filas)
        if calculado != impreso:
            malas.append(f"{_NOMBRES_COLUMNAS.get(columna, columna)}: calculado {calculado}, impreso {impreso}")
    return Control(regla, not malas, "; ".join(malas))


def _por_fila(regla: str, malas: list[str], revisadas: int) -> list[Control]:
    if not revisadas:
        return []
    return [Control(f"{regla} ({revisadas})", not malas, "; ".join(malas))]


def _suma(valores) -> Decimal:
    return sum((v for v in valores if v is not None), _CERO)


def _controles(lectura: _Lectura) -> list[Control]:
    cartola = lectura.cartola
    controles: list[Control] = []
    cartera = dict(lectura.cartera)
    inicial = cartera.get("VALOR INICIAL DE LA CUENTA", {})
    final = cartera.get("VALOR FINAL DE LA CUENTA", {})
    tenencias = lectura.total_tenencias

    # Resumen de la Cartera: valor inicial + las filas de en medio = valor final.
    rotulos = [r for r, _ in lectura.cartera]
    if inicial and final:
        entre = lectura.cartera[rotulos.index("VALOR INICIAL DE LA CUENTA") + 1 : rotulos.index("VALOR FINAL DE LA CUENTA")]
        for columna, nombre in (("periodo", "este período"), ("anio", "año hasta la fecha")):
            if columna in inicial or columna in final:
                calculado = inicial.get(columna, _CERO) + _suma(v.get(columna) for _, v in entre)
                regla = f"Resumen de la Cartera ({nombre}): valor inicial + movimientos = valor final"
                controles.append(_comparar(regla, calculado, final.get(columna), _CERO))
        cartola.totales["valor_inicial"] = inicial.get("periodo")
        cartola.totales["valor_final"] = final.get("periodo")
        ingresos = cartera.get("Dividendos, Intereses y Otros Ingresos", {})
        for columna, clave in (("periodo", "ingresos"), ("anio", "ingresos_anio")):
            if columna in ingresos:
                cartola.totales[clave] = ingresos[columna]
    else:
        controles.append(Control("Resumen de la Cartera: valor inicial y final", False, "no se encontraron"))
    if final and "Intereses Devengados" in cartera:
        con_intereses = next((v for r, v in lectura.cartera if r.startswith("Valor de la cuenta con intereses")), {})
        regla = "Resumen de la Cartera: valor final + intereses devengados = valor con intereses acumulados"
        calculado = final.get("periodo", _CERO) + cartera["Intereses Devengados"].get("periodo", _CERO)
        controles.append(_comparar(regla, calculado, con_intereses.get("periodo"), _CERO))
    for rotulo, clave in (("Ingresos Anuales Estimados", "eai"), ("Intereses Devengados", "interes")):
        if rotulo in cartera and tenencias.get(clave) is not None:
            regla = f"Resumen de la Cartera: {rotulo} = Total Tenencias en Cartera"
            controles.append(_comparar(regla, cartera[rotulo].get("periodo"), tenencias[clave], _CERO))

    # Resumen de Activos: clases, total y valores de la cuenta.
    activos = dict(lectura.activos)
    total_activos = next((activos.pop(r) for r in list(activos) if r.startswith("Total de la Cuenta")), {})
    for columna, valor_cuenta, nombre in (("anterior", inicial, "valor inicial"), ("actual", final, "valor final")):
        if columna not in total_activos:
            continue
        regla = f"Resumen de Activos: suma de clases = total ({columna})"
        calculado = _suma(v.get(columna) for v in activos.values())
        controles.append(_comparar(regla, calculado, total_activos[columna], _CERO))
        regla = f"Resumen de Activos: total ({columna}) = {nombre} de la cuenta"
        controles.append(_comparar(regla, total_activos[columna], valor_cuenta.get("periodo"), _CERO))
    for clase, valores in activos.items():
        if "actual" in valores:
            calculado = _suma(t.medida("valor", True) for t in lectura.titulos if t.categoria == clase)
            regla = f"Resumen de Activos: {clase} = tenencias de esa categoría"
            controles.append(_comparar(regla, calculado, valores["actual"], _CERO))
    if not lectura.activos:
        controles.append(Control("Resumen de Activos", False, "no se encontró"))

    # Tenencias.
    controles += _controles_tenencias(lectura)
    if tenencias:
        regla = "Total Tenencias en Cartera: valor de mercado = valor final de la cuenta"
        controles.append(_comparar(regla, tenencias.get("valor"), final.get("periodo"), _CERO))
    elif lectura.titulos:
        controles.append(Control("Total Tenencias en Cartera", False, "no se encontró"))

    # Money market: los detalles contra las tenencias.
    mercado = [t for t in lectura.titulos if t.tabla == "Money Market"]
    for f in lectura.fondos:
        t = next((t for t in mercado if _norma(t.nombre) == _norma(f.nombre)), None)
        regla = f"Money market {f.nombre}: saldo al cierre de los detalles = tenencias"
        controles.append(_comparar(regla, f.cierre, t.medida("cierre", False) if t else None, _CERO))
    if lectura.total_fondos is not None:
        regla = "Detalles del Fondo de Money Market: suma de fondos = Total de Todos los Fondos"
        controles.append(_comparar(regla, _suma(f.cierre for f in lectura.fondos), lectura.total_fondos, _CERO))
    malas = [
        f"{t.nombre}: {t.medida('cantidad', False)} vs {t.medida('cierre', False)}"
        for t in mercado
        if t.medida("cantidad", False) != t.medida("cierre", False)
    ]
    controles += _por_fila("Money market: cantidad = saldo al cierre", malas, len(mercado))

    # Resumen de Actividad.
    actividad = dict(lectura.actividad)
    totales = actividad.pop("Totales", None)
    malas, revisadas = [], 0
    for rotulo, fila in lectura.actividad.items():
        for sufijo in ("", "_anio"):
            if f"neto{sufijo}" in fila:
                revisadas += 1
                calculado = fila.get(f"creditos{sufijo}", _CERO) + fila.get(f"debitos{sufijo}", _CERO)
                if calculado != fila[f"neto{sufijo}"]:
                    malas.append(f"{rotulo}{' (año)' if sufijo else ''}: {calculado} vs {fila[f'neto{sufijo}']}")
    controles += _por_fila("Resumen de Actividad: créditos + débitos = neto", malas, revisadas)
    if totales:
        controles.append(_cuadrar("Resumen de Actividad: suma de filas = Totales", list(actividad.values()), totales))
    elif lectura.actividad:
        controles.append(Control("Resumen de Actividad: Totales", False, "no se encontró"))

    # Transacciones.
    for divisa, fila in lectura.total_transacciones.items():
        de_divisa = [t for t in lectura.transacciones if t.movimiento.moneda == divisa]
        for clave, nombre in (("monto", "montos"), ("interes", "intereses devengados")):
            if fila.get(clave) is not None:
                regla = f"Transacciones: suma de {nombre} = Valor Total de las Transacciones ({divisa})"
                calculado = _suma(_valor_transaccion(t, clave) for t in de_divisa)
                controles.append(_comparar(regla, calculado, fila[clave], _CERO))
    if lectura.transacciones and not lectura.total_transacciones:
        controles.append(Control("Transacciones: Valor Total de las Transacciones", False, "no se encontró"))
    if totales and set(lectura.total_transacciones) == {"USD"}:
        regla = "Transacciones: Valor Total = neto del período del Resumen de Actividad"
        controles.append(_comparar(regla, lectura.total_transacciones["USD"].get("monto"), totales.get("neto"), _CERO))

    # Ingresos y gastos contra la actividad.
    for total, fila_actividad in (("Total de ingresos", "Dividendos e Intereses"), ("Total de Distribuciones", "Distribuciones")):
        if total in lectura.ingresos and fila_actividad in lectura.actividad:
            ingresos, actividad_fila = lectura.ingresos[total], lectura.actividad[fila_actividad]
            for sufijo, nombre in (("", "período"), ("_anio", "año")):
                if f"neto{sufijo}" in actividad_fila:
                    calculado = ingresos.get(f"gravable{sufijo}", _CERO) + ingresos.get(f"no_gravable{sufijo}", _CERO)
                    regla = f"Resumen de Ingresos y Gastos: {total} = {fila_actividad} de la actividad ({nombre})"
                    controles.append(_comparar(regla, calculado, actividad_fila[f"neto{sufijo}"], _CERO))

    # Resumen de tenencias por divisa.
    for rotulo, fila in lectura.divisas.items():
        for codigo, impreso in fila.items():
            de_moneda = [t for t in lectura.titulos if t.moneda == codigo]
            if rotulo == "Total de valor de mercado local":
                calculado = _suma(t.medida("valor", False) for t in de_moneda)
            elif rotulo == "Total de valor de mercado (USD)":
                calculado = _suma(t.medida("valor", True) for t in de_moneda)
            elif rotulo == "Porcentaje de cartera":
                continue
            else:
                calculado = _suma(t.medida("valor", False) for t in de_moneda if t.categoria.startswith(rotulo))
            regla = f"Resumen de tenencias por divisa: {rotulo} ({codigo}) = tenencias"
            controles.append(_comparar(regla, calculado, impreso, _CERO))

    # Equivalente en USD de las posiciones en otras monedas.
    for t in lectura.titulos:
        if t.moneda == "USD":
            continue
        local, usd = t.medida("valor", False), t.medida("valor", True)
        tasa = lectura.cambio.get(t.moneda)
        regla = f"{t.nombre}: valor en {t.moneda} × equivalente en USD = valor en USD"
        if tasa is None or local is None:
            controles.append(Control(regla, False, f"no se encontró el valor en {t.moneda} o el tipo de cambio"))
            continue
        # La tasa viene con 4 decimales.
        controles.append(_comparar(regla, (local * tasa).quantize(_CENTESIMO), usd, abs(local) * Decimal("0.00005") + _CENTESIMO))
    return controles


def _controles_tenencias(lectura: _Lectura) -> list[Control]:
    controles: list[Control] = []
    for total in lectura.totales:
        items = [t for t in lectura.titulos if total.incluye(t)]
        malas, revisadas = [], 0
        for fila in total.filas:
            divisa = fila.get("divisa", "")
            en_usd = divisa == "USD" or (not divisa and total.moneda == "USD")
            for clave in _MEDIDAS:
                if fila.get(clave) is None:
                    continue
                revisadas += 1
                calculado = _suma(t.medida(clave, en_usd) for t in items)
                if calculado != fila[clave]:
                    nombre = _NOMBRES_MEDIDAS[clave] + (" en USD" if en_usd and total.moneda != "USD" else "")
                    malas.append(f"{nombre}: calculado {calculado}, impreso {fila[clave]}")
        if revisadas:
            controles.append(Control(f"Tenencias: suma de títulos = {total.rotulo}", not malas, "; ".join(malas)))

    malas, revisadas = [], 0
    for t in lectura.titulos:
        if not t.total:
            continue
        revisadas += 1
        for clave in _MEDIDAS:
            if t.total.get(clave) is not None:
                calculado = _suma(l.get(clave) for l in t.lotes)
                if calculado != t.total[clave]:
                    malas.append(f"{t.nombre} {_NOMBRES_MEDIDAS[clave]}: {calculado} vs {t.total[clave]}")
    controles += _por_fila("Tenencias: suma de lotes = fila Total del título", malas, revisadas)

    # Por lote: cantidad × precio = valor (el precio viene con 4 decimales; el
    # de los bonos, en porcentaje del nominal) y valor − costo = ganancia o pérdida.
    precio_malo, gp_malo, precio_revisados, gp_revisados = [], [], 0, 0
    for t in lectura.titulos:
        for l in t.lotes:
            cantidad, precio, valor, costo, gp = (l.get(k) for k in ("cantidad", "precio", "valor", "costo", "gp"))
            if None not in (cantidad, precio, valor):
                nominal = Decimal(100) if t.tabla == "Bonos" else Decimal(1)
                precio_revisados += 1
                calculado = cantidad * precio / nominal
                if abs(calculado - valor) > Decimal("0.005") + abs(cantidad) / nominal * Decimal("0.00005"):
                    precio_malo.append(f"{t.nombre} {l.get('fecha', '')}: {calculado} vs {valor}")
            if None not in (valor, costo, gp):
                gp_revisados += 1
                if valor - costo != gp:
                    gp_malo.append(f"{t.nombre} {l.get('fecha', '')}: {valor - costo} vs {gp}")
            unitario = l.get("costo_unitario")
            if None not in (cantidad, unitario, costo) and costo:
                nominal = Decimal(100) if t.tabla == "Bonos" else Decimal(1)
                diferencia = cantidad * unitario / nominal - costo
                # El costo unitario viene redondeado: solo se avisa si se aleja mucho.
                if abs(diferencia) > max(Decimal(1), abs(costo) * Decimal("0.001")):
                    lectura.aviso(f"{t.nombre} {l.get('fecha', '')}: cantidad × costo por unidad difiere de la base de costo en {diferencia:.2f}")
    controles += _por_fila("Tenencias: cantidad × precio = valor de mercado por lote", precio_malo, precio_revisados)
    controles += _por_fila("Tenencias: valor de mercado − base de costo = ganancia o pérdida por lote", gp_malo, gp_revisados)
    return controles
