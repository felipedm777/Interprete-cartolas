"""Instrumento de los dividendos BICE, deducido del monto por cuota."""

from datetime import date
from decimal import Decimal as D

from cartolas import dividendos
from cartolas.catalogo import Catalogo, Instrumento
from cartolas.modelo import Cartola, MovimientoCaja, Posicion

CATALOGO = Catalogo(
    [
        Instrumento("FONDO A", "CFI-A", "CLP", "AGF", "CFI", "CUSTODIA_ACCIONES"),
        Instrumento("FONDO B", "CFI-B", "CLP", "AGF", "CFI", "CUSTODIA_ACCIONES"),
        Instrumento("FONDO MUTUO", "FM-M", "CLP", "AGF", "FONDOS MUTUOS BICE", "SALDOS_FFMM"),
    ]
)
DIA = date(2026, 9, 30)


def _cartola(rut, posiciones, pagos):
    c = Cartola("BICE nueva", f"{rut}.pdf", rut, "", date(2026, 9, 1), DIA, D("1000"))
    c.posiciones = [
        Posicion("0", "Activos Alternativos", "Fondos De Inversión", False, nombre, "CLP", D(q), None, None, None, None)
        for nombre, q in posiciones
    ]
    c.movimientos_caja = [MovimientoCaja(DIA, "0", tipo, "CLP", D(0), D(monto)) for tipo, monto in pagos]
    return c


def test_asigna_el_instrumento_cuyo_monto_por_cuota_se_repite():
    # FONDO A paga 2,5 por cuota y FONDO B, 4; los montos vienen redondeados.
    uno = _cartola("1-9", [("FONDO A", 100), ("FONDO B", 30)], [("DIVIDENDO EN PESOS", 250)])
    dos = _cartola("2-7", [("FONDO A", 41), ("FONDO B", 10)], [("DIVIDENDO EN PESOS", 102), ("REPARTO DE DINERO", 40)])
    tres = _cartola("3-5", [("FONDO B", 7), ("FONDO MUTUO", 5)], [("REPARTO DE DINERO", 28)])
    dividendos.inferir([uno, dos, tres], CATALOGO)
    assert [m.instrumento for m in uno.movimientos_caja] == ["CFI-A"]
    assert [m.instrumento for m in dos.movimientos_caja] == ["CFI-A", "CFI-B"]
    # El fondo mutuo no paga dividendos en caja: la única posición posible es FONDO B.
    assert [m.instrumento for m in tres.movimientos_caja] == ["CFI-B"]
    assert any("2 dividendos" in a for a in dos.avisos)


def test_sin_evidencia_queda_como_caja():
    sola = _cartola("1-9", [("FONDO A", 100), ("FONDO B", 30)], [("DIVIDENDO EN PESOS", 250)])
    dividendos.inferir([sola], CATALOGO)
    assert sola.movimientos_caja[0].instrumento == ""
    assert not sola.avisos
