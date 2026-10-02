"""Cartola BICE Inversiones, formato vigente desde septiembre de 2026.

Página A4 apaisada con una portada, resúmenes, una página "Detalle de ..." por
clase de activo y las páginas de movimientos. El detalle del formato está en
docs/instituciones/bice-nueva.md.
"""

import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pymupdf

from ..modelo import (
    Cartola,
    Cuenta,
    MovimientoCaja,
    MovimientoTitulo,
    Posicion,
    SaldoCaja,
)
from ..numeros import leer_monto
from ..pdf import Span, armar_columnas, columna_de, leer_spans

FORMATO = "BICE nueva"

# Por debajo de esta altura empieza el contenido; arriba van título y número de página.
_Y_CONTENIDO = 70
# Las etiquetas de fila y los nombres de instrumento están a la izquierda de esta x.
_X_IZQUIERDA = 60
_TAM_ENCABEZADO = 6.2


def reconoce(doc: pymupdf.Document) -> bool:
    if doc.page_count < 3:
        return False
    portada = doc[0].get_text()
    return (
        "BICE" in portada
        and "Información del cliente" in portada
        and _titulo(doc[1]) == "Resumen de tus inversiones"
    )


def extraer(ruta: str | Path) -> Cartola:
    doc = pymupdf.open(ruta)
    cartola = _portada(doc[0], str(ruta))
    titulo_anterior, bloque_anterior = None, None
    for pagina in doc:
        titulo = _titulo(pagina)
        spans = [s for s in leer_spans(pagina) if s.y0 > _Y_CONTENIDO]
        if titulo == "Resumen por tipo de cuentas":
            _resumen_cuentas(spans, cartola)
        elif titulo == "Detalle de Caja":
            _detalle_caja(spans, cartola)
        elif titulo.startswith("Detalle de "):
            # Una sección larga sigue en la página siguiente con el mismo título y
            # sin repetir el bloque, así que se hereda el de la página anterior.
            heredado = bloque_anterior if titulo == titulo_anterior else None
            bloque_anterior = _detalle_posiciones(titulo, spans, cartola, heredado)
        elif titulo == "Movimiento de Caja":
            _movimientos_caja(spans, cartola)
        elif titulo == "Movimiento de Títulos":
            _movimientos_titulos(spans, cartola)
        titulo_anterior = titulo
    return cartola


# --- Portada -----------------------------------------------------------------

_MESES = {
    m: i
    for i, m in enumerate(
        "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
        1,
    )
}


def _portada(pagina: pymupdf.Page, archivo: str) -> Cartola:
    spans = leer_spans(pagina)
    etiquetas = sorted((s for s in spans if s.texto.endswith(":") and s.x0 < 620), key=lambda s: s.y0)
    valores: dict[str, list[str]] = defaultdict(list)
    for v in sorted((s for s in spans if s.x0 > 620), key=lambda s: s.y0):
        arriba = [e for e in etiquetas if e.y0 <= v.y0 + 2]
        if arriba:
            valores[arriba[-1].texto].append(v.texto)

    def valor(etiqueta: str) -> str:
        return " ".join(valores.get(etiqueta, []))

    rut = valor("Rut:").replace(".", "").upper()
    periodo = re.search(r"(\d{2}/\d{2}/\d{4}) al (\d{2}/\d{2}/\d{4})", valor("Fecha del Reporte:"))
    if not rut or not periodo:
        raise ValueError(f"{archivo}: no se encontró el RUT o el período en la portada")
    tc = re.search(r"([\d.,]+)\s*\(CLP/USD\)", valor("Tipo de Cambio Reporte:"))
    return Cartola(
        formato=FORMATO,
        archivo=archivo,
        rut=rut,
        nombre=valor("Nombre:"),
        desde=_fecha(periodo.group(1), "%d/%m/%Y"),
        hasta=_fecha(periodo.group(2), "%d/%m/%Y"),
        tipo_cambio_usd=leer_monto(tc.group(1)) if tc else None,
    )


def _fecha(texto: str, formato: str) -> date:
    return datetime.strptime(texto.strip(), formato).date()


def _titulo(pagina: pymupdf.Page) -> str:
    grandes = [s for s in leer_spans(pagina) if s.tamano >= 16 and s.y0 < 50 and s.x0 < 400]
    return " ".join(s.texto for s in sorted(grandes, key=lambda s: s.x0))


# --- Tablas de resumen (filas con etiqueta a la izquierda) --------------------


