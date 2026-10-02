"""Cuadraturas de una cartola extraída contra sus propios totales impresos.

Cada control compara una suma o un producto de lo extraído con lo que dice la
cartola. Si un control no cuadra, lo más probable es que el extractor haya
perdido, duplicado o leído mal una fila, así que el archivo queda marcado.
"""

from collections import defaultdict
from decimal import Decimal

from .modelo import Cartola, Control

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

    # Caja: saldos extraídos por cuenta y total.
    caja_cuenta: dict[str, Decimal] = defaultdict(Decimal)
    for s in cartola.saldos_caja:
        caja_cuenta[s.cuenta] += s.monto_clp if s.monto_clp is not None else s.monto
    for numero in {k.removeprefix("caja:") for k in t if k.startswith("caja:")} | set(caja_cuenta):
        controles.append(
            _comparar(
                f"Saldos de caja extraídos = valor de caja de la cuenta {numero}",
                caja_cuenta.get(numero, Decimal(0)),
                t.get(f"caja:{numero}", Decimal(0)),
                _tolerancia_suma(2),
            )
        )
    if "caja" in t:
        controles.append(
            _comparar(
                "Suma de caja por cuenta = total de caja",
                sum(caja_cuenta.values(), Decimal(0)),
                t["caja"],
                _tolerancia_suma(len(caja_cuenta)),
            )
        )

    # Posiciones: por sección contra su Total.
    secciones: dict[str, list[Decimal]] = defaultdict(list)
    for p in cartola.posiciones:
        clave = f"total:{p.seccion}{' APV' if p.previsional else ''}"
        secciones[clave].append(p.valor_clp or Decimal(0))
    for clave in {k for k in t if k.startswith("total:")} | set(secciones):
        valores = secciones.get(clave, [])
        controles.append(
            _comparar(
                f"Suma de posiciones = Total de {clave.removeprefix('total:')}",
                sum(valores, Decimal(0)),
                t.get(clave, Decimal(0)),
                _tolerancia_suma(len(valores)),
            )
        )

    # Patrimonio total = caja + todas las secciones.
    totales_seccion = [v for k, v in t.items() if k.startswith("total:")]
    if "patrimonio" in t and totales_seccion:
        controles.append(
            _comparar(
                "Caja + secciones = patrimonio total",
                t.get("caja", Decimal(0)) + sum(totales_seccion),
                t["patrimonio"],
                _tolerancia_suma(len(totales_seccion) + 1),
            )
        )

    # Por cuenta: caja + posiciones = patrimonio de la cuenta.
    posiciones_cuenta: dict[str, list[Decimal]] = defaultdict(list)
    for p in cartola.posiciones:
        posiciones_cuenta[p.cuenta].append(p.valor_clp or Decimal(0))
    for numero in cartola.cuentas:
        if f"cuenta:{numero}" not in t:
            continue
        valores = posiciones_cuenta.get(numero, []) + [t.get(f"caja:{numero}", Decimal(0))]
        controles.append(
            _comparar(
                f"Caja + posiciones = patrimonio de la cuenta {numero}",
                sum(valores),
                t[f"cuenta:{numero}"],
                _tolerancia_suma(len(valores)),
            )
        )

    controles += _controles_por_fila(cartola)
    return controles


def _controles_por_fila(cartola: Cartola) -> list[Control]:
    """Cantidad × precio = valor en cada posición y cada movimiento de títulos."""
    controles = []
    tc = cartola.tipo_cambio_usd
    malas = []
    revisadas = 0
    for p in cartola.posiciones:
        if p.cantidad is None or p.precio_actual is None or p.valor_clp is None:
            continue
        calculado = p.cantidad * p.precio_actual
        if p.tabla in ("Notas", "Bonos Internacionales"):
            calculado /= 100  # precio en porcentaje del nominal
        # El precio viene con 4 decimales: se tolera 0,05 % del valor, con un
        # mínimo de 1 peso o, en USD, de 0,60 dólares.
        minimo = Decimal(1)
        if p.moneda == "USD":
            if not tc:
                continue
            calculado *= tc
            minimo = Decimal("0.6") * tc
        revisadas += 1
        if abs(calculado - p.valor_clp) > max(minimo, abs(p.valor_clp) * Decimal("0.0005")):
            malas.append(f"{p.cuenta} {p.instrumento}: {calculado:.0f} vs {p.valor_clp}")
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
        if not m.cantidad or not m.precio or not m.monto:
            continue
        revisadas += 1
        calculado = m.cantidad * m.precio
        if abs(calculado - m.monto) > max(Decimal(1), abs(m.monto) * Decimal("0.001")):
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
