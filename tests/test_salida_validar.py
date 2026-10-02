"""Reglas de salida y cuadraturas sobre una cartola inventada."""

from datetime import date
from decimal import Decimal as D

from cartolas.catalogo import Catalogo, Instrumento
from cartolas.exportar import escribir
from cartolas.formato import MOVIMIENTOS_PERSHING
from cartolas.modelo import Cartola, Cuenta, MovimientoCaja, MovimientoTitulo, Posicion, SaldoCaja
from cartolas.salida import generar
from cartolas.validar import validar

TC = D("1000")

CATALOGO = Catalogo(
    [
        Instrumento("FONDO MUTUO X", "FM-X", "CLP", "AGF X", "FONDOS MUTUOS BICE", "SALDOS_FFMM"),
        Instrumento("FONDO INVERSION Y", "CFI-Y", "USD", "AGF Y", "CFI", "CUSTODIA_ACCIONES"),
    ]
)


def _posicion(cuenta, tabla, instrumento, moneda, cantidad, precio, valor_clp, seccion="Renta Fija"):
    return Posicion(
        cuenta=cuenta,
        seccion=seccion,
        tabla=tabla,
        previsional=cuenta.startswith("9"),
        instrumento=instrumento,
        moneda=moneda,
        cantidad=D(cantidad),
        precio_promedio=D("1"),
        precio_actual=D(precio),
        valor_clp=D(valor_clp),
        valor_usd=None,
    )


def _cartola() -> Cartola:
    c = Cartola("prueba", "x.pdf", "1-9", "", date(2026, 1, 1), date(2026, 1, 31), TC)
    c.cuentas = {
        "0": Cuenta("0", "PORTAFOLIO N° 1 - AFITRADING ASESORIA FINANCIERA - S", "Cuenta de Inversión"),
        "90": Cuenta("90", "PORTAFOLIO N° 1 - AFITRADING ASESORIA FINANCIERA - DAPV-B-S", "APV Prime"),
        "1": Cuenta("1", "PORTAFOLIO N° 2", "Cuenta de Inversión"),
        "EXT1": Cuenta("EXT1", "PORTAFOLIO N° 1 - EXT1", "Mercado Internacional Pershing"),
    }
    c.saldos_caja = [
        SaldoCaja("0", "CLP", D("500"), D("500")),
        SaldoCaja("0", "USD", D("1.25"), D("1250")),
        SaldoCaja("EXT1", "USD", D("2"), D("2000")),
    ]
    c.posiciones = [
        _posicion("0", "Fondos Mutuos", "FONDO MUTUO X", "CLP", "10", "100.5", "1005"),
        _posicion("0", "CFI", "FONDO INVERSION Y", "USD", "4", "2.5", "10000"),
        _posicion("90", "CFI", "FONDO INVERSION Y", "USD", "2", "2.5", "5000"),
        _posicion("1", "Acciones", "ACCION Z", "CLP", "3", "100", "300"),
        _posicion("0", "Intermediación Financiera", "PAGARE", "CLP", "1", "0", "700"),
    ]
    c.posiciones[-1].precio_actual = None
    c.movimientos_caja = [
        MovimientoCaja(date(2026, 1, 5), "0", "CARGO EN DOLARES", "USD", D("10"), D("0")),
        MovimientoCaja(date(2026, 1, 6), "0", "DIVIDENDO EN PESOS", "CLP", D("0"), D("50")),
    ]
    c.movimientos_titulos = [
        MovimientoTitulo(date(2026, 1, 7), "0", "INVERSION FM", "FONDO MUTUO X", "CLP", D("2"), D("100"), D("200"), "123"),
        MovimientoTitulo(date(2026, 1, 8), "90", "COMPRA RV", "FONDO INVERSION Y", "USD", D("2"), D("2.5"), D("5")),
    ]
    c.totales = {
        "cuenta:0": D("1750") + D("1005") + D("10000") + D("700"),
        "cuenta:90": D("5000"),
        "cuenta:1": D("300"),
        "cuenta:EXT1": D("2000"),
        "grupo:Cuenta de Inversión": D("13755"),
        "grupo:APV Prime": D("5000"),
        "grupo:Mercado Internacional Pershing": D("2000"),
        "patrimonio": D("20755"),
        "caja:0": D("1750"),
        "caja:EXT1": D("2000"),
        "caja": D("3750"),
        "total:Renta Fija": D("1005") + D("10000") + D("300") + D("700"),
        "total:Renta Fija APV": D("5000"),
    }
    return c


def test_cuadraturas_ok():
    controles = validar(_cartola())
    assert controles and all(c.ok for c in controles), [c for c in controles if not c.ok]


def test_cuadratura_detecta_una_fila_perdida():
    c = _cartola()
    del c.posiciones[0]
    malos = {x.regla for x in validar(c) if not x.ok}
    assert "Suma de posiciones = Total de Renta Fija" in malos
    assert "Caja + posiciones = patrimonio de la cuenta 0" in malos


def test_cuadratura_detecta_cantidad_mal_leida():
    c = _cartola()
    c.posiciones[0].cantidad = D("100")
    malos = [x for x in validar(c) if not x.ok]
    assert len(malos) == 1 and malos[0].regla.startswith("Cantidad × precio")