def _grilla(spans: list[Span]) -> list[dict]:
    """Filas de "Resumen por tipo de cuentas" y "Detalle de Caja".

    Cada fila tiene la etiqueta de la izquierda (grupo en negrita, portafolio o
    Total) y sus celdas por columna. Las celdas de 2 líneas ($ arriba y US$
    abajo) quedan juntas en la misma celda.
    """
    etiquetas = sorted(
        (s for s in spans if s.x0 < _X_IZQUIERDA and s.tamano >= 6 and s.tamano < 8),
        key=lambda s: s.y0,
    )
    if not etiquetas:
        return []
    primera = etiquetas[0].y0
    encabezados = [
        s for s in spans if s.negrita and s.x0 > 100 and s.y1 < primera - 2 and s.tamano < 7
    ]
    columnas = armar_columnas(encabezados)
    filas = [
        {"etiqueta": e.texto, "negrita": e.negrita, "yc": e.yc, "celdas": defaultdict(list)}
        for e in etiquetas
    ]
    for s in spans:
        if s.x0 < 100 or s in encabezados or s.y0 < primera - 8 or s.tamano >= 7:
            continue
        fila = min(filas, key=lambda f: abs(f["yc"] - s.yc))
        if abs(fila["yc"] - s.yc) <= 11:
            fila["celdas"][columna_de(s, columnas)].append(s)
    return filas


def _montos(celda: list[Span]) -> dict[str, Decimal]:
    """Separa una celda en su monto en pesos ("$") y en dólares ("US$")."""
    out = {}
    for s in celda:
        moneda = "USD" if s.texto.startswith(("US$", "USD")) else "CLP"
        out[moneda] = leer_monto(s.texto)
    return out


def _resumen_cuentas(spans: list[Span], cartola: Cartola) -> None:
    grupo = ""
    for fila in _grilla(spans):
        patrimonio = _montos(fila["celdas"].get("Patrimonio", [])).get("CLP")
        if fila["etiqueta"] == "Total":
            if patrimonio is not None:
                cartola.totales["patrimonio"] = patrimonio
        elif fila["negrita"]:
            grupo = fila["etiqueta"]
            if patrimonio is not None:
                cartola.totales[f"grupo:{grupo}"] = patrimonio
        else:
            numero = " ".join(s.texto for s in fila["celdas"].get("Número cuenta", []))
            if not numero:
                cartola.avisos.append(f"Portafolio sin número de cuenta: {fila['etiqueta']}")
                continue
            cartola.cuentas[numero] = Cuenta(numero, fila["etiqueta"], grupo)
            if patrimonio is not None:
                cartola.totales[f"cuenta:{numero}"] = patrimonio


def _detalle_caja(spans: list[Span], cartola: Cartola) -> None:
    for fila in _grilla(spans):
        celdas = fila["celdas"]
        valor = _montos(celdas.get("Valor de Mercado", [])).get("CLP", Decimal(0))
        if fila["etiqueta"] == "Total":
            cartola.totales["caja"] = valor
            continue
        if fila["negrita"]:
            continue
        numero = " ".join(s.texto for s in celdas.get("Número cuenta", []))
        pesos = _montos(celdas.get("Pesos", [])).get("CLP")
        dolar = _montos(celdas.get("Dólar", []))
        euro = _montos(celdas.get("Euro", [])).get("CLP")
        if pesos:
            cartola.saldos_caja.append(SaldoCaja(numero, "CLP", pesos, pesos))
        if dolar.get("CLP") or dolar.get("USD"):
            # El detalle muestra los dólares redondeados a entero; los centavos se
            # recuperan del equivalente en pesos, que se calculó con los dólares exactos.
            clp = dolar.get("CLP")
            usd = dolar.get("USD", Decimal(0))
            if clp is not None and cartola.tipo_cambio_usd:
                usd = (clp / cartola.tipo_cambio_usd).quantize(Decimal("0.01"))
            cartola.saldos_caja.append(SaldoCaja(numero, "USD", usd, clp))
        if euro:
            cartola.avisos.append(f"Caja en euros en la cuenta {numero}: no se exporta")
        cartola.totales[f"caja:{numero}"] = valor


# --- Tablas de detalle y movimientos (columnas con encabezado) ---------------


