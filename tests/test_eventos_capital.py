"""Identificación y comprobación de los abonos por eventos de capital con la Bolsa y DataFondos."""

import json
from datetime import date
from decimal import Decimal as D

import pytest

from cartolas import eventos_capital as ec
from cartolas.catalogo import Catalogo, Instrumento
from cartolas.modelo import Cartola, Cuenta, MovimientoCaja, MovimientoTitulo, Posicion

CATALOGO = Catalogo(
    [
        Instrumento("FONDO A", "CFI-A", "CLP", "AGF", "CFI", "CUSTODIA_ACCIONES"),
        Instrumento("FONDO B", "CFI-B", "CLP", "AGF", "CFI", "CUSTODIA_ACCIONES"),
        Instrumento("ACCION", "ACC", "CLP", "EMISOR", "ACCIONES", "CUSTODIA_ACCIONES"),
    ]
)
CIERRE = date(2026, 9, 30)

# FONDO A reparte dos veces el mismo día: un dividendo y una devolución de capital.
TABLA = ec.Tabla(
    [
        ec.Evento("1", "CFI-A", ec.DIVIDENDO, "CLP", D("2.5"), date(2026, 9, 23), date(2026, 9, 29)),
        ec.Evento("1", "CFI-A", ec.REPARTO, "CLP", D("10.125"), date(2026, 9, 23), date(2026, 9, 29)),
        ec.Evento("2", "CFI-B", ec.DIVIDENDO, "CLP", D("4"), date(2026, 9, 23), date(2026, 9, 29)),
        ec.Evento(
            "2", "CFI-B", ec.REPARTO, "CLP", D("50"), date(2026, 9, 23), date(2026, 9, 29), anulado=True
        ),
    ]
)


def _cartola(posiciones, pagos, titulos=(), formato="BICE nueva"):
    c = Cartola(formato, "x.pdf", "1-9", "", date(2026, 9, 1), CIERRE, D("1000"))
    c.cuentas = {"0": Cuenta("0", "PORTAFOLIO", "Cuenta de Inversión")}
    c.posiciones = [
        Posicion("0", "Alternativos", "Fondos De Inversión", False, nombre, "CLP", D(q), None, None, None, None)
        for nombre, q in posiciones
    ]
    c.movimientos_caja = [
        MovimientoCaja(fecha, "0", tipo, "CLP", D(0), D(monto), instrumento=instrumento)
        for tipo, monto, fecha, instrumento in pagos
    ]
    c.movimientos_titulos = [
        MovimientoTitulo(fecha, "0", tipo, nombre, "CLP", D(cant), D(precio), D(monto), nemotecnico=nemo)
        for tipo, nombre, nemo, cant, precio, monto, fecha in titulos
    ]
    return c


def test_identifica_el_fondo_y_distingue_dividendo_de_devolucion_de_capital():
    # 100 cuotas de FONDO A: el dividendo paga 250 y la devolución de capital, 1012.
    c = _cartola(
        [("FONDO A", 100), ("FONDO B", 30)],
        [
            ("DIVIDENDO EN PESOS", 250, CIERRE, ""),
            ("REPARTO DE DINERO", 1012, CIERRE, ""),
        ],
    )
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert [m.instrumento for m in c.movimientos_caja] == ["CFI-A", "CFI-A"]
    assert (resultado.asignados, resultado.confirmados, resultado.dudosos) == (2, 0, [])
    assert any("2 abonos" in a for a in c.avisos)


def test_confirma_el_instrumento_que_la_cartola_trae():
    c = _cartola([("FONDO B", 30)], [("DIVIDENDO EN PESOS", 120, CIERRE, "CFI-B")])
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert resultado.confirmados == 1
    assert [x.ok for x in c.controles] == [True]


def test_marca_para_revisar_el_monto_que_no_cuadra_con_el_reparto_publicado():
    c = _cartola([("FONDO B", 30)], [("DIVIDENDO EN PESOS", 500, CIERRE, "CFI-B")])
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert len(resultado.revisar) == 1
    assert [x.ok for x in c.controles] == [False]


