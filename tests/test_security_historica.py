"""Cartola Security que viene sola y con años de movimientos, sobre fragmentos inventados.

La cartola Security pegada a una BICE antigua se prueba con las copias
anonimizadas (test_security.py). La que viene sola imprime la cabecera de otra
forma, separa los fondos de inversión de la AGF de los fondos mutuos y, por
cubrir años, trae llamados de capital, liquidaciones y traspasos. Estas pruebas
arman a mano los fragmentos de texto con los tamaños y posiciones de la
cartola, sin datos de clientes.
"""

from datetime import date
from decimal import Decimal as D

import pytest

from cartolas.catalogo import Catalogo
from cartolas.extractores import security
from cartolas.modelo import Cartola, MovimientoCaja, MovimientoTitulo
from cartolas.pdf import Span


def _span(texto, x0, y0, x1=None, tamano=8.5, negrita=False):
    return Span(texto, x0, y0, x0 + 5 * len(texto) if x1 is None else x1, y0 + 10, tamano, negrita, "Arial")


def _cabecera(rut, nombre):
    return [
        _span("Desde el 02-01-2020 al 31-08-2026 Emisión: 03-09-2026 10:00:00", 11, 37, 251, tamano=9),
        *rut,
        *nombre,
        _span("USD:", 586, 87, 604),
        _span("940,91", 609, 87, 635),
        _span("€:", 654, 87, 661),
        _span("1.091,29", 666, 87, 699),
        _span("UF:", 704, 87, 716),
        _span("40.918,25", 719, 87, 757),
    ]


@pytest.mark.parametrize(
    "rut, nombre",
    [
        # La cartola sola: etiqueta y valor en un mismo fragmento.
        ([_span("Rut               : 1.111.111-1", 15, 53, 103)], [_span("Nombre     : CLIENTE DE PRUEBA", 15, 65, 178)]),
        # La pegada a una BICE antigua: el valor en un fragmento propio.
        (
            [_span("Rut :", 15, 53, 40), _span("1.111.111-1", 45, 53, 100)],
            [_span("Nombre :", 15, 65, 50), _span("CLIENTE", 55, 65, 90), _span("DE PRUEBA", 95, 65, 140)],
        ),
    ],
)
def test_lee_la_cabecera_con_el_valor_pegado_o_aparte(rut, nombre):
    c = security._cabecera(_cabecera(rut, nombre), "x.pdf")
    assert (c.rut, c.nombre) == ("1111111-1", "CLIENTE DE PRUEBA")
    assert (c.desde, c.hasta) == (date(2020, 1, 2), date(2026, 8, 31))
    assert (c.tipo_cambio_usd, c.tipo_cambio_eur) == (D("940.91"), D("1091.29"))


def _cartola():
    return Cartola(security.FORMATO, "x.pdf", "1111111-1", "", date(2020, 1, 2), date(2026, 8, 31), D("940.91"), "SECURITY")


# Columnas de la tabla FONDOS SECURITY - USD: (etiqueta, x0, x1).
_COLUMNAS = [
    ("NOMBRE FONDO", 20, 120),
    ("NUMERO CUENTA", 130, 170),
    ("NUMERO CUOTA", 180, 230),
    ("VALOR PROMEDIO COMPRA (USD)", 240, 300),
    ("MONTO INVERTIDO (USD)", 310, 370),
    ("VALOR CUOTA ACTUAL (USD)", 380, 440),
    ("SALDO ACTUAL (USD)", 450, 510),
    ("MAYOR O MENOR VALOR (USD)", 520, 580),
    ("VALORIZACIÓN EN $", 590, 650),
]


def _pagina_fondos(seccion):
    """Página con el título de sección, el bloque FONDOS SECURITY - USD, un fondo y el TOTAL."""
    fila = ["FI FULLY FUNDED SERIE A", "0", "10.000,0000", "1,0000", "10.000,00", "1,0533", "10.533,00", "533,00", "9.910.605"]
    total = ["TOTAL", "", "", "", "10.000,00", "", "10.533,00", "533,00", "9.910.605"]
    return (
        [_span(seccion, 20, 106, 200, tamano=14), _span("FONDOS SECURITY - USD", 20, 132, 200, tamano=12)]
        + [_span(e, x0, 150, x1, tamano=7, negrita=True) for e, x0, x1 in _COLUMNAS]
        + [_span(t, x0 + 2, 165, x1 - 2, tamano=7) for t, (_, x0, x1) in zip(fila, _COLUMNAS)]
        + [_span(t, x0 + 2, 180, x1 - 2, tamano=7, negrita=True) for t, (_, x0, x1) in zip(total, _COLUMNAS) if t]
    )