def _tablas(spans: list[Span]) -> list[dict]:
    """Tablas de una página "Detalle de ..." o de movimientos.

    Una tabla empieza en un nombre en negrita a la izquierda (p. ej. "Fondos
    Mutuos" o "Fecha") con al menos 3 encabezados en negrita en la misma banda.
    Cada fila se ancla en su celda de la primera columna (número de cuenta) o
    en "Total", y los demás fragmentos se asignan a la fila más cercana.
    """
    bloques = sorted(
        (s for s in spans if s.negrita and s.tamano == 7.0 and s.x0 < _X_IZQUIERDA),
        key=lambda s: s.y0,
    )
    tablas = []
    for nombre in sorted(spans, key=lambda s: s.y0):
        if not (
            nombre.negrita
            and nombre.x0 < _X_IZQUIERDA
            and nombre.tamano in (_TAM_ENCABEZADO, 8.2)
            and nombre.texto != "Total"
        ):
            continue
        encabezados = [
            s
            for s in spans
            if s.negrita
            and abs(s.tamano - _TAM_ENCABEZADO) < 0.15
            and s is not nombre
            and abs(s.yc - nombre.yc) <= 10
            and s.x0 > nombre.x1
        ]
        if len(encabezados) >= 3:
            tablas.append(
                {"nombre": nombre.texto, "y": nombre.y0, "columnas": armar_columnas(encabezados)}
            )

    resultado = []
    for i, tabla in enumerate(tablas):
        columnas = tabla["columnas"]
        y_ini = max(c.y1 for c in columnas)
        y_fin = tablas[i + 1]["y"] - 12 if i + 1 < len(tablas) else 10_000
        siguientes = [b for b in bloques if b.y0 > tabla["y"]]
        if siguientes:
            y_fin = min(y_fin, siguientes[0].y0 - 2)
        anteriores = [b for b in bloques if b.y0 < tabla["y"]]
        bloque = None
        if anteriores:
            b = anteriores[-1]
            bloque = " ".join(
                s.texto for s in sorted(spans, key=lambda s: s.x0) if abs(s.yc - b.yc) < 2 and s.tamano == 7.0
            )
        region = [s for s in spans if y_ini < s.y0 < y_fin]
        x_primera = min(c.x0 for c in columnas)
        primera = min(columnas, key=lambda c: c.x0).etiqueta
        izquierda = [s for s in region if s.x1 <= x_primera + 2 or s.x0 < _X_IZQUIERDA]
        anclas = [s for s in izquierda if s.texto == "Total" and s.negrita]
        anclas += [
            s
            for s in region
            if s not in izquierda and not s.negrita and columna_de(s, columnas) == primera
        ]
        anclas.sort(key=lambda s: s.yc)
        if not anclas:
            continue
        filas = {id(a): {"ancla": a, "spans": []} for a in anclas}
        for s in region:
            if any(s is a for a in anclas):
                continue
            # Los nombres largos envuelven unos 6 pt arriba y abajo de la fila;
            # un fragmento muy por encima de un ancla pertenece a la fila anterior.
            a = min(anclas, key=lambda a: abs(a.yc - s.yc) + (0 if s.yc >= a.yc - 9 else 50))
            filas[id(a)]["spans"].append(s)
        salida = []
        for a in anclas:
            fila = {
                "total": a.texto == "Total",
                "nombre": [],
                "detalle": [],
                "izquierda": [],
                "celdas": defaultdict(list),
            }
            if a.texto != "Total":
                fila["celdas"][primera].append(a)
            for s in sorted(filas[id(a)]["spans"], key=lambda s: (s.y0, s.x0)):
                if s in izquierda:
                    if s.x0 < _X_IZQUIERDA and s.tamano >= 6.0:
                        fila["izquierda"].append(s.texto)
                    if s.tamano <= 5.0:
                        fila["detalle"].append(s.texto)
                    else:
                        fila["nombre"].append(s.texto)
                else:
                    fila["celdas"][columna_de(s, columnas)].append(s)
            salida.append(fila)
        resultado.append({"nombre": tabla["nombre"], "bloque": bloque, "filas": salida})
    return resultado


def _texto(celda: list[Span]) -> str:
    return " ".join(s.texto for s in sorted(celda, key=lambda s: (s.y0, s.x0)))


def _numero(celda: list[Span], decimal: str = ",") -> Decimal | None:
    return leer_monto(celda[0].texto, decimal) if celda else None


def _detalle_posiciones(
    titulo: str, spans: list[Span], cartola: Cartola, heredado: str | None
) -> str | None:
    seccion = titulo.removeprefix("Detalle de ")
    bloque = heredado
    for tabla in _tablas(spans):
        bloque = tabla["bloque"] or bloque
        previsional = bool(bloque and "Previsional" in bloque)
        clave = f"total:{seccion}{' APV' if previsional else ''}"
        for fila in tabla["filas"]:
            celdas = fila["celdas"]
            valor = _montos(celdas.get("Valor de mercado", []))
            if fila["total"]:
                cartola.totales[clave] = valor.get("CLP", Decimal(0))
                continue
            cartola.posiciones.append(_posicion(seccion, tabla["nombre"], previsional, fila, valor))
    return bloque


