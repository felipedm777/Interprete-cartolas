"""Instrumento de los dividendos y repartos que la cartola BICE no identifica.

La cartola BICE nueva imprime "DIVIDENDO EN PESOS" o "REPARTO DE DINERO" sin
decir de qué instrumento vienen, pero el export los trae con el nemotécnico.
Un mismo instrumento paga el mismo monto por cuota a todos sus aportantes el
mismo día, así que, juntando las cartolas, el instrumento de cada pago es la
posición de la cuenta cuyo monto por cuota se repite en otros clientes.
"""

from collections import defaultdict
from decimal import Decimal

from .catalogo import Catalogo
from .formato import CUSTODIA_ACCIONES
from .modelo import Cartola, MovimientoCaja

TIPOS = {"DIVIDENDO EN PESOS", "DIVIDENDO EN DOLARES", "REPARTO DE DINERO"}
# Los montos vienen sin decimales: se acepta un peso (o dólar) de diferencia.
_TOLERANCIA = Decimal(1)


def inferir(cartolas: list[Cartola], catalogo: Catalogo) -> None:
    """Llena ``instrumento`` (nemotécnico) en los dividendos y repartos BICE que
    no lo traen, cuando el monto por cuota cuadra con otro cliente o la cuenta
    tiene una sola posición que pueda pagarlos."""
    # (cartola, cuenta) -> {nemotécnico: cantidad}
    posiciones: dict[tuple[int, str], dict[str, Decimal]] = defaultdict(dict)
    pagos: list[tuple[Cartola, MovimientoCaja]] = []
    for c in cartolas:
        if c.institucion != "BICE":
            continue
        for p in c.posiciones:
            i = catalogo.buscar(p.instrumento, p.moneda, p.precio_actual) or catalogo.buscar_nemotecnico(
                p.instrumento, p.moneda
            )
            if i and i.archivo == CUSTODIA_ACCIONES.tipo and p.cantidad:
                cuenta = posiciones[(id(c), p.cuenta)]
                cuenta[i.nemotecnico] = cuenta.get(i.nemotecnico, Decimal(0)) + p.cantidad
        pagos += [(c, m) for m in c.movimientos_caja if m.tipo in TIPOS and not m.instrumento]

    # (fecha, tipo, nemotécnico) -> pagos de las cuentas con esa posición
    grupos: dict[tuple, list[tuple[MovimientoCaja, Decimal]]] = defaultdict(list)
    for c, m in pagos:
        for nemo, cantidad in posiciones[(id(c), m.cuenta)].items():
            grupos[(m.fecha, m.tipo, nemo)].append((m, cantidad))

    # Por grupo, el monto por cuota que explica más pagos; vale si explica dos o más.
    apoyo: dict[int, dict[str, int]] = defaultdict(dict)
    for (_, _, nemo), lista in grupos.items():
        mejor: list[MovimientoCaja] = []
        for m, cantidad in lista:
            por_cuota = _monto(m) / cantidad
            explicados = [x for x, q in lista if abs(_monto(x) - por_cuota * q) <= _TOLERANCIA]
            if len(explicados) > len(mejor):
                mejor = explicados
        if len(mejor) >= 2:
            for m in mejor:
                apoyo[id(m)][nemo] = len(mejor)

    asignados: dict[int, int] = defaultdict(int)
    for c, m in pagos:
        candidatos = apoyo.get(id(m))
        if candidatos:
            maximo = max(candidatos.values())
            ganadores = [n for n, v in candidatos.items() if v == maximo]
        else:
            ganadores = list(posiciones[(id(c), m.cuenta)])
        if len(ganadores) == 1:
            m.instrumento = ganadores[0]
            asignados[id(c)] += 1
    for c in cartolas:
        if asignados.get(id(c)):
            c.avisos.append(
                f"{asignados[id(c)]} dividendos o repartos asignados a su instrumento por el monto por cuota"
            )


def _monto(m: MovimientoCaja) -> Decimal:
    return m.abono - m.cargo
