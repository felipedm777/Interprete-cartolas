"""Cartola consolidada de inversiones de Valores Security / AGF Security.

Viene pegada después de una cartola BICE antigua, en páginas carta apaisadas.
Página 1: resumen de inversión; página 2: detalle por productos y por clase de
activos; luego el detalle de inversiones no previsionales y previsionales, la
caja, los movimientos y una página de rentabilidad sin datos. El detalle del
formato está en docs/instituciones/bice-antigua-y-security.md (parte B).
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
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

FORMATO = "Valores Security"

_MARCA = "VALORES SECURITY S.A. CDB"
_MONEDAS = {"CLP", "USD", "EUR"}
_NUMERO = re.compile(r"-?[\d.]+(,\d+)?")
# Los títulos de página van arriba de esta altura y el pie (texto legal y
# número de página), abajo de la otra.
_Y_TITULO = 30
_Y_PIE = 566

_CAJA = {"PESOS": "CLP", "DOLAR": "USD", "EURO": "EUR"}
_SALDO_CAJA = {"En Peso": "CLP", "En Dolar": "USD", "En Euro": "EUR"}

# Movimientos de caja con equivalente en el vocabulario del export: (comienzo de
# la descripción, moneda de la caja) -> tipo. El resto queda con la descripción
# en mayúsculas y sin el nemotécnico, que va en el campo instrumento.
TIPOS_CAJA = {
    ("Dividendo", "CLP"): "DIVIDENDO EN PESOS",
    ("Dividendo", "USD"): "DIVIDENDO EN DOLARES",
    ("Factura Ele. Compra Acciones", "CLP"): "FACTURA COMPRA RV",
    ("Factura Ele. Compra Acciones", "USD"): "FACTURA COMPRA RV EN USD",
    ("Cargo en Cuenta Corriente para Inversión en FM", "CLP"): "CARGO COMPROMISO DE INVERSION $ OWP",
}

# TIPO MOVTO del informe de transacciones (viene truncado) -> (tipo, destino).
# Los dividendos no se exportan como títulos: ya están en los movimientos de caja.
TIPOS_TITULOS = {
    "inversion": ("INVERSION FM", "FFMM"),
    "rescate": ("RESCATE FM", "FFMM"),
    "compra": ("COMPRA RV", "BOLSA"),
    "venta": ("VENTA RV", "BOLSA"),
    "canje de cu": ("CANJE DE CUOTAS", "BOLSA"),
    "disminucio": ("DISMINUCION DE CAPITAL", "BOLSA"),
    "emision lib": ("EMISION LIBERADA", "BOLSA"),
    "dividendo": ("DIVIDENDO", ""),
}
# Inversiones y rescates de algo que no es un fondo mutuo (p. ej. un CFI rescatable).
_TIPOS_NO_FM = {"INVERSION FM": "INVERSION CFI", "RESCATE FM": "RESCATE CFI"}
# Compraventa de divisas: el instrumento es la moneda y no es un título.
_DIVISAS = {"EURO", "DOLAR", "DÓLAR", "USD", "EUR"}
_TIPOS_DIVISA = {"COMPRA RV": "COMPRA MONEDA EXTRANJERA", "VENTA RV": "VENTA MONEDA EXTRANJERA"}

_NEMO_EN_DESCRIPCION = re.compile(r"^(Dividendo|Disminucion de Capital)\s+(\S+)\s+-\s+")
_NEMO_SUELTO = re.compile(r"\b(CF[IM][\w-]*)\b", re.IGNORECASE)

_CERO = Decimal(0)
_MEDIO = Decimal("0.5")


def paginas(doc: pymupdf.Document) -> list[int]:
    """Páginas de la cartola Security dentro del PDF.

    Son las que traen la marca en la cabecera, más las carta apaisadas que las
    siguen sin marca. El tamaño solo no basta: Pershing, Sura y Larrainvial
    también usan carta apaisada.
    """
    return _paginas(doc)


def _paginas(doc: pymupdf.Document) -> list[int]:
    resultado: list[int] = []
    for i, pagina in enumerate(doc):
        if _MARCA in pagina.get_text().upper():
            resultado.append(i)
        elif resultado and resultado[-1] == i - 1 and _carta_apaisada(pagina):
            resultado.append(i)
    return resultado


def _carta_apaisada(pagina: pymupdf.Page) -> bool:
    return round(pagina.rect.width) == 792 and round(pagina.rect.height) == 612


def extraer(ruta: str | Path, paginas: list[int] | None = None) -> Cartola:
    doc = pymupdf.open(ruta)
    indices = paginas if paginas is not None else _paginas(doc)
    if not indices:
        raise ValueError(f"{ruta}: no trae páginas de la cartola Security")
    # La cabecera y los totales de la página 1 van en blanco sobre una franja de color.
    hojas = [leer_spans(doc[i], blancos=True) for i in indices]
    cartola = _cabecera(hojas[0], str(ruta))
    lector = _Lector(cartola)
    for spans in hojas:
        titulo = _titulo(spans)
        contenido = _contenido(spans)
        textos = {s.texto for s in contenido}
        if "Resumen Inversión" in textos:
            _resumen_inversion(contenido, lector)
        elif "DETALLE DE INVERSIONES POR PRODUCTOS" in textos:
            _productos_y_clases(contenido, lector)
        elif titulo.startswith("DETALLE DE"):
            lector.pagina(titulo, contenido)
    lector.cerrar()
    return cartola


# --- Cabecera -----------------------------------------------------------------


def _cabecera(spans: list[Span], archivo: str) -> Cartola:
    def valor(etiqueta: str) -> list[Span]:
        e = next((s for s in spans if s.y0 < _Y_PIE and re.match(etiqueta, s.texto)), None)
        if e is None:
            return []
        return sorted(
            (s for s in spans if abs(s.yc - e.yc) < 3 and s.x0 >= e.x1 - 1 and s.x0 < e.x1 + 300),
            key=lambda s: s.x0,
        )

    texto = " ".join(s.texto for s in spans)
    periodo = re.search(r"Desde el (\d{2}-\d{2}-\d{4}) al (\d{2}-\d{2}-\d{4})", texto)
    rut = valor(r"Rut\s*:")
    if not rut or not periodo:
        raise ValueError(f"{archivo}: no se encontró el RUT o el período en la cabecera")
    nombre = valor(r"Nombre\s*:")

    def cambio(etiqueta: str) -> Decimal | None:
        celdas = valor(etiqueta)
        return leer_monto(celdas[0].texto) if celdas else None

    return Cartola(
        formato=FORMATO,
        archivo=archivo,
        rut=rut[0].texto.replace(".", "").upper(),
        nombre=" ".join(s.texto for s in nombre),
        desde=_fecha(periodo.group(1)),
        hasta=_fecha(periodo.group(2)),
        tipo_cambio_usd=cambio(r"USD:$"),
        institucion="SECURITY",
        tipo_cambio_eur=cambio(r"€:$"),
    )


def _titulo(spans: list[Span]) -> str:
    grandes = [s for s in spans if s.y1 < _Y_TITULO and s.tamano >= 12]
    return " ".join(s.texto for s in sorted(grandes, key=lambda s: s.x0))


def _contenido(spans: list[Span]) -> list[Span]:
    """Lo que está entre la cabecera (que termina en la línea de tipos de cambio) y el pie."""
    cambio = [s for s in spans if s.texto in ("USD:", "€:", "UF:")]
    y_min = max(s.y1 for s in cambio) if cambio else 104
    return [s for s in spans if y_min < s.y0 < _Y_PIE and s.tamano >= 6]


def _fecha(texto: str) -> date:
    return datetime.strptime(texto.strip().replace("/", "-"), "%d-%m-%Y").date()


def _es_numero(texto: str) -> bool:
    return bool(_NUMERO.fullmatch(texto))


def _monto(texto: str | None) -> Decimal | None:
    if not texto:
        return None
    return leer_monto(texto.replace("(*)", ""))


def _filas(spans: list[Span]) -> list[list[Span]]:
    """Agrupa los fragmentos en líneas por su altura, ordenadas de izquierda a derecha."""
    filas: list[list[Span]] = []
    for s in sorted(spans, key=lambda s: (s.yc, s.x0)):
        if filas and abs(filas[-1][0].yc - s.yc) < 2:
            filas[-1].append(s)
        else:
            filas.append([s])
    return [sorted(f, key=lambda s: s.x0) for f in filas]


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


# --- Cuadraturas ----------------------------------------------------------------


class _Cuadraturas:
    """Junta las comparaciones de cada regla y entrega un Control por regla."""

    def __init__(self) -> None:
        self.reglas: dict[str, list] = {}

    def comparar(
        self, regla: str, calculado: Decimal, impreso: Decimal, tolerancia: Decimal, que: str = ""
    ) -> None:
        cuenta = self.reglas.setdefault(regla, [0, []])
        cuenta[0] += 1
        diferencia = calculado - impreso
        if abs(diferencia) > tolerancia:
            cuenta[1].append(f"{que + ': ' if que else ''}calculado {calculado}, impreso {impreso}")

    def controles(self) -> list[Control]:
        return [
            Control(regla if n == 1 else f"{regla} ({n})", not malas, "; ".join(malas))
            for regla, (n, malas) in self.reglas.items()
        ]


# --- Páginas 1 y 2: resúmenes ---------------------------------------------------


def _resumen_inversion(spans: list[Span], lector: "_Lector") -> None:
    """Resumen Inversión: grupos de activos, caja y patrimonio total."""
    c = lector.cuadraturas
    t = lector.cartola.totales
    grupos: dict[str, list[Decimal]] = {}
    grupo = None
    for fila in _filas([s for s in spans if s.x1 < 420]):
        etiqueta = " ".join(s.texto for s in fila if s.x1 < 200)
        if any(s.texto.startswith("Monto de Inversión") for s in fila):
            grupo = etiqueta
            grupos[grupo] = []
            continue
        montos = [s for s in fila if 200 < s.x1 < 300 and _es_numero(s.texto)]
        if not etiqueta or not montos:
            continue
        valor = leer_monto(montos[0].texto)
        t[f"resumen:{etiqueta}"] = valor
        if grupo and not etiqueta.startswith("Total") and etiqueta != "TOTAL PATRIMONIO":
            grupos[grupo].append(valor)
    activos = next((s for s in spans if s.texto.startswith("Total Activos :")), None)
    if activos:
        derecha = [s for s in spans if abs(s.yc - activos.yc) < 3 and s.x0 > activos.x1]
        if derecha:
            t["resumen:Total Activos"] = _monto(derecha[0].texto)
    for nombre, valores in grupos.items():
        total = t.get(f"resumen:Total {nombre}")
        if total is not None:
            c.comparar(f"Resumen inversión: suma de {nombre} = Total {nombre}", sum(valores, _CERO), total, _CERO)
    partes = ("Activos Directos", "Activos Bajo Mandato", "Ahorro Previsional")
    if "resumen:Total Activos" in t and all(f"resumen:Total {p}" in t for p in partes):
        c.comparar(
            "Resumen inversión: directos + bajo mandato + previsional = Total Activos",
            sum(t[f"resumen:Total {p}"] for p in partes),
            t["resumen:Total Activos"],
            _CERO,
        )
    if all(k in t for k in ("resumen:Total Activos", "resumen:Total Caja", "resumen:TOTAL PATRIMONIO")):
        c.comparar(
            "Resumen inversión: Total Activos + Total Caja = TOTAL PATRIMONIO",
            t["resumen:Total Activos"] + t["resumen:Total Caja"],
            t["resumen:TOTAL PATRIMONIO"],
            _CERO,
        )


def _productos_y_clases(spans: list[Span], lector: "_Lector") -> None:
    """Página 2: detalle por productos (saldo inicial y final) y por clase de activos."""
    c = lector.cuadraturas
    t = lector.cartola.totales
    spans = [s for s in spans if s.x0 < 570]
    corte = next((s.y0 for s in spans if s.texto == "DETALLE DE INVERSIONES POR CLASE DE ACTIVOS"), 10_000)

    productos = _tabla_resumen([s for s in spans if s.y0 < corte - 2])
    fechas = [col.etiqueta for col in productos["columnas"]]
    bloque: list[tuple[str, dict]] = []
    totales_bloque = []
    for etiqueta, valores in productos["filas"]:
        if etiqueta == "Saldo Total":
            for col in fechas:
                if col in valores:
                    c.comparar(
                        "Por productos: suma = Saldo Total",
                        sum((v.get(col, _CERO) for _, v in bloque), _CERO),
                        valores[col],
                        Decimal(1),
                        col,
                    )
            totales_bloque.append(valores)
            bloque = []
        elif etiqueta == "TOTAL":
            if fechas and fechas[-1] in valores:
                t["productos:TOTAL"] = valores[fechas[-1]]
                if len(totales_bloque) > 1:
                    c.comparar(
                        "Por productos: Saldo Total + Pershing = TOTAL",
                        sum((v.get(fechas[-1], _CERO) for v in totales_bloque), _CERO),
                        valores[fechas[-1]],
                        Decimal(1),
                    )
        else:
            bloque.append((etiqueta, valores))
            if fechas and fechas[-1] in valores and not totales_bloque:
                t[f"productos:{etiqueta}"] = valores[fechas[-1]]
    if "productos:TOTAL" in t and "resumen:TOTAL PATRIMONIO" in t:
        c.comparar(
            "Por productos: TOTAL = TOTAL PATRIMONIO",
            t["productos:TOTAL"],
            t["resumen:TOTAL PATRIMONIO"],
            Decimal(1),
        )

    clases = _tabla_resumen([s for s in spans if s.y0 >= corte - 2])
    columnas = [col.etiqueta for col in clases["columnas"]]
    if len(columnas) != 3:
        lector.cartola.avisos.append("Detalle por clase de activos: no se reconocieron sus 3 columnas")
        return
    nacional, internacional, total = columnas
    subtotales, grupo = [], []
    for etiqueta, valores in clases["filas"]:
        if all(k in valores for k in columnas):
            c.comparar(
                "Por clase: nacional + internacional = total",
                valores[nacional] + valores[internacional],
                valores[total],
                Decimal(1),
                etiqueta,
            )
        if etiqueta == "SubTotal":
            c.comparar(
                "Por clase: suma del grupo = SubTotal",
                sum((v.get(total, _CERO) for v in grupo), _CERO),
                valores.get(total, _CERO),
                Decimal(1),
            )
            subtotales.append(valores.get(total, _CERO))
            grupo = []
        elif etiqueta == "SALDO TOTAL":
            c.comparar(
                "Por clase: suma de SubTotal = SALDO TOTAL",
                sum(subtotales, _CERO),
                valores.get(total, _CERO),
                Decimal(1),
            )
            if "resumen:TOTAL PATRIMONIO" in t:
                c.comparar(
                    "Por clase: SALDO TOTAL = TOTAL PATRIMONIO",
                    valores.get(total, _CERO),
                    t["resumen:TOTAL PATRIMONIO"],
                    Decimal(1),
                )
        elif valores:
            grupo.append(valores)


def _tabla_resumen(spans: list[Span]) -> dict:
    """Tabla con etiquetas a la izquierda y columnas de montos en pesos.

    El encabezado es la primera línea; sus fragmentos a la derecha de la
    etiqueta son las columnas.
    """
    filas = _filas(spans)
    if not filas:
        return {"columnas": [], "filas": []}
    encabezado = [s for s in filas[0][1:]]
    columnas = armar_columnas(encabezado)
    salida = []
    for fila in filas[1:]:
        etiqueta = " ".join(s.texto for s in fila if s.x1 < 200)
        valores = {
            columna_de(s, columnas): leer_monto(s.texto) for s in fila if s.x1 >= 200 and _es_numero(s.texto)
        }
        salida.append((etiqueta, valores))
    return {"columnas": columnas, "filas": salida}


# --- Detalle de inversiones y movimientos ---------------------------------------


@dataclass
class _Fila:
    celdas: dict[str, str] = field(default_factory=dict)
    # Moneda impresa junto a una celda (p. ej. el CLP/USD/EUR que sigue a un precio).
    monedas: dict[str, str] = field(default_factory=dict)
    total: bool = False

    def texto(self, *etiquetas: str) -> str:
        """Celda de la primera etiqueta que calce por comienzo."""
        for etiqueta in etiquetas:
            for k, v in self.celdas.items():
                if k.startswith(etiqueta):
                    return v
        return ""

    def monto(self, *etiquetas: str) -> Decimal | None:
        return _monto(self.texto(*etiquetas))

    def etiqueta(self, *etiquetas: str) -> str:
        for etiqueta in etiquetas:
            for k in self.celdas:
                if k.startswith(etiqueta):
                    return k
        return ""


@dataclass
class _BloqueCaja:
    moneda: str
    cuenta: str
    saldo: Decimal | None


class _Lector:
    """Recorre las páginas de detalle y arrastra el estado entre páginas.

    Las tablas de CFI siguen en la página siguiente sin repetir el encabezado,
    y los movimientos de caja no repiten el título "CAJA: <MONEDA>" ni el saldo
    inicial, así que el bloque, las columnas y el saldo corrido se heredan.
    """

    def __init__(self, cartola: Cartola) -> None:
        self.cartola = cartola
        self.cuadraturas = _Cuadraturas()
        self.previsional: bool | None = None
        self.bloque = ""
        self.columnas: list[Columna] = []
        self.caja: _BloqueCaja | None = None
        # Cuenta -> previsional, según el título de las páginas de detalle.
        self.grupos: dict[str, set[bool]] = defaultdict(set)
        # Suma de filas por bloque, para compararla con su TOTAL.
        self.sumas: dict[str, dict[str, Decimal]] = {}
        # (moneda, cuenta) -> saldo, del resumen de caja y del último movimiento.
        self.saldos_resumen: dict[tuple[str, str], Decimal] = {}
        self.saldos_movimientos: dict[tuple[str, str], Decimal] = {}
        self.caja_en_pesos: list[Decimal] = []
        self.total_caja: Decimal | None = None

    # Páginas ------------------------------------------------------------------

    def pagina(self, titulo: str, spans: list[Span]) -> None:
        if titulo.endswith("NO PREVISIONALES"):
            self.previsional = False
        elif titulo.endswith("PREVISIONALES"):
            self.previsional = True
        else:
            self.previsional = None
        encabezado: list[Span] = []
        for fila in _filas(spans):
            if any(s.tamano >= 11.5 for s in fila):
                titulo_bloque = " ".join(s.texto for s in fila if s.tamano >= 11.5 and s.tamano < 13)
                if titulo_bloque:
                    self._nuevo_bloque(re.sub(r"\s+", " ", titulo_bloque))
                continue
            total = fila[0].texto == "TOTAL" and fila[0].negrita
            if not total and all(s.negrita and not _es_numero(s.texto) for s in fila):
                encabezado += fila
                continue
            if encabezado:
                self.columnas = armar_columnas(encabezado)
                encabezado = []
            if not self.columnas:
                continue
            self._fila(self._celdas(fila, total))

    def _nuevo_bloque(self, titulo: str) -> None:
        self.bloque = titulo
        self.columnas = []
        if titulo.startswith("CAJA:"):
            moneda = _CAJA.get(titulo.removeprefix("CAJA:").strip())
            if moneda is None:
                self.cartola.avisos.append(f"Movimientos de caja en moneda no reconocida: {titulo}")
            self._cerrar_caja()
            self.caja = _BloqueCaja(moneda or "", "", None)

    def _celdas(self, fila: list[Span], total: bool) -> _Fila:
        resultado = _Fila(total=total)
        primera = min(self.columnas, key=lambda c: c.x0)
        anterior = None
        for s in fila:
            # El CLP/USD/EUR que sigue a un precio es su moneda, salvo que caiga en
            # una columna propia (la MDA de las transacciones).
            if s.texto in _MONEDAS and anterior is not None and _es_numero(anterior.texto):
                columna = columna_de(anterior, self.columnas)
                if _solapada(s, self.columnas) in (None, columna):
                    resultado.monedas[columna] = s.texto
                    continue
            etiqueta = primera.etiqueta if s.x0 <= primera.x0 + 5 else columna_de(s, self.columnas)
            previo = resultado.celdas.get(etiqueta)
            resultado.celdas[etiqueta] = f"{previo} {s.texto}" if previo else s.texto
            anterior = s
        return resultado

    def _fila(self, fila: _Fila) -> None:
        bloque = self.bloque
        if bloque.startswith("FONDOS SECURITY"):
            self._fondo_mutuo(fila, "USD" if bloque.endswith("USD") else "CLP")
        elif bloque in ("ACCIONES NACIONALES", "CUOTAS"):
            self._accion_o_cuota(fila, "Acciones" if bloque == "ACCIONES NACIONALES" else "CFI")
        elif bloque == "RESUMEN DE SALDOS EN CAJA":
            self._saldo_caja(fila)
        elif bloque == "INFORME DE TRANSACCIONES":
            self._transaccion(fila)
        elif bloque.startswith("CAJA:"):
            self._movimiento_caja(fila)
        elif bloque:
            aviso = f"Bloque no reconocido: {bloque}"
            if aviso not in self.cartola.avisos:
                self.cartola.avisos.append(aviso)

    def _sumar(self, clave: str, fila: _Fila, etiquetas: list[str]) -> None:
        """Acumula las columnas de montos de un bloque y, en su TOTAL, las compara."""
        suma = self.sumas.setdefault(clave, {})
        if fila.total:
            for etiqueta in etiquetas:
                impreso = fila.monto(etiqueta)
                if impreso is not None:
                    filas = suma.get("#", _CERO)
                    self.cuadraturas.comparar(
                        f"{self.bloque}: suma de filas = TOTAL",
                        suma.get(etiqueta, _CERO),
                        impreso,
                        max(Decimal(1), _MEDIO * filas),
                        etiqueta,
                    )
            del self.sumas[clave]
            return
        suma["#"] = suma.get("#", _CERO) + 1
        for etiqueta in etiquetas:
            valor = fila.monto(etiqueta)
            if valor is not None:
                suma[etiqueta] = suma.get(etiqueta, _CERO) + valor

    # Posiciones ---------------------------------------------------------------

    def _fondo_mutuo(self, fila: _Fila, moneda: str) -> None:
        sufijo = "(USD)" if moneda == "USD" else "($)"
        saldo = f"SALDO ACTUAL {sufijo}"
        etiquetas = [f"MONTO INVERTIDO {sufijo}", saldo, "MAYOR O MENOR VALOR"]
        if moneda == "USD":
            etiquetas.append("VALORIZACIÓN EN $")
        self._sumar(f"{self.previsional}:{self.bloque}", fila, etiquetas)
        if fila.total:
            return
        c = self.cuadraturas
        nombre = fila.texto("NOMBRE FONDO")
        cuenta = fila.texto("NUMERO CUENTA")
        cuotas = fila.monto("NUMERO CUOTA")
        valor_cuota = fila.monto("VALOR CUOTA ACTUAL")
        promedio = fila.monto("VALOR PROMEDIO COMPRA")
        invertido = fila.monto("MONTO INVERTIDO")
        saldo_moneda = fila.monto(saldo)
        mayor_menor = fila.monto("MAYOR O MENOR VALOR")
        valor_clp = fila.monto("VALORIZACIÓN EN $") if moneda == "USD" else saldo_moneda
        que = f"{cuenta} {nombre}"
        tolerancia = Decimal("0.005") if moneda == "USD" else _MEDIO
        if None not in (cuotas, valor_cuota, saldo_moneda):
            c.comparar(f"FM {moneda}: cuotas × valor cuota = saldo", cuotas * valor_cuota, saldo_moneda, tolerancia, que)
        if None not in (cuotas, promedio, invertido):
            c.comparar(
                f"FM {moneda}: cuotas × valor promedio de compra = monto invertido",
                cuotas * promedio,
                invertido,
                tolerancia,
                que,
            )
        if None not in (saldo_moneda, invertido, mayor_menor):
            c.comparar(
                f"FM {moneda}: saldo − monto invertido = mayor o menor valor",
                saldo_moneda - invertido,
                mayor_menor,
                Decimal("0.01") if moneda == "USD" else Decimal(1),
                que,
            )
        if moneda == "USD" and None not in (saldo_moneda, valor_clp) and self.cartola.tipo_cambio_usd:
            c.comparar(
                "FM USD: saldo en USD × USD de la cabecera = valorización en $",
                saldo_moneda * self.cartola.tipo_cambio_usd,
                valor_clp,
                _MEDIO,
                que,
            )
        usadas = {"NOMBRE FONDO", "NUMERO CUENTA", "NUMERO CUOTA"}
        usadas |= {fila.etiqueta(e) for e in ("VALOR CUOTA ACTUAL", "VALOR PROMEDIO COMPRA", saldo, "VALORIZACIÓN EN $")}
        self._posicion(
            Posicion(
                cuenta=cuenta,
                seccion="Fondos Mutuos",
                tabla="Fondos Mutuos",
                previsional=bool(self.previsional),
                instrumento=f"FM SECURITY {nombre}",
                moneda=moneda,
                cantidad=cuotas,
                precio_promedio=promedio,
                precio_actual=valor_cuota,
                valor_clp=valor_clp,
                valor_usd=saldo_moneda if moneda == "USD" else None,
                otros={k: v for k, v in fila.celdas.items() if k not in usadas},
            )
        )

    def _accion_o_cuota(self, fila: _Fila, tabla: str) -> None:
        etiquetas = ["MONTO INVERTIDO ($)", "SALDO ACTUAL ($)", "MAYOR O MENOR VALOR", "DEVOLUCION"]
        self._sumar(f"{self.previsional}:{self.bloque}", fila, etiquetas)
        if fila.total:
            return
        c = self.cuadraturas
        nombre = fila.texto("NOMBRE")
        cuenta = fila.texto("NUMERO CUENTA")
        total = fila.monto("TOTAL")
        garantias = fila.monto("GARANTIAS") or _CERO
        plazo = fila.monto("SALDO A PLAZO") or _CERO
        disponibles = fila.monto("DISPONIBLES") or _CERO
        precio = fila.monto("PRECIO CIERRE")
        promedio = fila.monto("PRECIO PROMEDIO COMPRA")
        invertido = fila.monto("MONTO INVERTIDO")
        saldo = fila.monto("SALDO ACTUAL")
        devolucion = fila.monto("DEVOLUCION") or _CERO
        mayor_menor = fila.monto("MAYOR O MENOR VALOR")
        moneda = fila.monedas.get(fila.etiqueta("PRECIO CIERRE")) or "CLP"
        moneda_promedio = fila.monedas.get(fila.etiqueta("PRECIO PROMEDIO COMPRA"))
        que = f"{cuenta} {nombre}"
        if moneda_promedio and moneda_promedio != moneda:
            self.cartola.avisos.append(
                f"{tabla} {que}: precio promedio en {moneda_promedio} y precio de cierre en {moneda}"
            )
        if total is not None:
            c.comparar(
                "Acciones y CFI: TOTAL = garantías + plazo + disponibles",
                garantias + plazo + disponibles,
                total,
                _CERO,
                que,
            )
        cambio = {"CLP": Decimal(1), "USD": self.cartola.tipo_cambio_usd, "EUR": self.cartola.tipo_cambio_eur}
        if None not in (total, precio, saldo) and cambio.get(moneda):
            c.comparar(
                "Acciones y CFI: TOTAL × precio de cierre × tipo de cambio = saldo actual",
                total * precio * cambio[moneda],
                saldo,
                _MEDIO,
                que,
            )
        if None not in (saldo, invertido, mayor_menor):
            c.comparar(
                "Acciones y CFI: saldo − monto invertido + devolución = mayor o menor valor",
                saldo - invertido + devolucion,
                mayor_menor,
                Decimal(1),
                que,
            )
        if moneda == "CLP" and None not in (total, promedio, invertido):
            c.comparar(
                "Acciones y CFI en CLP: TOTAL × precio promedio = monto invertido",
                total * promedio,
                invertido,
                _MEDIO,
                que,
            )
        nemotecnico, _, resto = nombre.partition(" - ")
        usadas = {
            fila.etiqueta(e)
            for e in ("NOMBRE", "NUMERO CUENTA", "TOTAL", "PRECIO CIERRE", "PRECIO PROMEDIO COMPRA", "SALDO ACTUAL")
        }
        self._posicion(
            Posicion(
                cuenta=cuenta,
                seccion="Acciones y CFI",
                tabla=tabla,
                previsional=bool(self.previsional),
                instrumento=resto.strip() if tabla == "CFI" and resto else nombre,
                moneda=moneda,
                cantidad=total,
                precio_promedio=promedio,
                precio_actual=precio,
                valor_clp=saldo,
                valor_usd=None,
                nemotecnico=nemotecnico.strip() if tabla == "CFI" else nombre,
                otros={k: v for k, v in fila.celdas.items() if k not in usadas},
            )
        )

    def _posicion(self, posicion: Posicion) -> None:
        if self.previsional is None:
            self.cartola.avisos.append(
                f"{posicion.tabla} {posicion.instrumento}: página sin título previsional o no previsional"
            )
        else:
            self.grupos[posicion.cuenta].add(self.previsional)
        self.cartola.posiciones.append(posicion)

    # Caja -----------------------------------------------------------------------

    def _saldo_caja(self, fila: _Fila) -> None:
        en_pesos = fila.monto("SALDO EN CAJA EN PESOS")
        if fila.total:
            self.total_caja = en_pesos
            return
        tipo = fila.texto("CAJA")
        moneda = _SALDO_CAJA.get(tipo)
        cuenta = fila.texto("NUMERO CUENTA")
        monto = fila.monto("SALDO EN CAJA SEGUN MONEDA")
        if moneda is None or monto is None:
            self.cartola.avisos.append(f"Saldo de caja no reconocido: {tipo} {cuenta}")
            return
        cambio = {"CLP": Decimal(1), "USD": self.cartola.tipo_cambio_usd, "EUR": self.cartola.tipo_cambio_eur}
        if en_pesos is not None and cambio.get(moneda):
            self.cuadraturas.comparar(
                "Caja: saldo en moneda × tipo de cambio = saldo en $",
                monto * cambio[moneda],
                en_pesos,
                _MEDIO,
                f"{cuenta} {moneda}",
            )
        if en_pesos is not None:
            self.caja_en_pesos.append(en_pesos)
        self.saldos_resumen[(moneda, cuenta)] = monto
        if monto or en_pesos:
            self.cartola.saldos_caja.append(SaldoCaja(cuenta, moneda, monto, en_pesos))

    def _movimiento_caja(self, fila: _Fila) -> None:
        caja = self.caja
        if caja is None:
            self.cartola.avisos.append("Movimiento de caja fuera de un bloque CAJA: <MONEDA>")
            return
        cuenta = fila.texto("NUMERO CUENTA")
        descripcion = re.sub(r"\s+", " ", fila.texto("DESCRIPCIÓN", "DESCRIPCION"))
        saldo = fila.monto("SALDO")
        if descripcion == "Saldo Inicial":
            self._cerrar_caja()
            caja.cuenta, caja.saldo = cuenta, saldo
            return
        if not caja.cuenta:
            # Bloque sin "Saldo Inicial": la cuenta empezó el período sin saldo.
            caja.cuenta, caja.saldo = cuenta, _CERO
        elif cuenta != caja.cuenta:
            self.cartola.avisos.append(
                f"Movimientos de caja {caja.moneda} de la cuenta {cuenta} sin título ni saldo inicial"
            )
            self._cerrar_caja()
            caja.cuenta, caja.saldo = cuenta, None
        cargo = fila.monto("CARGO") or _CERO
        abono = fila.monto("ABONO") or _CERO
        fecha = fila.texto("FECHA")
        if caja.saldo is not None and saldo is not None:
            self.cuadraturas.comparar(
                "Movimientos de caja: saldo anterior − cargo + abono = saldo",
                caja.saldo - cargo + abono,
                saldo,
                _CERO,
                f"{cuenta} {caja.moneda} {fecha}",
            )
        caja.saldo = saldo
        tipo, instrumento = _tipo_caja(descripcion, caja.moneda)
        self.cartola.movimientos_caja.append(
            MovimientoCaja(
                fecha=_fecha(fecha),
                cuenta=cuenta,
                tipo=tipo,
                moneda=caja.moneda,
                cargo=cargo,
                abono=abono,
                folio=fila.texto("DOCUMENTO"),
                instrumento=instrumento,
            )
        )

    def _cerrar_caja(self) -> None:
        caja = self.caja
        if caja is None or not caja.cuenta or caja.saldo is None:
            return
        self.saldos_movimientos[(caja.moneda, caja.cuenta)] = caja.saldo

    # Transacciones ----------------------------------------------------------------

    def _transaccion(self, fila: _Fila) -> None:
        movto = fila.texto("TIPO MOVTO")
        clave = next((k for k in TIPOS_TITULOS if _normalizar(movto).startswith(k)), None)
        instrumento = fila.texto("INSTRUMENTO")
        if clave is None:
            tipo, destino = movto.upper(), ""
            self.cartola.avisos.append(f"Transacción de tipo no reconocido: {movto} {instrumento}")
        else:
            tipo, destino = TIPOS_TITULOS[clave]
        fondo_mutuo = instrumento.startswith("FM ")
        divisa = instrumento.upper() in _DIVISAS
        if tipo in _TIPOS_NO_FM and not fondo_mutuo:
            tipo, destino = _TIPOS_NO_FM[tipo], "BOLSA"
        if tipo in _TIPOS_DIVISA and divisa:
            tipo, destino = _TIPOS_DIVISA[tipo], ""
        self.cartola.movimientos_titulos.append(
            MovimientoTitulo(
                fecha=_fecha(fila.texto("FECHA OPERACI")),
                cuenta=fila.texto("NRO CUENTA"),
                tipo=tipo,
                instrumento=instrumento,
                moneda=fila.texto("MDA"),
                cantidad=fila.monto("CANTIDAD") or _CERO,
                precio=fila.monto("PRECIO") or _CERO,
                monto=fila.monto("MONTO") or _CERO,
                referencia=fila.texto("NUMERO OPERACI"),
                nemotecnico="" if fondo_mutuo or divisa else instrumento,
                destino=destino,
            )
        )

    # Cierre ------------------------------------------------------------------------

    def cerrar(self) -> None:
        self._cerrar_caja()
        self._cuentas()
        self._controles_caja()
        self._controles_resumen()
        self._completar_fondos()
        self._corregir_monedas()
        self._controles_transacciones()
        self.cartola.controles += self.cuadraturas.controles()

    def _cuentas(self) -> None:
        cartola = self.cartola
        numeros = [p.cuenta for p in cartola.posiciones]
        numeros += [cuenta for _, cuenta in self.saldos_resumen]
        numeros += [m.cuenta for m in cartola.movimientos_caja + cartola.movimientos_titulos]
        for numero in dict.fromkeys(n for n in numeros if n):
            grupos = self.grupos.get(numero, set())
            if len(grupos) > 1:
                cartola.avisos.append(
                    f"La cuenta {numero} está en las páginas previsionales y en las no previsionales: "
                    "se deja como previsional"
                )
            elif not grupos:
                cartola.avisos.append(
                    f"La cuenta {numero} no tiene posiciones que digan si es previsional: se deja como no previsional"
                )
            previsional = True in grupos
            cartola.cuentas[numero] = Cuenta(
                numero=numero,
                portafolio="",
                grupo="Previsional" if previsional else "No previsional",
                producto_base="APV PRIME" if previsional else "CUENTA INVERSION",
            )

    def _controles_caja(self) -> None:
        c = self.cuadraturas
        for clave in sorted(self.saldos_movimientos):
            moneda, cuenta = clave
            c.comparar(
                "Movimientos de caja: último saldo = resumen de saldos en caja",
                self.saldos_movimientos[clave],
                self.saldos_resumen.get(clave, _CERO),
                _CERO,
                f"{cuenta} {moneda}",
            )
        if self.total_caja is not None:
            c.comparar(
                "Caja: suma de saldos en $ = TOTAL",
                sum(self.caja_en_pesos, _CERO),
                self.total_caja,
                max(Decimal(1), _MEDIO * len(self.caja_en_pesos)),
            )

    def _controles_resumen(self) -> None:
        """Detalle contra la página 1 (solo no previsional, salvo APV FFMM/DC) y la 2."""
        cartola, t = self.cartola, self.cartola.totales
        sumas: dict[str, Decimal] = defaultdict(Decimal)
        for p in cartola.posiciones:
            clase = "Fondos Mutuos" if p.tabla == "Fondos Mutuos" else "Acciones y CFI"
            sumas[f"productos:{clase}"] += p.valor_clp or _CERO
            if p.previsional:
                if clase == "Fondos Mutuos":
                    sumas["resumen:APV FFMM/DC"] += p.valor_clp or _CERO
            else:
                sumas[f"resumen:{clase}"] += p.valor_clp or _CERO
        nombres = {"CLP": "Disponible Peso", "USD": "Disponible Dólar", "EUR": "Disponible Euro"}
        for s in cartola.saldos_caja:
            if cartola.cuentas[s.cuenta].grupo == "No previsional":
                sumas[f"resumen:{nombres[s.moneda]}"] += s.monto_clp or _CERO
        reglas = (
            ("productos:Fondos Mutuos", "Suma de fondos mutuos = Por productos: Fondos Mutuos", 2),
            ("productos:Acciones y CFI", "Suma de acciones y CFI = Por productos: Acciones y CFI", 5),
            ("resumen:Fondos Mutuos", "Fondos mutuos no previsionales = Resumen inversión: Fondos Mutuos", 2),
            ("resumen:Acciones y CFI", "Acciones y CFI no previsionales = Resumen inversión: Acciones y CFI", 5),
            ("resumen:APV FFMM/DC", "Fondos mutuos previsionales = Resumen inversión: APV FFMM/DC", 2),
        ) + tuple(
            (f"resumen:{n}", f"Caja no previsional en {m} = Resumen inversión: {n}", 1) for m, n in nombres.items()
        )
        for clave, regla, tolerancia in reglas:
            if clave in t:
                self.cuadraturas.comparar(regla, sumas[clave], t[clave], Decimal(tolerancia))

    def _completar_fondos(self) -> None:
        """Completa el nombre de los fondos mutuos del informe de transacciones.

        El informe trae el nombre largo, truncado y sin serie ("FM SECURITY
        AGRESIVO ESTRATEGICO SE"), y el detalle de inversiones el corto con serie
        ("AGRESIVO EST SERIE I-APV"). Se toma la posición de la misma cuenta y
        moneda que empieza con la misma palabra y cuyo valor cuota al cierre está
        a menos de 5 % del de la operación.
        """
        fondos = [p for p in self.cartola.posiciones if p.tabla == "Fondos Mutuos" and p.precio_actual]
        sin_serie = set()
        for m in self.cartola.movimientos_titulos:
            if m.destino != "FFMM":
                continue
            candidatos = {
                p.instrumento
                for p in fondos
                if p.cuenta == m.cuenta
                and p.moneda == m.moneda
                and _primera_palabra(p.instrumento) == _primera_palabra(m.instrumento)
                and abs(m.precio / p.precio_actual - 1) < Decimal("0.05")
            }
            if len(candidatos) == 1:
                m.instrumento = candidatos.pop()
            else:
                sin_serie.add(m.instrumento)
        for nombre in sorted(sin_serie):
            self.cartola.avisos.append(f"Transacciones de {nombre}: no se pudo deducir la serie del fondo")

    def _corregir_monedas(self) -> None:
        """Corrige la MDA de las transacciones de CFI en moneda extranjera.

        En los dividendos de CFI en USD el precio está en USD y el monto en pesos,
        y en las compras de CFI en EUR cantidad × precio da el monto en euros,
        aunque la MDA diga CLP en los dos casos. La moneda del CFI sale de su
        precio de cierre en el detalle de inversiones.
        """
        cartola = self.cartola
        monedas: dict[tuple[str, str], str] = {}
        for p in cartola.posiciones:
            if p.nemotecnico:
                monedas[(p.cuenta, p.nemotecnico)] = p.moneda
                monedas.setdefault(("", p.nemotecnico), p.moneda)
        abonos = {(m.cuenta, m.folio, m.instrumento, m.moneda): m.abono for m in cartola.movimientos_caja}
        dividendos = []
        for m in cartola.movimientos_titulos:
            moneda = monedas.get((m.cuenta, m.nemotecnico)) or monedas.get(("", m.nemotecnico))
            if not m.nemotecnico or m.moneda != "CLP" or moneda in (None, "CLP"):
                continue
            if m.tipo == "DIVIDENDO":
                abono = abonos.get((m.cuenta, m.referencia, m.nemotecnico, moneda))
                if abono:
                    dividendos.append(m.nemotecnico)
                    m.moneda, m.monto = moneda, abono
            elif _cuadra(m.cantidad, m.precio, m.monto):
                cartola.avisos.append(
                    f"{m.tipo} {m.instrumento} cuenta {m.cuenta} del {m.fecha:%d-%m-%Y}: "
                    f"MDA CLP, pero cantidad × precio da el monto en {moneda}; se toma {moneda}"
                )
                m.moneda = moneda
        if dividendos:
            cartola.avisos.append(
                f"{len(dividendos)} dividendos de CFI en moneda extranjera vienen con MDA CLP y el monto en "
                "pesos: se toman la moneda y el monto del abono en caja con el mismo número de operación "
                f"({', '.join(sorted(set(dividendos)))})"
            )

    def _controles_transacciones(self) -> None:
        excepciones = reinvertidos = 0
        for m in self.cartola.movimientos_titulos:
            if m.tipo == "DIVIDENDO" and m.instrumento.startswith("FM "):
                reinvertidos += 1
            if not (m.cantidad and m.precio and m.monto):
                continue
            if m.tipo == "DIVIDENDO" and m.moneda == "CLP" and not _cuadra(m.cantidad, m.precio, m.monto):
                excepciones += 1
                continue
            self.cuadraturas.comparar(
                "Transacciones: cantidad × precio = monto",
                m.cantidad * m.precio,
                m.monto,
                _tolerancia_producto(m.cantidad),
                f"{m.tipo} {m.instrumento} cuenta {m.cuenta} del {m.fecha:%d-%m-%Y}",
            )
        if excepciones:
            self.cartola.avisos.append(
                f"{excepciones} dividendos con precio en moneda extranjera y monto en pesos sin abono en caja "
                "que lo confirme: no se compara cantidad × precio con el monto"
            )
        if reinvertidos:
            self.cartola.avisos.append(
                f"{reinvertidos} dividendos de fondos mutuos reinvertidos en cuotas, sin movimiento de caja: "
                "no se exportan"
            )


def _primera_palabra(nombre: str) -> str:
    resto = nombre.removeprefix("FM SECURITY ").split()
    return resto[0] if resto else ""


def _tipo_caja(descripcion: str, moneda: str) -> tuple[str, str]:
    """Tipo de movimiento en el vocabulario del export, si lo hay, y nemotécnico."""
    instrumento = ""
    resto = descripcion
    m = _NEMO_EN_DESCRIPCION.match(descripcion)
    if m:
        instrumento = m.group(2)
        resto = f"{m.group(1)} - {descripcion[m.end():]}"
    else:
        suelto = _NEMO_SUELTO.search(descripcion)
        if suelto:
            instrumento = suelto.group(1).upper()
            resto = (descripcion[: suelto.start()] + descripcion[suelto.end() :]).strip()
    for (comienzo, moneda_caja), tipo in TIPOS_CAJA.items():
        if descripcion.startswith(comienzo) and moneda == moneda_caja:
            return tipo, instrumento
    return re.sub(r"\s+", " ", resto).strip().upper(), instrumento


def _tolerancia_producto(cantidad: Decimal) -> Decimal:
    # El precio viene con 4 decimales, así que su redondeo pesa hasta 0,00005 por
    # unidad, y los montos en pesos vienen truncados a entero.
    return max(Decimal(1), abs(cantidad) * Decimal("0.00005"))


def _solapada(span: Span, columnas: list[Columna]) -> str | None:
    """Etiqueta de la columna con la que el fragmento se solapa en x, o None."""
    mejor, solape = None, 0.0
    for c in columnas:
        o = min(span.x1, c.x1) - max(span.x0, c.x0)
        if o > solape:
            mejor, solape = c.etiqueta, o
    return mejor


def _cuadra(cantidad: Decimal, precio: Decimal, monto: Decimal) -> bool:
    return abs(cantidad * precio - monto) <= _tolerancia_producto(cantidad)