def test_un_fondo_de_inversion_de_la_agf_no_es_un_fondo_mutuo():
    c = _cartola()
    # Así lo resumen las páginas 1 y 2: el fondo cuenta como fondo de inversión.
    c.totales.update(
        {
            "resumen:Fondos Mutuos": D(0),
            "productos:Fondos Mutuos": D(0),
            "resumen:Fondos de Inversión": D(9910605),
            "productos:Fondos de Inversión": D(9910605),
        }
    )
    lector = security._Lector(c)
    lector.pagina("DETALLE DE INVERSIONES NO PREVISIONALES", _pagina_fondos("FONDOS DE INVERSION"))
    lector.cerrar()
    (p,) = c.posiciones
    assert (p.tabla, p.seccion, p.instrumento) == ("Fondos Inversión Bice", "Fondos de Inversión", "FI SECURITY FULLY FUNDED SERIE A")
    assert (p.cantidad, p.valor_usd, p.valor_clp) == (D("10000.0000"), D("10533.00"), D(9910605))
    assert all(x.ok for x in c.controles), [x for x in c.controles if not x.ok]
    reglas = {x.regla for x in c.controles}
    assert "Fondos de inversión de la AGF no previsionales = Resumen inversión: Fondos de Inversión" in reglas
    assert "FI USD: cuotas × valor cuota = saldo" in reglas


def test_bajo_fondos_mutuos_sigue_siendo_un_fondo_mutuo():
    c = _cartola()
    lector = security._Lector(c)
    lector.pagina("DETALLE DE INVERSIONES NO PREVISIONALES", _pagina_fondos("FONDOS MUTUOS"))
    lector.cerrar()
    assert [(p.tabla, p.instrumento) for p in c.posiciones] == [("Fondos Mutuos", "FM SECURITY FI FULLY FUNDED SERIE A")]


def test_la_tabla_maestra_lleva_el_fondo_al_export_y_a_su_nemotecnico_de_bolsa():
    catalogo = Catalogo.cargar()
    i = catalogo.buscar("FI SECURITY FULLY FUNDED SERIE A", "USD", D("1.0533"))
    assert (i.nemotecnico, i.archivo, i.producto) == ("FIP-FI FULLY FUNDED-SERIE A", "SALDOS_FFMM", "FONDOS INVERSIÓN BICE")
    # La Bolsa publica sus repartos como CFI-SPFFAE.
    assert catalogo.nemo_bolsa(i.nemotecnico) == "CFI-SPFFAE"
    assert catalogo.nemo_bolsa("CFI-OTRO") == "CFI-OTRO"


@pytest.mark.parametrize(
    "movto, tipo",
    [
        ("Llamado Ca", "LLAMADO DE CAPITAL"),
        ("Liquidacion", "LIQUIDACION"),
        ("Ingreso", "INGRESO DE TITULOS"),
        ("Egreso", "EGRESO DE TITULOS"),
    ],
)
def test_reconoce_llamados_de_capital_liquidaciones_y_traspasos(movto, tipo):
    c = _cartola()
    lector = security._Lector(c)
    celdas = {
        "FECHA OPERACIÓN": "31-08-2022",
        "NRO CUENTA": "0",
        "TIPO MOVTO": movto,
        "INSTRUMENTO": "CFIPRIV-E",
        "MDA": "CLP",
        "CANTIDAD": "10,0000",
        "PRECIO": "1.000.000,0000",
        "MONTO": "10.000.000",
        "NUMERO OPERACIÓN": "1",
    }
    lector._transaccion(security._Fila(celdas=celdas))
    (m,) = c.movimientos_titulos
    # No se exportan: el export no trae estos movimientos.
    assert (m.tipo, m.destino, m.nemotecnico) == (tipo, "", "CFIPRIV-E")
    assert c.avisos == []


def test_el_retiro_de_una_disminucion_de_capital_va_con_su_fondo():
    c = _cartola()
    c.movimientos_titulos = [
        MovimientoTitulo(date(2025, 2, 6), "0", "DISMINUCION DE CAPITAL", "CFIAAA", "CLP", D(100), D("1342.3004"), D("134230.04"), "10", "CFIAAA", "BOLSA"),
    ]
    c.movimientos_caja = [
        MovimientoCaja(date(2025, 2, 6), "0", "RETIRO", "CLP", D(0), D(134230), "10"),
        MovimientoCaja(date(2025, 2, 7), "0", "RETIRO", "CLP", D(0), D(5000), "11"),
    ]
    security._Lector(c)._vincular_caja()
    assert [(m.tipo, m.instrumento) for m in c.movimientos_caja] == [
        ("DISMINUCION DE CAPITAL - ABONO EN CUENTA MERCANTIL", "CFIAAA"),
        ("RETIRO", ""),
    ]


def test_un_dividendo_en_dolares_de_un_fondo_vendido_toma_la_moneda_del_abono():
    # El fondo ya no está al cierre: la moneda sale del abono con el mismo número de operación.
    c = _cartola()
    c.movimientos_titulos = [
        MovimientoTitulo(date(2021, 11, 8), "0", "DIVIDENDO", "CFI-BBBE", "CLP", D(10000), D("0.0143"), D(134550), "20", "CFI-BBBE"),
    ]
    c.movimientos_caja = [
        MovimientoCaja(date(2021, 11, 9), "0", "DIVIDENDO EN DOLARES", "USD", D(0), D("143.35"), "20", "CFI-BBBE"),
    ]
    security._Lector(c)._corregir_monedas()
    (m,) = c.movimientos_titulos
    assert (m.moneda, m.monto) == ("USD", D("143.35"))
