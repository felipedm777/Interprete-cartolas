"""Cuadraturas de una cartola extraída contra sus propios totales impresos.

Cada control compara una suma o un producto de lo extraído con lo que dice la
cartola. Si un control no cuadra, lo más probable es que el extractor haya
perdido, duplicado o leído mal una fila, así que el archivo queda marcado.
"""

import re
from collections import defaultdict
from decimal import Decimal

from .modelo import Cartola, Control, MovimientoTitulo

# Las cartolas imprimen los pesos sin decimales, así que cada sumando puede
# arrastrar medio peso de redondeo.
_MEDIO = Decimal("0.5")


def _tolerancia_suma(sumandos: int) -> Decimal:
    return max(Decimal(1), _MEDIO * (sumandos + 1))


def _comparar(regla: str, calculado: Decimal, impreso: Decimal, tolerancia: Decimal) -> Control:
    diferencia = calculado - impreso
    ok = abs(diferencia) <= tolerancia
    detalle = "" if diferencia == 0 else f"calculado {calculado}, impreso {impreso}, diferencia {diferencia}"
    return Control(regla, ok, detalle)


def validar(cartola: Cartola) -> list[Control]:
    t = cartola.totales
    controles: list[Control] = []

    # Resumen por tipo de cuentas: cuentas -> grupos -> patrimonio.
    grupos: dict[str, list[Decimal]] = defaultdict(list)
    for numero, cuenta in cartola.cuentas.items():
        if f"cuenta:{numero}" in t:
            grupos[cuenta.grupo].append(t[f"cuenta:{numero}"])
    for grupo, valores in grupos.items():
        if f"grupo:{grupo}" in t:
            controles.append(
                _comparar(
                    f"Suma de cuentas = total del grupo {grupo}",
                    sum(valores),
                    t[f"grupo:{grupo}"],
                    _tolerancia_suma(len(valores)),
                )
            )
    totales_grupo = [v for k, v in t.items() if k.startswith("grupo:")]
    if "patrimonio" in t and totales_grupo:
        controles.append(
            _comparar(
                "Suma de grupos = patrimonio total",
                sum(totales_grupo),
                t["patrimonio"],
                _tolerancia_suma(len(totales_grupo)),
            )
        )

    # Caja y cuentas por cobrar (caja en tránsito): saldos extraídos por cuenta
    # y total, si la cartola imprime el valor de cada cuenta.
    for clave, nombre, en_transito in (("caja", "caja", False), ("cobrar", "cuentas por cobrar", True)):
        por_cuenta: dict[str, Decimal] = defaultdict(Decimal)
        for s in cartola.saldos_caja:
            if s.en_transito == en_transito:
                por_cuenta[s.cuenta] += s.monto_clp if s.monto_clp is not None else s.monto
        impresas = {k.removeprefix(f"{clave}:") for k in t if k.startswith(f"{clave}:")}
        for numero in impresas | (set(por_cuenta) if impresas else set()):
            controles.append(
                _comparar(
                    f"Saldos de {nombre} extraídos = valor de {nombre} de la cuenta {numero}",
                    por_cuenta.get(numero, Decimal(0)),
                    t.get(f"{clave}:{numero}", Decimal(0)),
                    _tolerancia_suma(2),
                )
            )
        if clave in t:
            controles.append(
                _comparar(
                    f"Suma de {nombre} por cuenta = total de {nombre}",
                    sum(por_cuenta.values(), Decimal(0)),
                    t[clave],
                    _tolerancia_suma(len(por_cuenta)),
                )
            )

    # Posiciones: por sección contra su Total.
    secciones: dict[str, list[Decimal]] = defaultdict(list)
    for p in cartola.posiciones:
        clave = f"total:{p.seccion}{' APV' if p.previsional else ''}"
        secciones[clave].append(p.valor_clp or Decimal(0))
    impresas = {k for k in t if k.startswith("total:")}
    for clave in impresas | (set(secciones) if impresas else set()):
        valores = secciones.get(clave, [])
        controles.append(
            _comparar(
                f"Suma de posiciones = Total de {clave.removeprefix('total:')}",
                sum(valores, Decimal(0)),
                t.get(clave, Decimal(0)),
                _tolerancia_suma(len(valores)),
            )
        )

    # Por cuenta: caja + posiciones = patrimonio de la cuenta. La cartola no
    # muestra la caja en dólares bajo US$ 0,50 (el export sí la trae), así que
    # una cuenta sin caja en dólares puede sumar unos pesos menos que su
    # patrimonio: se acepta con un aviso.
    posiciones_cuenta: dict[str, list[Decimal]] = defaultdict(list)
    for p in cartola.posiciones:
        posiciones_cuenta[p.cuenta].append(p.valor_clp or Decimal(0))
    con_dolares = {s.cuenta for s in cartola.saldos_caja if s.moneda == "USD"}
    medio_dolar = (cartola.tipo_cambio_usd or Decimal(0)) / 2
    ocultos = Decimal(0)
    for numero in cartola.cuentas:
        if f"cuenta:{numero}" not in t:
            continue
        valores = posiciones_cuenta.get(numero, []) + [
            t.get(f"caja:{numero}", Decimal(0)),
            t.get(f"cobrar:{numero}", Decimal(0)),
        ]
        regla = f"Caja + posiciones = patrimonio de la cuenta {numero}"
        control = _comparar(regla, sum(valores), t[f"cuenta:{numero}"], _tolerancia_suma(len(valores)))
        faltan = t[f"cuenta:{numero}"] - sum(valores)
        if numero not in con_dolares and 1 < faltan <= medio_dolar:
            ocultos += faltan
            cartola.avisos.append(
                f"La cuenta {numero} suma {faltan} pesos menos que su patrimonio: puede ser caja en "
                "dólares bajo US$ 0,50, que la cartola no muestra"
            )
            control = Control(regla, True, control.detalle)
        controles.append(control)

    # Patrimonio total = caja + cuentas por cobrar + todas las secciones (los
    # pasivos son una sección con valores negativos).
    totales_seccion = [v for k, v in t.items() if k.startswith("total:")]
    if "patrimonio" in t and totales_seccion:
        controles.append(
            _comparar(
                "Caja + secciones = patrimonio total",
                t.get("caja", Decimal(0)) + t.get("cobrar", Decimal(0)) + sum(totales_seccion) + ocultos,
                t["patrimonio"],
                _tolerancia_suma(len(totales_seccion) + 2),
            )
        )

    controles += _controles_por_fila(cartola)
    return controles


