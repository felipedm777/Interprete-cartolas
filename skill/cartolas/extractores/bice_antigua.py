"""Cartola BICE Inversiones de formato antiguo (la de abril de 2026).

Página A4 vertical, organizada por moneda ($, US$ y APV $): una portada con el
resumen, una página "DETALLE DE INVERSIONES EN <moneda>" por moneda, "DETALLE
DE CARTERAS", "DETALLE DE MOVIMIENTOS" y el glosario. En la muestra casi
siempre viene seguida de una cartola Valores Security del mismo cliente en el
mismo PDF. El formato está descrito en docs/instituciones/bice-antigua-y-security.md.

No trae tipo de cambio ni portafolio, y la caja solo tiene cuenta cuando hubo
movimientos.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pymupdf

from ..catalogo import tipo_cuenta
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
from ..pdf import Span, leer_palabras

FORMATO = "BICE antigua"

_PIE = "BICE Inversiones Corredores de Bolsa S.A."
# Arriba va la barra de navegación (desde la página 2) y abajo el pie de página.
_Y_CONTENIDO = 80
_Y_PIE = 790
_TAM_TITULO_PAGINA = 11
# Los superíndices (A), (B)… miden 5 pt y van en otra línea.
_TAM_MINIMO = 6

_MONEDA = r"(\$|US\$|APV \$)"
_MONEDAS = {"$": "CLP", "US$": "USD", "APV $": "CLP"}
_NUMERO = re.compile(r"-?(\d{1,3}(\.\d{3})+|\d+)(,\d+)?%?")
_FECHA = re.compile(r"\d{2}-\d{2}-\d{4}")
_RUT = re.compile(r"\d{1,2}\.\d{3}\.\d{3}-[\dkK]")

# Bloques que se leen, por el título en negrita a la izquierda.
_BLOQUES = (
    ("resumen_cartera", re.compile(rf"Resumen Cartera en {_MONEDA} Resumen de Movimientos")),
    ("resumen_inversiones", re.compile(rf"Resumen de sus inversiones en {_MONEDA}$")),
    ("dividendos", re.compile(r"Dividendos del Período$")),
    ("renta_variable", re.compile(rf"Detalle Cartera Renta Variable en {_MONEDA}$")),
    ("fondos_mutuos", re.compile(rf"Detalle Cartera Fondos Mutuos en {_MONEDA}$")),
    ("depositos", re.compile(rf"Detalle Cartera Depósitos a Plazo en {_MONEDA}$")),
    ("caja", re.compile(rf"Detalle de movimientos de Caja en {_MONEDA}$")),
    ("titulos", re.compile(rf"Movimientos de Títulos en {_MONEDA}$")),
)
_OTRA_TABLA = re.compile(rf"(Detalle Cartera .+|Detalle de .+|Movimientos de .+) en {_MONEDA}$")
_CUENTA = re.compile(r"Cuenta Inversión: (\S+)$")

# Clase del "Resumen de sus inversiones" que corresponde a cada tabla de detalle.
_CLASE = {
    "renta_variable": "Acciones",
    "fondos_mutuos": "Fondos Mutuos",
    "depositos": "Depósitos a Plazo BICE",
}


def paginas(doc: pymupdf.Document) -> list[int]:
    """Las páginas verticales del principio que llevan el pie de BICE Inversiones."""
    return _paginas(doc)


def _paginas(doc: pymupdf.Document) -> list[int]:
    if doc.page_count == 0:
        return []
    portada = doc[0]
    texto = portada.get_text()
    if not (
        portada.rect.width < portada.rect.height
        and _PIE in texto
        and "Resumen de sus inversiones" in texto
    ):
        return []
    resultado = []
    for i, pagina in enumerate(doc):
        if pagina.rect.width > pagina.rect.height or _PIE not in pagina.get_text():
            break
        resultado.append(i)
    return resultado


# --- Líneas y bloques ------------------------------------------------------------


@dataclass
class _Linea:
    palabras: list[Span]

    @property
    def yc(self) -> float:
        return sum(p.yc for p in self.palabras) / len(self.palabras)

    @property
    def texto(self) -> str:
        return " ".join(p.texto for p in self.palabras)

    @property
    def negrita(self) -> bool:
        return all(p.negrita for p in self.palabras)

    def numeros(self) -> list[Span]:
        return [p for p in self.palabras if _es_numero(p.texto)]


@dataclass
class _Bloque:
    tipo: str
    simbolo: str
    # Moneda de la página "DETALLE DE INVERSIONES EN <moneda>" donde está.
    pagina: str = ""
    cuenta: str = ""
    lineas: list[_Linea] = field(default_factory=list)

    @property
    def moneda(self) -> str:
        return _MONEDAS[self.simbolo]

    @property
    def previsional(self) -> bool:
        return self.simbolo == "APV $"

    def encabezado(self) -> list[_Linea]:
        """Líneas en negrita y sin números del principio del bloque."""
        resultado = []
        for linea in self.lineas:
            if not linea.negrita or linea.numeros():
                break
            resultado.append(linea)
        return resultado

    def filas(self) -> list[_Linea]:
        return self.lineas[len(self.encabezado()) :]


def _es_numero(texto: str) -> bool:
    return bool(_NUMERO.fullmatch(texto))


def _lineas(pagina: pymupdf.Page) -> tuple[str, list[_Linea]]:
    """Título de la página y sus líneas de contenido, de arriba abajo."""
    palabras = [
        p
        for p in leer_palabras(pagina, blancos=True)
        if _Y_CONTENIDO < p.y0 < _Y_PIE and p.tamano >= _TAM_MINIMO
    ]
    titulo = " ".join(p.texto for p in palabras if p.tamano >= _TAM_TITULO_PAGINA)
    lineas: list[list[Span]] = []
    for p in sorted((p for p in palabras if p.tamano < _TAM_TITULO_PAGINA), key=lambda p: p.yc):
        if lineas and abs(lineas[-1][-1].yc - p.yc) <= 2.5:
            lineas[-1].append(p)
        else:
            lineas.append([p])
    return titulo, [_Linea(sorted(l, key=lambda p: p.x0)) for l in lineas]


def _ancla(encabezado: list[_Linea], texto: str, n: int = 0) -> float:
    """Borde derecho de la n-ésima palabra del encabezado con ese texto."""
    palabras = [p for linea in encabezado for p in linea.palabras if p.texto == texto]
    return sorted(palabras, key=lambda p: p.x0)[n].x1


def _celdas(palabras: list[Span], anclas: dict[str, float]) -> dict[str, str]:
    """Asigna cada palabra a la columna cuyo encabezado termina más cerca de su
    borde derecho: los números van alineados a la derecha."""
    celdas: dict[str, list[str]] = defaultdict(list)
    for p in palabras:
        columna = min(anclas, key=lambda c: abs(anclas[c] - p.x1))
        celdas[columna].append(p.texto)
    return {c: " ".join(v) for c, v in celdas.items()}


def _monto(texto: str | None) -> Decimal | None:
    return leer_monto(texto) if texto and _es_numero(texto) else None


def _fecha(texto: str) -> date:
    return datetime.strptime(texto, "%d-%m-%Y").date()


# --- Extracción --------------------------------------------------------------------


@dataclass
class _Lectura:
    """Lo leído de la cartola, incluidos los resúmenes que solo sirven para cuadrar."""

    cartola: Cartola
    portada: dict[str, list[Decimal]] = field(default_factory=dict)
    portada_grupo: dict[str, str] = field(default_factory=dict)
    # Por moneda ($, US$, APV $): columnas A, B, GP, C del resumen de cartera y
    # Inicio, D, E, F, B, Final del resumen de movimientos de caja.
    cartera: dict[str, dict[str, Decimal]] = field(default_factory=lambda: defaultdict(dict))
    mov_caja: dict[str, dict[str, Decimal]] = field(default_factory=lambda: defaultdict(dict))
    # Por moneda: filas (etiqueta, es clase, {G, H, I, CV, J, %}).
    inversiones: dict[str, list[tuple[str, bool, dict[str, Decimal]]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    dividendos: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    # Por (tabla, moneda): suma de las filas y subtotales impresos.
    tablas: dict[tuple[str, str], Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    subtotales: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    # Suma de las filas desde el último subtotal, por tabla; una tabla puede
    # seguir en la página siguiente con el subtotal ahí.
    parciales: dict[tuple[str, str], Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    # Saldo corrido de caja por (moneda, cuenta).
    saldo_caja: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    caja_final: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    controles: list[Control] = field(default_factory=list)


def extraer(ruta: str | Path, paginas: list[int] | None = None) -> Cartola:
    doc = pymupdf.open(ruta)
    if paginas is None:
        paginas = _paginas(doc)
    bloques: list[_Bloque] = []
    lectura: _Lectura | None = None
    for numero in paginas:
        titulo, lineas = _lineas(doc[numero])
        if numero == paginas[0]:
            lectura = _Lectura(_portada(lineas, str(ruta)))
            _resumen_portada(lineas, lectura)
            continue
        if titulo == "GLOSARIO":
            continue
        m = re.fullmatch(rf"DETALLE DE INVERSIONES EN {_MONEDA}", titulo)
        moneda_pagina = m.group(1) if m else ""
        bloque = None
        for linea in lineas:
            texto = linea.texto
            if texto.startswith(("Ejecutivo:", "Período:")):
                continue
            nuevo = _titulo_bloque(texto, moneda_pagina)
            if nuevo:
                # Una tabla que sigue en otra página repite título y encabezado;
                # la cuenta del bloque de movimientos se mantiene.
                anterior = bloques[-1] if bloques else None
                if anterior and (anterior.tipo, anterior.simbolo) == (nuevo.tipo, nuevo.simbolo):
                    nuevo.cuenta = anterior.cuenta
                bloque = nuevo
                bloques.append(bloque)
                continue
            if _OTRA_TABLA.match(texto) and linea.negrita:
                lectura.cartola.avisos.append(f"La cartola trae «{texto}», que este extractor no lee")
                bloque = None
                continue
            m = _CUENTA.match(texto)
            if m and bloque and bloque.tipo in ("caja", "titulos"):
                bloque = _Bloque(bloque.tipo, bloque.simbolo, bloque.pagina, m.group(1))
                bloques.append(bloque)
                continue
            if bloque:
                bloque.lineas.append(linea)
            elif linea.numeros():
                lectura.cartola.avisos.append(f"Línea sin tabla conocida en la página {numero + 1}: {texto}")
    for bloque in bloques:
        _LECTORES[bloque.tipo](bloque, lectura)
    _caja_sin_movimientos(lectura)
    lectura.cartola.controles = lectura.controles + _controles(lectura)
    return lectura.cartola


def _titulo_bloque(texto: str, moneda_pagina: str) -> _Bloque | None:
    for tipo, patron in _BLOQUES:
        m = patron.match(texto)
        if m:
            simbolo = m.group(1) if m.groups() else moneda_pagina or "$"
            return _Bloque(tipo, simbolo, moneda_pagina)
    return None


# --- Portada -----------------------------------------------------------------------


def _portada(lineas: list[_Linea], archivo: str) -> Cartola:
    nombre = rut = ""
    desde = hasta = None
    for linea in lineas:
        texto = linea.texto
        if texto.startswith("Cliente:"):
            nombre = " ".join(p.texto for p in linea.palabras[1:] if p.x1 < 410 and not p.negrita)
            for p in linea.palabras:
                if _RUT.fullmatch(p.texto):
                    rut = p.texto.replace(".", "").upper()
        m = re.match(r"Período: (\d{2}-\d{2}-\d{4}) al (\d{2}-\d{2}-\d{4})", texto)
        if m:
            desde, hasta = _fecha(m.group(1)), _fecha(m.group(2))
    if not (rut and desde):
        raise ValueError("no se encontró el RUT o el período en la portada")
    return Cartola(
        formato=FORMATO,
        archivo=archivo,
        rut=rut,
        nombre=nombre,
        desde=desde,
        hasta=hasta,
        tipo_cambio_usd=None,
        institucion="BICE",
    )


def _resumen_portada(lineas: list[_Linea], lectura: _Lectura) -> None:
    """Tabla "Resumen de sus inversiones" de la portada: columnas $, US$ y APV ($)."""
    grupo = ""
    for linea in lineas:
        texto = linea.texto
        if texto.startswith("Activos $ US$"):
            grupo = "Activos"
            continue
        if not grupo:
            continue
        numeros = linea.numeros()
        etiqueta = " ".join(p.texto for p in linea.palabras if p not in numeros)
        if not numeros:
            grupo = etiqueta
            continue
        if len(numeros) != 3:
            lectura.cartola.avisos.append(f"Resumen de la portada: fila no reconocida «{texto}»")
            continue
        lectura.portada[etiqueta] = [leer_monto(p.texto) for p in numeros]
        lectura.portada_grupo[etiqueta] = grupo
        if etiqueta == "Patrimonio":
            break


# --- Resúmenes por moneda -------------------------------------------------------------

_ETIQUETAS_CARTERA = {
    "Valor inicial": "A",
    "Abonos/Retiros": "B",
    "Ganancia/Pérdida": "GP",
    "Valor Final": "C",
}
_ETIQUETAS_MOV_CAJA = {
    "Inicio": "Inicio",
    "Compras/Aportes": "D",
    "Ventas/Rescates": "E",
    "Dividendos y Otros": "F",
    "Abonos/Retiros": "B",
    "Final": "Final",
}
# El bloque derecho (resumen de movimientos de caja) empieza en esta x.
_X_DERECHA = 280


def _resumen_cartera(bloque: _Bloque, lectura: _Lectura) -> None:
    for linea in bloque.lineas:
        for lado, etiquetas, destino in (
            (False, _ETIQUETAS_CARTERA, lectura.cartera),
            (True, _ETIQUETAS_MOV_CAJA, lectura.mov_caja),
        ):
            palabras = [p for p in linea.palabras if (p.x0 >= _X_DERECHA) == lado]
            numeros = [p for p in palabras if _es_numero(p.texto)]
            texto = " ".join(p.texto for p in palabras if p not in numeros)
            clave = next((v for k, v in etiquetas.items() if texto.startswith(k)), None)
            if clave and len(numeros) == 1:
                destino[bloque.simbolo][clave] = leer_monto(numeros[0].texto)


def _resumen_inversiones(bloque: _Bloque, lectura: _Lectura) -> None:
    encabezado = bloque.encabezado()
    fechas = [p for linea in encabezado for p in linea.palabras if _FECHA.fullmatch(p.texto)]
    anclas = {
        "G": fechas[0].x1,
        "H": _ancla(encabezado, "Aportes"),
        "I": _ancla(encabezado, "Rescates"),
        "CV": _ancla(encabezado, "Valor"),
        "J": fechas[1].x1,
        "%": _ancla(encabezado, "%"),
    }
    limite = fechas[0].x0 - 5
    for linea in bloque.filas():
        etiqueta = [p for p in linea.palabras if p.x1 < limite]
        valores = _celdas([p for p in linea.palabras if p.x1 >= limite], anclas)
        fila = {k: leer_monto(v) for k, v in valores.items()}
        # Las filas de clase (Acciones, Fondos Mutuos…) tienen la etiqueta en negrita.
        es_clase = all(p.negrita for p in etiqueta)
        lectura.inversiones[bloque.simbolo].append((" ".join(p.texto for p in etiqueta), es_clase, fila))


def _dividendos(bloque: _Bloque, lectura: _Lectura) -> None:
    encabezado = bloque.encabezado()
    monto = _ancla(encabezado, "Dividendo")
    for linea in bloque.filas():
        numeros = [p for p in linea.numeros() if abs(p.x1 - monto) < 20]
        if numeros:
            lectura.dividendos[bloque.simbolo] += leer_monto(numeros[0].texto)


# --- Carteras ----------------------------------------------------------------------


def _cuenta(lectura: _Lectura, numero: str, previsional: bool) -> None:
    if numero not in lectura.cartola.cuentas:
        grupo = "APV" if previsional else "Cuenta de Inversión"
        lectura.cartola.cuentas[numero] = Cuenta(numero, "", grupo)
        if tipo_cuenta(numero) is None:
            lectura.cartola.avisos.append(f"Cuenta {numero}: no se sabe su producto base ni régimen")


def _subtotal(linea: _Linea, tabla: tuple[str, str], lectura: _Lectura) -> bool:
    """Controla las filas de subtotal; True si la línea era un subtotal."""
    texto = linea.texto
    if not texto.startswith("Subtotal"):
        return False
    impreso = leer_monto(linea.numeros()[0].texto)
    if texto.startswith("Subtotal Cartera"):
        lectura.subtotales[tabla] = impreso
    else:
        etiqueta = texto.split(":")[0]
        lectura.controles.append(
            _comparar(f"{etiqueta} en {tabla[1]} = suma de sus filas", lectura.parciales[tabla], impreso, tabla[1])
        )
        lectura.parciales[tabla] = Decimal(0)
    return True


def _renta_variable(bloque: _Bloque, lectura: _Lectura) -> None:
    encabezado = bloque.encabezado()
    anclas = {
        "cuenta": _ancla(encabezado, "Inversión"),
        "libre": _ancla(encabezado, "Libre"),
        "garantia": _ancla(encabezado, "Garantía"),
        "plazo": _ancla(encabezado, "Plazo"),
        "compra": _ancla(encabezado, "Compra"),
        "ultimo": _ancla(encabezado, "Último"),
        "dividendos": _ancla(encabezado, "Periodo"),
        "valor": _ancla(encabezado, "Mercado"),
    }
    limite = min(p.x0 for linea in encabezado for p in linea.palabras if p.texto != "Instrumento") - 5
    tabla = ("renta_variable", bloque.simbolo)
    for linea in bloque.filas():
        if _subtotal(linea, tabla, lectura):
            continue
        nemo = " ".join(p.texto for p in linea.palabras if p.x1 < limite)
        c = _celdas([p for p in linea.palabras if p.x1 >= limite], anclas)
        valor = leer_monto(c["valor"])
        cantidad = sum(leer_monto(c.get(k, "0")) for k in ("libre", "garantia", "plazo"))
        _cuenta(lectura, c["cuenta"], bloque.previsional)
        lectura.cartola.posiciones.append(
            Posicion(
                cuenta=c["cuenta"],
                seccion="Renta Variable",
                tabla="CFI" if nemo.startswith("CFI") else "Acciones",
                previsional=bloque.previsional,
                instrumento=nemo,
                moneda=bloque.moneda,
                cantidad=cantidad,
                precio_promedio=_monto(c.get("compra")),
                precio_actual=_monto(c.get("ultimo")),
                valor_clp=valor if bloque.moneda == "CLP" else None,
                valor_usd=valor if bloque.moneda == "USD" else None,
                nemotecnico=nemo,
                otros={k: c[k] for k in ("garantia", "plazo", "dividendos") if k in c},
            )
        )
        lectura.tablas[tabla] += valor
        lectura.parciales[tabla] += valor


def _fondos_mutuos(bloque: _Bloque, lectura: _Lectura) -> None:
    encabezado = bloque.encabezado()
    anclas = {
        "cuenta": _ancla(encabezado, "Inversión"),
        "fondo": _ancla(encabezado, "Fondo"),
        "valor_cuota": _ancla(encabezado, "Cuota"),
        "libres": _ancla(encabezado, "Libres"),
        "garantia": _ancla(encabezado, "Garantía"),
        "saldo": max(p.x1 for linea in encabezado for p in linea.palabras),
    }
    limite = min(p.x0 for linea in encabezado for p in linea.palabras if p.texto != "Instrumento") - 5
    tabla = ("fondos_mutuos", bloque.simbolo)
    for linea in bloque.filas():
        if _subtotal(linea, tabla, lectura):
            continue
        nombre = " ".join(p.texto for p in linea.palabras if p.x1 < limite)
        c = _celdas([p for p in linea.palabras if p.x1 >= limite], anclas)
        saldo = leer_monto(c["saldo"])
        # En APV, "Cuenta Inversión" trae el régimen (DAPV-A) y la cuenta va en
        # "Cuenta Fondo"; fuera de APV, "Cuenta Fondo" es la cuenta en el fondo.
        cuenta = c["fondo"] if bloque.previsional else c["cuenta"]
        _cuenta(lectura, cuenta, bloque.previsional)
        otros = {"Cuenta Fondo": c["fondo"]} if not bloque.previsional else {"Cuenta Inversión": c["cuenta"]}
        lectura.cartola.posiciones.append(
            Posicion(
                cuenta=cuenta,
                seccion="Fondos Mutuos",
                # Los fondos de inversión de BICE AGF aparecen entre los fondos mutuos.
                tabla="Fondos Inversión Bice" if nombre.startswith("FI BICE") else "Fondos Mutuos",
                previsional=bloque.previsional,
                instrumento=nombre,
                moneda=bloque.moneda,
                cantidad=leer_monto(c["libres"]) + leer_monto(c.get("garantia", "0")),
                precio_promedio=None,
                precio_actual=leer_monto(c["valor_cuota"]),
                valor_clp=saldo if bloque.moneda == "CLP" else None,
                valor_usd=saldo if bloque.moneda == "USD" else None,
                otros=otros,
            )
        )
        lectura.tablas[tabla] += saldo
        lectura.parciales[tabla] += saldo


def _depositos(bloque: _Bloque, lectura: _Lectura) -> None:
    """Depósitos a plazo: se leen para cuadrar y para el reporte; no tienen cuenta
    ni archivo de destino."""
    encabezado = bloque.encabezado()
    anclas = {
        "folio": _ancla(encabezado, "Folio"),
        "tipo": _ancla(encabezado, "Tipo"),
        "moneda": _ancla(encabezado, "Origen"),
        "captacion": _ancla(encabezado, "Captación"),
        "vencimiento": _ancla(encabezado, "Vencimiento"),
        "total": _ancla(encabezado, "plazo"),
        "total_vencimiento": _ancla(encabezado, "Vencimiento", 1),
    }
    limite = min(p.x0 for linea in encabezado for p in linea.palabras if p.texto != "Instrumento") - 5
    tabla = ("depositos", bloque.simbolo)
    for linea in bloque.filas():
        if _subtotal(linea, tabla, lectura):
            continue
        if not linea.numeros():
            continue  # notas al pie de la tabla
        nombre = " ".join(p.texto for p in linea.palabras if p.x1 < limite)
        c = _celdas([p for p in linea.palabras if p.x1 >= limite], anclas)
        total = leer_monto(c["total"])
        lectura.cartola.posiciones.append(
            Posicion(
                cuenta="",
                seccion="Depósitos a Plazo",
                tabla="Depósitos a Plazo",
                previsional=bloque.previsional,
                instrumento=nombre,
                moneda=bloque.moneda,
                cantidad=None,
                precio_promedio=None,
                precio_actual=None,
                valor_clp=total if bloque.moneda == "CLP" else None,
                valor_usd=total if bloque.moneda == "USD" else None,
                otros={k: v for k, v in c.items() if k != "total"},
            )
        )
        lectura.tablas[tabla] += total
        lectura.parciales[tabla] += total


# --- Movimientos -------------------------------------------------------------------


def _caja(bloque: _Bloque, lectura: _Lectura) -> None:
    if not bloque.lineas:
        return
    encabezado = bloque.encabezado()
    anclas = {
        "abono": _ancla(encabezado, "Abono"),
        "cargo": _ancla(encabezado, "Cargo"),
        "saldo": _ancla(encabezado, "Saldo"),
    }
    # El tipo de movimiento empieza bajo el folio y termina antes de la columna
    # Instrumento; los montos están a la derecha de esta.
    x_instrumento = next(p.x0 for l in encabezado for p in l.palabras if p.texto == "Instrumento") - 6
    x_montos = next(p.x0 for l in encabezado for p in l.palabras if p.texto == "Abono") - 20
    simbolo, cuenta = bloque.simbolo, bloque.cuenta
    _cuenta(lectura, cuenta, bloque.previsional)
    saldo = lectura.saldo_caja.get((simbolo, cuenta))
    for linea in bloque.filas():
        texto = linea.texto
        if texto.startswith("SALDO INICIAL CAJA"):
            saldo = lectura.saldo_caja[(simbolo, cuenta)] = leer_monto(linea.numeros()[-1].texto)
            continue
        if texto.startswith("SALDO FINAL CAJA"):
            final = leer_monto(linea.numeros()[-1].texto)
            regla = f"Saldo inicial + abonos − cargos = saldo final de caja en {simbolo}, cuenta {cuenta}"
            lectura.controles.append(_comparar(regla, saldo if saldo is not None else Decimal(0), final, simbolo))
            lectura.caja_final[simbolo] += final
            if final:
                lectura.cartola.saldos_caja.append(
                    SaldoCaja(cuenta, bloque.moneda, final, final if bloque.moneda == "CLP" else None)
                )
            continue
        palabras = linea.palabras
        if not _FECHA.fullmatch(palabras[0].texto):
            continue  # SIN MOVIMIENTOS
        folio = palabras[1].texto if len(palabras) > 1 and _es_numero(palabras[1].texto) else ""
        resto = palabras[2:] if folio else palabras[1:]
        tipo = " ".join(p.texto for p in resto if p.x0 < x_instrumento)
        instrumento = " ".join(p.texto for p in resto if x_instrumento <= p.x0 < x_montos)
        c = _celdas([p for p in resto if p.x0 >= x_montos], anclas)
        abono, cargo, nuevo = (leer_monto(c.get(k, "0")) for k in ("abono", "cargo", "saldo"))
        if saldo is not None:
            regla = f"Saldo anterior + abono − cargo = saldo, caja {simbolo} cuenta {cuenta} folio {folio}"
            lectura.controles.append(_comparar(regla, saldo + abono - cargo, nuevo, simbolo))
        saldo = lectura.saldo_caja[(simbolo, cuenta)] = nuevo
        lectura.cartola.movimientos_caja.append(
            MovimientoCaja(
                fecha=_fecha(palabras[0].texto),
                cuenta=cuenta,
                tipo=tipo,
                moneda=bloque.moneda,
                cargo=cargo,
                abono=abono,
                folio=folio.replace(".", ""),
                instrumento=instrumento,
            )
        )


def _titulos(bloque: _Bloque, lectura: _Lectura) -> None:
    if not bloque.lineas:
        return
    encabezado = bloque.encabezado()
    anclas = {
        "cantidad": _ancla(encabezado, "Cantidad"),
        "precio": _ancla(encabezado, "TIR"),
        "monto": _ancla(encabezado, "Neto"),
    }
    x_instrumento = _ancla(encabezado, "Operación") + 15
    x_montos = _ancla(encabezado, "P/B")
    cuenta = bloque.cuenta
    _cuenta(lectura, cuenta, bloque.previsional)
    filas = [l for l in bloque.filas() if _FECHA.fullmatch(l.palabras[0].texto)]
    # El instrumento de un fondo mutuo que no cabe se parte en una línea arriba
    # y otra abajo de la fila; cada pedazo va con la fila más cercana.
    instrumento: dict[int, list[Span]] = defaultdict(list)
    for linea in bloque.filas():
        if linea in filas:
            instrumento[id(linea)] += [p for p in linea.palabras if x_instrumento <= p.x0 < x_montos]
        elif filas:
            fila = min(filas, key=lambda f: abs(f.yc - linea.yc))
            if abs(fila.yc - linea.yc) <= 10:
                instrumento[id(fila)] += linea.palabras
    for fila in filas:
        palabras = fila.palabras
        referencia = palabras[1].texto if _es_numero(palabras[1].texto) else ""
        operacion = " ".join(
            p.texto for p in palabras[2 if referencia else 1 :] if p.x0 < x_instrumento
        )
        texto = " ".join(p.texto for p in sorted(instrumento[id(fila)], key=lambda p: (round(p.yc), p.x0)))
        nombre, nemotecnico = texto, ""
        m = re.fullmatch(r"(.*?)\s*-\s*CUENTA FONDO:\s*(\S+)", texto)
        if m:
            nombre = m.group(1)
        elif " " not in texto:
            nemotecnico = texto
        c = _celdas([p for p in palabras if p.x0 >= x_montos], anclas)
        lectura.cartola.movimientos_titulos.append(
            MovimientoTitulo(
                fecha=_fecha(palabras[0].texto),
                cuenta=cuenta,
                tipo=operacion,
                instrumento=nombre,
                moneda=bloque.moneda,
                cantidad=leer_monto(c["cantidad"]),
                precio=leer_monto(c["precio"]),
                monto=leer_monto(c["monto"]),
                referencia=referencia.replace(".", ""),
                nemotecnico=nemotecnico,
            )
        )


_LECTORES = {
    "resumen_cartera": _resumen_cartera,
    "resumen_inversiones": _resumen_inversiones,
    "dividendos": _dividendos,
    "renta_variable": _renta_variable,
    "fondos_mutuos": _fondos_mutuos,
    "depositos": _depositos,
    "caja": _caja,
    "titulos": _titulos,
}


def _caja_sin_movimientos(lectura: _Lectura) -> None:
    """Si una moneda tiene caja pero no detalle de movimientos, la cartola no dice
    de qué cuenta es; se asigna a la única cuenta de inversión si hay solo una."""
    cartola = lectura.cartola
    for simbolo, filas in lectura.inversiones.items():
        disponible = _fila(filas, "Disponible en Caja").get("J", Decimal(0))
        if not disponible or simbolo in lectura.caja_final:
            continue
        cuentas = sorted({n for n, c in cartola.cuentas.items() if c.grupo != "APV"})
        if simbolo != "APV $" and len(cuentas) == 1:
            moneda = _MONEDAS[simbolo]
            cartola.saldos_caja.append(
                SaldoCaja(cuentas[0], moneda, disponible, disponible if moneda == "CLP" else None)
            )
            cartola.avisos.append(
                f"Caja en {simbolo} sin detalle de movimientos: se asignó a la cuenta {cuentas[0]}, la única de la cartola"
            )
        else:
            cartola.avisos.append(
                f"Caja en {simbolo} ({disponible}) sin detalle de movimientos: la cartola no dice de qué cuenta es y no se exporta"
            )
        lectura.caja_final[simbolo] = disponible


# --- Cuadraturas -------------------------------------------------------------------


def _comparar(regla: str, calculado: Decimal, impreso: Decimal, simbolo: str) -> Control:
    # Pesos sin decimales y dólares con 2: las sumas impresas cuadran exactas,
    # salvo el redondeo de la última cifra.
    tolerancia = Decimal("0.011") if simbolo == "US$" else Decimal(1)
    diferencia = calculado - impreso
    detalle = "" if diferencia == 0 else f"calculado {calculado}, impreso {impreso}, diferencia {diferencia}"
    return Control(regla, abs(diferencia) <= tolerancia, detalle)


def _fila(filas: list[tuple[str, bool, dict[str, Decimal]]], etiqueta: str) -> dict[str, Decimal]:
    return next((f for e, _, f in filas if e == etiqueta), {})


def _controles(lectura: _Lectura) -> list[Control]:
    controles = []
    portada, grupo = lectura.portada, lectura.portada_grupo
    columnas = ("$", "US$", "APV $")
    if "Total Activos" in portada and "Patrimonio" in portada:
        for j, simbolo in enumerate(columnas):
            activos = sum(v[j] for e, v in portada.items() if grupo[e] == "Activos" and e != "Total Activos")
            controles.append(
                _comparar(f"Portada: suma de activos = Total Activos en {simbolo}", activos, portada["Total Activos"][j], simbolo)
            )
            otros = sum(v[j] for e, v in portada.items() if grupo[e] == "Otros Activos y Derivados")
            pasivos = portada.get("Total Pasivos", [Decimal(0)] * 3)[j]
            controles.append(
                _comparar(
                    f"Portada: Total Activos + otros − pasivos = Patrimonio en {simbolo}",
                    portada["Total Activos"][j] + otros - pasivos,
                    portada["Patrimonio"][j],
                    simbolo,
                )
            )

    for simbolo, filas in lectura.inversiones.items():
        total = _fila(filas, "Total Activos")
        clases: dict[str, dict[str, Decimal]] = {}
        sumas: dict[str, dict[str, Decimal]] = {}
        clase = ""
        for etiqueta, es_clase, fila in filas:
            if etiqueta in ("Total Activos", "Patrimonio"):
                continue
            if es_clase:
                clase = etiqueta
                clases[clase] = fila
                continue
            suma = sumas.setdefault(clase, defaultdict(Decimal))
            for k, v in fila.items():
                suma[k] += v
            # Las renovaciones de depósitos a plazo no aparecen como compras.
            if clase != "Depósitos a Plazo BICE":
                controles.append(
                    _comparar(
                        f"Resumen en {simbolo}: saldo inicial + compras − ventas + cambio de valor = saldo final, {etiqueta}",
                        fila.get("G", 0) + fila.get("H", 0) - fila.get("I", 0) + fila.get("CV", 0),
                        fila.get("J", Decimal(0)),
                        simbolo,
                    )
                )
        for clase, suma in sumas.items():
            for k in ("G", "H", "I", "CV", "J"):
                controles.append(
                    _comparar(f"Resumen en {simbolo}: suma de {clase} ({k})", suma[k], clases[clase].get(k, Decimal(0)), simbolo)
                )
        for k in ("G", "H", "I", "CV", "J"):
            controles.append(
                _comparar(
                    f"Resumen en {simbolo}: suma de clases = Total Activos ({k})",
                    sum((c.get(k, Decimal(0)) for c in clases.values()), Decimal(0)),
                    total.get(k, Decimal(0)),
                    simbolo,
                )
            )
        if "Total Activos" in portada:
            controles.append(
                _comparar(
                    f"Resumen en {simbolo}: Total Activos = el de la portada",
                    total.get("J", Decimal(0)),
                    portada["Total Activos"][columnas.index(simbolo)],
                    simbolo,
                )
            )

        cartera, caja = lectura.cartera.get(simbolo, {}), lectura.mov_caja.get(simbolo, {})
        dap = clases.get("Depósitos a Plazo BICE", {})
        if len(cartera) == 4:
            controles.append(_comparar(f"Resumen cartera {simbolo}: valor inicial = saldo inicial del resumen", cartera["A"], total.get("G", Decimal(0)), simbolo))
            controles.append(_comparar(f"Resumen cartera {simbolo}: valor final = saldo final del resumen", cartera["C"], total.get("J", Decimal(0)), simbolo))
            # La ganancia o pérdida no incluye los depósitos a plazo.
            delta_dap = dap.get("J", Decimal(0)) - dap.get("G", Decimal(0))
            controles.append(
                _comparar(
                    f"Resumen cartera {simbolo}: inicial + abonos/retiros + ganancia + variación de depósitos = final",
                    cartera["A"] + cartera["B"] + cartera["GP"] + delta_dap,
                    cartera["C"],
                    simbolo,
                )
            )
        if len(caja) == 6:
            controles.append(
                _comparar(
                    f"Movimientos de caja {simbolo}: inicio − compras + ventas + dividendos + abonos = final",
                    caja["Inicio"] - caja["D"] + caja["E"] + caja["F"] + caja["B"],
                    caja["Final"],
                    simbolo,
                )
            )
            controles.append(_comparar(f"Movimientos de caja {simbolo}: compras = compras del resumen", caja["D"], total.get("H", Decimal(0)), simbolo))
            controles.append(_comparar(f"Movimientos de caja {simbolo}: ventas = ventas del resumen", caja["E"], total.get("I", Decimal(0)), simbolo))
            if "B" in cartera:
                controles.append(_comparar(f"Movimientos de caja {simbolo}: abonos/retiros = los del resumen de cartera", caja["B"], cartera["B"], simbolo))
            disponible = _fila(filas, "Disponible en Caja").get("J", Decimal(0))
            controles.append(_comparar(f"Movimientos de caja {simbolo}: final = disponible en caja", caja["Final"], disponible, simbolo))
            if simbolo in lectura.caja_final:
                controles.append(
                    _comparar(f"Detalle de caja {simbolo}: suma de saldos finales = disponible en caja", lectura.caja_final[simbolo], disponible, simbolo)
                )
        if simbolo in lectura.dividendos:
            controles.append(
                _comparar(f"Dividendos del período {simbolo} = dividendos y otros del resumen de caja", lectura.dividendos[simbolo], caja.get("F", Decimal(0)), simbolo)
            )

    for (tipo, simbolo), suma in lectura.tablas.items():
        nombre = tipo.replace("_", " ")
        controles.append(
            _comparar(f"Detalle de {nombre} en {simbolo}: suma de filas = subtotal de la cartera", suma, lectura.subtotales.get((tipo, simbolo), Decimal(0)), simbolo)
        )
        clase = _fila(lectura.inversiones.get(simbolo, []), _CLASE[tipo])
        controles.append(
            _comparar(f"Detalle de {nombre} en {simbolo}: suma de filas = {_CLASE[tipo]} del resumen", suma, clase.get("J", Decimal(0)), simbolo)
        )
    return controles