def test_varios_fondos_que_explican_el_monto_quedan_dudosos():
    # 48 cuotas de A y 30 de B pagan los mismos 120 pesos de dividendo.
    c = _cartola([("FONDO A", 48), ("FONDO B", 30)], [("DIVIDENDO EN PESOS", 120, CIERRE, "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert c.movimientos_caja[0].instrumento == ""
    assert resultado.asignados == 0 and len(resultado.dudosos) == 1
    assert "CFI-A, CFI-B" in resultado.dudosos[0]


def test_lo_que_la_tabla_no_explica_queda_dudoso_y_sin_instrumento():
    c = _cartola([("ACCION", 100)], [("PAGO DE DIVIDENDOS", 3000, CIERRE, "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert c.movimientos_caja[0].instrumento == ""
    # Los dividendos de las acciones los publica la Bolsa, y la tabla no la trae.
    assert len(resultado.dudosos) == 1 and "por bajar el Excel de la Bolsa: ACC" in resultado.dudosos[0]
    assert resultado.causas == {ec.POR_BAJAR: 1}
    # DataFondos sigue solo fondos: una acción no se le consulta.
    assert resultado.pendientes == set()


def test_un_fondo_que_falta_en_la_tabla_queda_pendiente_de_consultar():
    c = _cartola([("FONDO A", 100)], [("DIVIDENDO EN PESOS", 250, CIERRE, "")])
    sin_a = ec.Tabla([e for e in TABLA.eventos if e.nemotecnico != "CFI-A"])
    resultado = ec.conciliar([c], CATALOGO, sin_a)
    assert resultado.pendientes == {("CFI-A", "2026-09")}
    assert len(resultado.dudosos) == 1


def test_no_usa_un_evento_anulado():
    # El reparto de 50 por cuota de FONDO B está anulado: no pagó dinero.
    c = _cartola([("FONDO B", 30)], [("REPARTO DE DINERO", 1500, CIERRE, "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert c.movimientos_caja[0].instrumento == ""
    assert len(resultado.dudosos) == 1


def test_un_abono_lejano_a_la_fecha_de_pago_no_cuenta():
    c = _cartola([("FONDO A", 100)], [("DIVIDENDO EN PESOS", 250, date(2026, 8, 10), "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert c.movimientos_caja[0].instrumento == ""
    assert len(resultado.dudosos) == 1


def test_el_monto_por_cuota_impreso_confirma_aunque_cambien_las_cuotas():
    # La cartola Security trae el monto por cuota del dividendo; las cuotas del
    # cierre son otras porque el cliente compró después de la fecha límite.
    c = _cartola(
        [("FONDO A", 120)],
        [("DIVIDENDO EN PESOS", 250, date(2026, 9, 28), "CFI-A")],
        [("DIVIDENDO", "FONDO A", "CFI-A", 100, "2.5", 250, date(2026, 9, 29))],
        formato="Valores Security",
    )
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert (resultado.confirmados, resultado.revisar) == (1, [])


def test_un_cargo_por_pago_de_dividendos_no_se_explica():
    # El dividendo ya se abonó; el cargo es su pago al cliente y queda como caja.
    c = _cartola([("FONDO A", 100)], [])
    c.movimientos_caja = [MovimientoCaja(CIERRE, "0", "PAGO DE DIVIDENDOS", "CLP", D(250), D(0))]
    resultado = ec.conciliar([c], CATALOGO, TABLA)
    assert (resultado.confirmados, resultado.asignados, resultado.dudosos) == (0, 0, [])
    assert c.movimientos_caja[0].instrumento == ""


def test_encuentra_el_fondo_aunque_el_guion_vaya_en_otro_lugar():
    # El catálogo dice CFI-CCCE y DataFondos publica el mismo fondo como CFICCC-E.
    catalogo = Catalogo([Instrumento("FONDO C", "CFI-CCCE", "USD", "AGF", "CFI", "CUSTODIA_ACCIONES")])
    tabla = ec.Tabla(
        [ec.Evento("3", "CFICCC-E", ec.REPARTO, "USD", D("0.003859215"), date(2026, 9, 1), date(2026, 9, 7))]
    )
    c = _cartola([("FONDO C", 29500)], [("REPARTO DE DINERO EN USD", "113.85", date(2026, 9, 7), "")])
    c.posiciones[0].moneda = "USD"
    resultado = ec.conciliar([c], catalogo, tabla)
    assert c.movimientos_caja[0].instrumento == "CFI-CCCE"
    assert resultado.asignados == 1 and resultado.pendientes == set()


def test_un_abono_con_instrumento_sin_reparto_publicado_queda_sin_comprobar():
    c = _cartola([("FONDO A", 100)], [("DIVIDENDO EN PESOS", 250, date(2026, 8, 10), "CFI-A")])
    resultado = ec.conciliar([c], CATALOGO, TABLA, COBERTURA)
    assert (resultado.confirmados, resultado.revisar, resultado.dudosos) == (0, [], [])
    assert resultado.sin_comprobar == [
        "DIVIDENDO EN PESOS CLP del 10-08-2026 va con CFI-A: sin reparto publicado en la fecha"
    ]
    assert c.movimientos_caja[0].instrumento == "CFI-A"
    assert any(a.startswith("Abono sin comprobar") for a in c.avisos)


def test_sin_tabla_no_cambia_nada():
    c = _cartola([("FONDO A", 100)], [("DIVIDENDO EN PESOS", 250, CIERRE, "")])
    resultado = ec.conciliar([c], CATALOGO, ec.Tabla([]))
    assert c.movimientos_caja[0].instrumento == ""
    assert (resultado.confirmados, resultado.asignados, resultado.dudosos) == (0, 0, [])
    assert c.avisos == [] and c.controles == []


@pytest.mark.parametrize(
    "texto, clase, monto",
    [
        ("DIVIDENDO PROV. $ 264,8097994", ec.DIVIDENDO, D("264.8097994")),
        ("REPARTO CAP.  $ 1.407,7626", ec.REPARTO, D("1407.7626")),
        ("DIVIDENDO INF US$ 0,019015694", ec.DIVIDENDO, D("0.019015694")),
        ("DISMINUCION DE CAPITAL $ 10", ec.DISMINUCION, D(10)),
        ("EMIS PAGO INF 1,457 X 1", ec.EMISION, None),
    ],
)
def test_lee_la_clase_y_el_monto_por_cuota_del_texto(texto, clase, monto):
    assert ec.clase_de(texto) == clase
    assert ec.monto_de(texto) == monto


def test_la_moneda_sale_del_texto():
    assert ec.moneda_de("DIVIDENDO INF US$ 0,01") == "USD"
    assert ec.moneda_de("DIVIDENDO PROV. $ 100") == "CLP"
    assert ec.moneda_de("EMIS PAGO INF 1,457 X 1") == ""


def test_agrega_a_la_tabla_lo_que_devuelve_datafondos(tmp_path):
    respuesta = tmp_path / "dividendos.json"
    respuesta.write_text(
        json.dumps(
            {
                "ok": True,
                "data": [
                    {
                        "rut": "9991",
                        "nemo": "CFI-A",
                        "evento": "REPARTO CAP.  $ 349,9154356",
                        "moneda": "$",
                        "pago_por_accion": 349.915,
                        "fecha_limite": "2026-09-23",
                        "fecha_pago": "2026-09-29",
                        "anulado": 0,
                    },
                    {
                        "rut": "9991",
                        "nemo": "CFI-A",
                        "evento": "DIVIDENDO PROV. $ 100",
                        "moneda": "$",
                        "pago_por_accion": 100,
                        "fecha_limite": "2025-01-20",
                        "fecha_pago": "2025-01-26",
                        "anulado": 0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    tabla = tmp_path / "eventos_capital.csv"
    assert ec.main([str(respuesta), "--tabla", str(tabla), "--desde", "2026-01-01"]) == 0
    eventos = ec.Tabla.cargar(tabla).eventos
    assert [(e.clase, e.monto_por_cuota, e.fecha_pago) for e in eventos] == [
        (ec.REPARTO, D("349.9154356"), date(2026, 9, 29))
    ]
    # Volver a agregar la misma respuesta no repite el evento.
    assert ec.main([str(respuesta), "--tabla", str(tabla)]) == 0
    assert len(ec.Tabla.cargar(tabla)) == 2
    # --desde filtra lo que llega, no lo que la tabla ya tenía.
    assert ec.main([str(respuesta), "--tabla", str(tabla), "--desde", "2026-01-01"]) == 0
    assert len(ec.Tabla.cargar(tabla)) == 2


# Qué fondos sigue DataFondos, actualizada después de los abonos de las pruebas.
COBERTURA = ec.Cobertura(
    [
        ec.Seguido("CFI-A", "1", eventos=2, ultima_fecha=date(2026, 9, 29), actualizado=date(2026, 10, 7)),
        ec.Seguido("CFI-B", "2", eventos=2, ultima_fecha=date(2026, 9, 29), actualizado=date(2026, 10, 7)),
    ]
)


def test_con_la_cobertura_un_fondo_que_datafondos_no_sigue_no_queda_por_consultar():
    c = _cartola([("FONDO A", 100)], [("DIVIDENDO EN PESOS", 250, CIERRE, "")])
    sin_a = ec.Tabla([e for e in TABLA.eventos if e.nemotecnico != "CFI-A"])
    resultado = ec.conciliar([c], CATALOGO, sin_a, ec.Cobertura(COBERTURA.seguidos[1:]))
    assert resultado.pendientes == set()
    assert resultado.causas == {ec.SIN_REPARTO: 1}
    assert "fondos que no siguen ni la Bolsa ni DataFondos: CFI-A" in resultado.dudosos[0]


def test_un_fondo_con_repartos_mas_nuevos_que_la_tabla_queda_por_consultar():
    c = _cartola([("FONDO A", 100)], [("DIVIDENDO EN PESOS", 250, CIERRE, "")])
    sin_a = ec.Tabla([e for e in TABLA.eventos if e.nemotecnico != "CFI-A"])
    resultado = ec.conciliar([c], CATALOGO, sin_a, COBERTURA)
    assert resultado.pendientes == {("CFI-A", "2026-09")}
    assert resultado.causas == {ec.POR_CONSULTAR: 1}


def test_una_cobertura_anterior_al_abono_deja_el_fondo_por_consultar():
    c = _cartola([("FONDO B", 30)], [("DIVIDENDO EN PESOS", 120, date(2026, 11, 27), "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA, COBERTURA)
    assert resultado.pendientes == {("CFI-B", "2026-11")}
    assert resultado.causas == {ec.POR_CONSULTAR: 1}


def test_un_fondo_al_dia_sin_reparto_en_la_fecha_no_queda_por_consultar():
    c = _cartola([("FONDO B", 30)], [("DIVIDENDO EN PESOS", 120, date(2026, 8, 10), "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA, COBERTURA)
    assert resultado.pendientes == set()
    assert "sin reparto publicado en la fecha: CFI-B" in resultado.dudosos[0]


def test_ningun_reparto_publicado_cuadra():
    c = _cartola([("FONDO B", 30), ("ACCION", 10)], [("DIVIDENDO EN PESOS", 999, CIERRE, "")])
    # Con el Excel de la Bolsa al día, que no publica nada de la acción.
    resultado = ec.conciliar([c], CATALOGO, ec.Tabla(TABLA.eventos, date(2026, 10, 9)), COBERTURA)
    assert resultado.causas == {ec.NO_CUADRA: 1}
    assert "acciones u otros instrumentos que la Bolsa no publica: ACC" in resultado.dudosos[0]


def test_sin_la_tabla_de_la_bolsa_una_accion_pide_bajarla():
    c = _cartola([("FONDO B", 30), ("ACCION", 10)], [("DIVIDENDO EN PESOS", 999, CIERRE, "")])
    resultado = ec.conciliar([c], CATALOGO, TABLA, COBERTURA)
    assert resultado.causas == {ec.POR_BAJAR: 1}


def test_agrega_la_cobertura_que_devuelve_resumen_dividendos(tmp_path):
    respuesta = tmp_path / "resumen.json"
    fila = {"rut": "9461", "serie": "A", "nombre": "FONDO", "ultima_actualizacion": "2026-10-07T18:15:04"}
    respuesta.write_text(
        json.dumps(
            {
                "ok": True,
                "data": [
                    {**fila, "nemo": "CFI-AMG2AE", "total": 0, "ultima_fecha": None},
                    {**fila, "nemo": "CFIAMG2A-E", "total": 45, "ultima_fecha": "2026-06-22"},
                ],
            }
        ),
        encoding="utf-8",
    )
    tabla, cobertura = tmp_path / "eventos.csv", tmp_path / "cobertura.csv"
    assert ec.main([str(respuesta), "--tabla", str(tabla), "--cobertura", str(cobertura)]) == 0
    assert not tabla.exists()
    leida = ec.Cobertura.cargar(cobertura)
    assert len(leida) == 2
    # El mismo fondo con las dos grafías: vale la que tiene los repartos.
    seguido = leida.buscar("CFI-AMG2AE")
    assert (seguido.nemotecnico, seguido.eventos, seguido.actualizado) == (
        "CFIAMG2A-E",
        45,
        date(2026, 10, 7),
    )