def _controles_por_fila(cartola: Cartola) -> list[Control]:
    """Cantidad × precio = valor en cada posición y cada movimiento de títulos exportable."""
    controles = []
    cambio = {"USD": cartola.tipo_cambio_usd, "EUR": cartola.tipo_cambio_eur}
    malas = []
    revisadas = 0
    for p in cartola.posiciones:
        if p.cantidad is None or p.precio_actual is None:
            continue
        calculado = p.cantidad * p.precio_actual
        if p.tabla in ("Notas", "Bonos Internacionales"):
            calculado /= 100  # precio en porcentaje del nominal
        if opcion := re.match(r"(CALL|PUT) (\d+) ", p.instrumento):
            calculado *= int(opcion.group(2))  # cada contrato de opciones es por 100 acciones
        # El precio viene con 4 decimales: se tolera 0,05 % del valor, con un
        # mínimo de 1 peso o de 0,60 en moneda extranjera.
        if p.moneda in cambio and p.valor_clp is not None and cambio[p.moneda]:
            calculado *= cambio[p.moneda]
            valor, minimo = p.valor_clp, Decimal("0.6") * cambio[p.moneda]
        elif p.moneda == "USD" and p.valor_usd is not None:
            valor, minimo = p.valor_usd, Decimal("0.6")
        elif p.moneda == "CLP" and p.valor_clp is not None:
            valor, minimo = p.valor_clp, Decimal(1)
        else:
            continue
        revisadas += 1
        if abs(calculado - valor) > max(minimo, abs(valor) * Decimal("0.0005")):
            malas.append(f"{p.cuenta} {p.instrumento}: {calculado:.2f} vs {valor}")
    if revisadas:
        controles.append(
            Control(
                f"Cantidad × precio = valor de mercado ({revisadas} posiciones)",
                not malas,
                "; ".join(malas),
            )
        )
    malas, revisadas = [], 0
    for m in cartola.movimientos_titulos:
        # En Pershing el monto incluye comisiones y el precio de los bonos es un
        # porcentaje del nominal: lo cuadra su propio extractor.
        if not m.cantidad or not m.precio or not m.monto or destino(m) not in ("FFMM", "BOLSA"):
            continue
        calculado = m.cantidad * m.precio
        if abs(calculado - m.monto) <= max(Decimal(1), abs(m.monto) * Decimal("0.001")):
            revisadas += 1
        elif m.tipo.startswith(("INGRESO ", "RETIRO ")):
            # En los traspasos de custodia el monto puede ser el costo de origen y
            # no cantidad × precio (p. ej. fondos de otras AGF traídos desde
            # Security); el export trae los mismos valores, así que solo se avisa.
            cartola.avisos.append(
                f"Traspaso {m.fecha} {m.tipo} {m.instrumento}: el monto impreso ({m.monto}) "
                f"no es cantidad × precio ({calculado:.2f})"
            )
        else:
            revisadas += 1
            malas.append(f"{m.fecha} {m.tipo} {m.instrumento}: {calculado:.2f} vs {m.monto}")
    if revisadas:
        controles.append(
            Control(
                f"Cantidad × precio = monto ({revisadas} movimientos de títulos)",
                not malas,
                "; ".join(malas),
            )
        )
    return controles


def destino(m: MovimientoTitulo) -> str:
    """"FFMM", "BOLSA", "PERSHING" o "" si el movimiento no va a ningún archivo."""
    if m.destino:
        return m.destino
    if m.tipo.endswith(" FM"):
        return "FFMM"
    # Renta variable, renta fija y cuotas de fondos de inversión, como en el export.
    if m.tipo.endswith((" RV", " RF", " CF")):
        return "BOLSA"
    return ""