def test_saldos_de_caja():
    s = generar(_cartola(), CATALOGO)
    caja = s.filas["SALDOS_CAJA"]
    assert [(f["Cuenta"], f["MonedaValoracionPatrimonio"]) for f in caja] == [("0", "CLP"), ("0", "USD")]
    clp, usd = caja
    assert (clp["patrimonioCLP"], clp["patrimonioUSD"]) == (D("500"), D("0.5"))
    assert (usd["PatrimonioEnMonedaValoracion"], usd["patrimonioCLP"]) == (D("1.25"), D("1250"))
    assert clp["ProductoBase"] == "CUENTA INVERSION" and clp["Producto"] == "CUENTAS CAJA"
    assert clp["FechaProceso"] == "2026-01-31" and clp["EnTransito"] == "NO"
    assert any("EXT1" in o for o in s.omitidos)


def test_posiciones():
    s = generar(_cartola(), CATALOGO)
    (ffmm,) = s.filas["SALDOS_FFMM"]
    assert ffmm["NemotecnicoInstrumento"] == "FM-X"
    assert ffmm["PatrimonioEnMonedaValoracion"] == D("1005.0")  # cuotas × valor cuota
    custodia = {(f["Cuenta"], f["Instrumento"]): f for f in s.filas["CUSTODIA_ACCIONES"]}
    cfi_ci = custodia[("0", "FONDO INVERSION Y")]
    assert cfi_ci["MonedaValoracionPatrimonio"] == "USD"
    assert (cfi_ci["patrimonioUSD"], cfi_ci["patrimonioCLP"]) == (D("10"), D("10000"))
    cfi_apv = custodia[("90", "FONDO INVERSION Y")]
    assert cfi_apv["MonedaValoracionPatrimonio"] == "CLP" and cfi_apv["patrimonioCLP"] == D("5000")
    assert (cfi_apv["ProductoBase"], cfi_apv["TipoAPV"]) == ("APV PRIME", "DAPV")
    # Fuera de la tabla maestra: producto según la tabla de la cartola y sin nemotécnico.
    accion = custodia[("1", "ACCION Z")]
    assert accion["Producto"] == "ACCIONES" and accion["NemotecnicoInstrumento"] == ""
    assert any("ACCION Z" in a for a in s.avisos)
    assert any("Intermediación Financiera" in o for o in s.omitidos)


def test_solo_afi():
    s = generar(_cartola(), CATALOGO, solo_afi=True)
    assert all("AFITRADING" in f["Portafolio"] for filas in s.filas.values() for f in filas)
    assert any("no es de AFI Trading" in o for o in s.omitidos)


def test_movimientos():
    s = generar(_cartola(), CATALOGO)
    dolar, dividendo = s.filas["MOVIMIENTOS_DE_CAJA"]
    assert (dolar["Instrumento"], dolar["Producto"], dolar["cargo"]) == ("DOLAR", "FORWARDS DIVISA", D("10"))
    assert (dividendo["Instrumento"], dividendo["FechaProceso"]) == ("CAJA CLP", "2026-01-06")
    (fm,) = s.filas["MOVIMIENTOS_FFMM"]
    assert (fm["NumeroRerferencia"], fm["NemotecnicoInstrumento"], fm["MontoNeto"]) == ("123", "FM-X", D("200"))
    (rv,) = s.filas["MOVIMIENTOS_BOLSA"]
    assert (rv["NombreTipoMovimiento"], rv["Producto"], rv["Cuenta"]) == ("COMPRA RV", "CFI", "90")


def _cartola_pershing() -> Cartola:
    c = Cartola("Pershing", "x.pdf", "", "", date(2026, 1, 1), date(2026, 1, 31), TC, institucion="PERSHING")
    c.cuentas = {"EXT1": Cuenta("EXT1", "", "Pershing", producto_base="CUENTA INVERSION")}
    c.posiciones = [
        _posicion("EXT1", "Acciones", "ACCION GBP", "GBP", "10", "2", "0", seccion="Acciones"),
    ]
    c.posiciones[0].valor_clp, c.posiciones[0].valor_usd = None, D("25")
    c.movimientos_titulos = [
        MovimientoTitulo(date(2026, 1, 9), "EXT1", "MONEY FUND INCOME", "FONDO MM", "USD", None, None, D("1.5"),
                         nemotecnico="MM1", destino="PERSHING", producto="MONEY MARKET"),
        MovimientoTitulo(date(2026, 1, 10), "EXT1", "BOUGHT", "ACCION W", "USD", D("3"), D("10"), D("-30.5"),
                         destino="PERSHING", producto="ACCIONES"),
    ]
    return c


def test_pershing(tmp_path):
    c = _cartola_pershing()
    assert all(x.ok for x in validar(c))  # la compra con comisión no entra al control genérico
    s = generar(c, CATALOGO)
    (accion,) = s.filas["CUSTODIA_ACCIONES"]
    assert (accion["MonedaValoracionPatrimonio"], accion["patrimonioUSD"], accion["patrimonioCLP"]) == (
        "USD", D("25"), D("25000"))
    ingreso, compra = s.filas["MOVIMIENTOS_PERSHING"]
    assert (ingreso["Cuenta"], ingreso["CuentaPershing"], ingreso["RutCliente"]) == ("EXT1", "EXT1", "")
    assert (ingreso["Producto"], ingreso["Cantidad"], ingreso["MontoNeto"]) == ("MONEY MARKET", None, D("1.5"))
    assert (compra["NombreTipoMovimiento"], compra["MontoNeto"], compra["FechaProceso"]) == ("BOUGHT", D("-30.5"), "2026-01-10")
    assert "TipoAPV" not in compra
    escribir(MOVIMIENTOS_PERSHING, s.filas["MOVIMIENTOS_PERSHING"], tmp_path / "m.csv")
    assert (tmp_path / "m.csv").read_text(encoding="utf-8").splitlines()[2].startswith("3,0000;2026-01-10;;EXT1;EXT1;")