def _posicion(seccion: str, tabla: str, previsional: bool, fila: dict, valor: dict) -> Posicion:
    c = fila["celdas"]
    if "Número Cuotas" in c:
        cantidad = _numero(c["Número Cuotas"])
    elif "Acc. Libres" in c:
        cantidad = sum(
            (_numero(c[k]) or Decimal(0)) for k in ("Acc. Libres", "Acc. en Gtía", "Saldo a Plazo") if k in c
        )
    elif "Cantidad" in c:
        cantidad = _numero(c["Cantidad"])
    elif "Nominales" in c:
        # Los bonos internacionales traen los nominales en formato inglés (1,000).
        decimal = "." if tabla == "Bonos Internacionales" else ","
        cantidad = _numero(c["Nominales"], decimal)
    else:
        cantidad = None
    precio_actual = c.get("Valor Cuota Actual") or c.get("Precio Actual") or []
    precio_promedio = c.get("Precio Prom. Compra") or []
    textos_precio = " ".join(s.texto for s in precio_actual + precio_promedio)
    if textos_precio:
        moneda = "USD" if "USD" in textos_precio else "CLP"
    else:
        moneda = "USD" if "USD" in valor else "CLP"
    usadas = {
        "Número cuenta",
        "Número Cuotas",
        "Acc. Libres",
        "Acc. en Gtía",
        "Saldo a Plazo",
        "Cantidad",
        "Nominales",
        "Valor Cuota Actual",
        "Precio Actual",
        "Precio Prom. Compra",
        "Valor de mercado",
    }
    return Posicion(
        cuenta=_texto(c.get("Número cuenta", [])),
        seccion=seccion,
        tabla=tabla,
        previsional=previsional,
        instrumento=" ".join(fila["nombre"]),
        moneda=moneda,
        cantidad=cantidad,
        precio_promedio=_numero(precio_promedio),
        precio_actual=_numero(precio_actual),
        valor_clp=valor.get("CLP"),
        valor_usd=valor.get("USD"),
        detalle=fila["detalle"],
        otros={k: _texto(v) for k, v in c.items() if k not in usadas},
    )


def _movimientos_caja(spans: list[Span], cartola: Cartola) -> None:
    for tabla in _tablas(spans):
        for fila in tabla["filas"]:
            c = fila["celdas"]
            if fila["total"] or not fila["izquierda"]:
                continue
            tipo = _texto(c.get("Tipo de movimiento", []))
            moneda = _texto(c.get("Moneda", []))
            cargo = _numero(c.get("Cargo", [])) or Decimal(0)
            abono = _numero(c.get("Abono", [])) or Decimal(0)
            if tipo == "CARGO EN DOLARES" and moneda != "USD":
                # La cartola rotula estos cargos en pesos, pero el monto está en dólares.
                cartola.avisos.append(
                    f"CARGO EN DOLARES del {fila['izquierda'][0]} rotulado {moneda}: se toma como USD"
                )
                moneda = "USD"
            cartola.movimientos_caja.append(
                MovimientoCaja(
                    fecha=_fecha(fila["izquierda"][0], "%d-%m-%Y"),
                    cuenta=_texto(c.get("Número cuenta", [])),
                    tipo=tipo,
                    moneda=moneda,
                    cargo=cargo,
                    abono=abono,
                    folio=_texto(c.get("Folio", [])),
                )
            )


def _movimientos_titulos(spans: list[Span], cartola: Cartola) -> None:
    for tabla in _tablas(spans):
        for fila in tabla["filas"]:
            c = fila["celdas"]
            if fila["total"] or not fila["izquierda"]:
                continue
            cartola.movimientos_titulos.append(
                MovimientoTitulo(
                    fecha=_fecha(fila["izquierda"][0], "%d-%m-%Y"),
                    cuenta=_texto(c.get("Número cuenta", [])),
                    tipo=_texto(c.get("Tipo de operación", [])),
                    instrumento=_texto(c.get("Instrumento", [])),
                    moneda=_texto(c.get("Moneda", [])),
                    cantidad=_numero(c.get("Cantidad", [])) or Decimal(0),
                    precio=_numero(c.get("Precio", [])) or Decimal(0),
                    monto=_numero(c.get("Monto", [])) or Decimal(0),
                    referencia=_texto(c.get("Nº Referencia", [])),
                )
            )
