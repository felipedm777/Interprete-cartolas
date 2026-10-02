from decimal import Decimal

from cartolas.catalogo import RUTA_TABLA, Catalogo, Instrumento, tipo_cuenta


def _instrumento(nombre, nemo, moneda, precio=None):
    return Instrumento(nombre, nemo, moneda, "EMISOR", "CFI", "CUSTODIA_ACCIONES", precio)


CATALOGO = Catalogo(
    [
        _instrumento("FONDO  UNO SERIE A", "UNO-A", "CLP"),
        _instrumento("FONDO DOS", "DOS-CLP", "CLP", Decimal("1000")),
        _instrumento("FONDO DOS", "DOS-USD1", "USD", Decimal("2.5")),
        _instrumento("FONDO DOS", "DOS-USD2", "USD", Decimal("1.0")),
    ],
    alias={("OTRO NOMBRE DEL FONDO DOS", "USD"): "DOS-USD2"},
)


def test_busca_por_nombre_exacto_o_normalizado():
    assert CATALOGO.buscar("FONDO  UNO SERIE A").nemotecnico == "UNO-A"
    assert CATALOGO.buscar("Fondo Uno Serie A").nemotecnico == "UNO-A"
    assert CATALOGO.buscar("FONDO TRES") is None


def test_elige_la_serie_por_moneda_y_precio():
    assert CATALOGO.buscar("FONDO DOS", "CLP").nemotecnico == "DOS-CLP"
    assert CATALOGO.buscar("FONDO DOS", "USD", Decimal("2.4")).nemotecnico == "DOS-USD1"
    assert CATALOGO.buscar("FONDO DOS", "USD", Decimal("0.97")).nemotecnico == "DOS-USD2"


def test_alias():
    assert CATALOGO.buscar("Otro nombre del fondo dos", "USD").nemotecnico == "DOS-USD2"
    assert CATALOGO.buscar("OTRO NOMBRE DEL FONDO DOS", "CLP") is None


def test_tipo_cuenta():
    assert tipo_cuenta("0").producto_base == "CUENTA INVERSION"
    assert tipo_cuenta("9").tipo_apv == ""
    assert tipo_cuenta("80") == tipo_cuenta("80")
    assert (tipo_cuenta("80").producto_base, tipo_cuenta("80").regimen) == ("APV FFMM", "BONIFICACIÓN")
    assert (tipo_cuenta("95").tipo_apv, tipo_cuenta("95").regimen) == ("DAPVC", "APORTE")
    assert tipo_cuenta("10") is None
    assert tipo_cuenta("ABC123") is None


def test_tabla_maestra_del_repositorio():
    catalogo = Catalogo.cargar()
    assert RUTA_TABLA.exists() and len(catalogo.instrumentos) > 200
    archivos = {i.archivo for i in catalogo.instrumentos}
    assert archivos == {"SALDOS_FFMM", "CUSTODIA_ACCIONES"}
    assert all(i.moneda in ("CLP", "USD") for i in catalogo.instrumentos)
