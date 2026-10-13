"""Lectura del Excel de dividendos y repartos de la Bolsa y su uso para cuadrar abonos."""

from datetime import date, datetime
from decimal import Decimal as D

import pytest

from cartolas import bolsa
from cartolas import eventos_capital as ec
from cartolas.catalogo import Catalogo, Instrumento
from cartolas.modelo import Cartola, Cuenta, MovimientoCaja, Posicion

openpyxl = pytest.importorskip("openpyxl")

# Encabezados como los publica la Bolsa: la hoja de acciones tiene una columna
# de nemotécnico más una que dice "Acciones"; las de fondos, la de pesos y la de
# dólares; la de extranjeros, la de dólares y la de pesos.
_COMUNES = ["Nº Mov.", "Tipo (3)", "Moneda", "Por Acción / cuota", "Monto total a distribuir"]
ENCABEZADOS = {
    "Dividendos acciones nacionales": ["Nombre Emisor", "Serie", "Nemotécnico", "Columna1", "Tipo Instrumento"]
    + _COMUNES
    + ["Límite (1)", "Pago", "Lugar o modalidad de pago", "Observaciones"],
    "Dividendos CFI nacionales": ["Nombre Emisor", "Serie", "Pesos", "Dólares", "Tipo Instrumento"]
    + _COMUNES
    + ["Límite (1)", "Pago", "Lugar o modalidad de pago", "Observaciones"],
    "Repartos CFI-CFM": ["Nombre Emisor", "Serie", "Pesos", "Dólares", "Tipo Instrumento"]
    + _COMUNES
    + ["Límite (1)", "Pago", "Lugar o modalidad de pago", "Observaciones"],
    "Dividendos emisores extranjeros": ["Nombre Emisor", "Serie", "Dólar", "Pesos", "Mercado"]
    + _COMUNES
    + ["Ex Date (1)", "Pago", "Lugar o modalidad de pago", "Observaciones"],
}


def _fila(emisor, serie, nemo1, nemo2, clase, tipo, moneda, monto, limite, pago):
    return [emisor, serie, nemo1, nemo2, clase, "-", tipo, moneda, monto, None, limite, pago, "-", None]


def _dia(m, d):
    return datetime(2026, m, d)


FILAS = {
    "Dividendos acciones nacionales": [
        _fila("Emisor A", None, "ACC", "Acciones", "Acciones", "Definitivo", "$", 40, _dia(9, 9), _dia(9, 15)),
        _fila("Emisor B", None, "ACCB", "Acciones", "Acciones", "Reparto de Capital", "$", 12.5, _dia(9, 9), _dia(9, 15)),
        # Fila suelta que solo dice "Acciones": no es un evento.
        [None, None, None, "Acciones"],
        # Sin fecha de pago: no se puede cuadrar.
        _fila("Emisor C", None, "ACCC", "Acciones", "Acciones", "Provisorio", "$", "-", "-", "-"),
    ],
    "Dividendos CFI nacionales": [
        # Un fondo en dólares con sus dos nemotécnicos: son el mismo.
        _fila("Fondo D", "A", "CFIDDDA-E", "CFI-DDDAE", "CFI", "Provisorio", "US$", 0.0031329609, _dia(9, 9), _dia(9, 15)),
        # Nemotécnico con un carácter de control escapado y monto escrito como texto.
        _fila("Fondo E", "B", "CFIEEEB-E_x0006_", None, "CFI", "Definitivo", "$", "\xa0\xa0 7,199693879412", _dia(9, 9), _dia(9, 15)),
    ],
    "Repartos CFI-CFM": [
        _fila("Fondo F", None, "CFIFFF", None, "CFI", "Reparto", "$", 1500, _dia(9, 9), _dia(9, 15)),
        _fila("Fondo G", None, "CFIGGG", None, "CFI", "Reparto", "US$", "Ver documento", _dia(9, 9), _dia(9, 15)),
        _fila("Fondo H", None, "CFIHHH", None, "CFI", "Reparto", "$", "2 18,1848371858", _dia(9, 9), _dia(9, 15)),
        # Un reparto informado como "Provisorio" sigue siendo un reparto.
        _fila("Fondo I", None, "CFIIII", None, "CFI", "Provisorio", "EURO", 0.0280187, _dia(9, 9), _dia(9, 15)),
        # Un evento viejo, para --desde.
        _fila("Fondo F", None, "CFIFFF", None, "CFI", "Reparto", "$", 1000, datetime(2024, 3, 1), datetime(2024, 3, 7)),
    ],
    "Dividendos emisores extranjeros": [
        _fila("Apple", None, "AAPL", "AAPLCL", "Extranjero", "-", "US$", 0.26, _dia(9, 8), _dia(9, 14)),
        _fila("Wal-Mart", None, "WMT; WALMARTCL", None, "Extranjero", "-", "US$", 0.56, _dia(9, 8), _dia(9, 14)),
    ],
}


def _excel(ruta):
    libro = openpyxl.Workbook()
    libro.remove(libro.active)
    for nombre, encabezado in ENCABEZADOS.items():
        hoja = libro.create_sheet(nombre)
        hoja.append(["VARIACIONES DE CAPITAL"])
        hoja.append(["Resumen de Dividendos y Repartos de Capital"])
        hoja.append([None, None, None, None, None, None, None, None, "M  O  N  T  O ", None, "F  E  C  H  A"])
        hoja.append(encabezado)
        for fila in FILAS[nombre]:
            hoja.append(fila)
        hoja.append([])
    # Una hoja que no se lee.
    libro.create_sheet("Canjes").append(["Canjes de acciones/cuotas"])
    libro.save(ruta)
    return ruta


def _por_nemo(eventos):
    return {e.nemotecnico: e for e in eventos}


def test_lee_los_eventos_con_dinero_de_las_cuatro_hojas(tmp_path):
    lectura = bolsa.leer(_excel(tmp_path / "20260920.xlsx"))
    assert lectura.al == date(2026, 9, 20)
    # Cada fila con contenido es un evento o queda descartada: la lectura cuadra.
    for h in lectura.hojas:
        assert h.filas == h.eventos + len(h.descartadas)
    acciones = lectura.hojas[0]
    assert (acciones.filas, acciones.eventos, len(acciones.descartadas)) == (4, 2, 2)

    eventos = _por_nemo(lectura.eventos)
    acc = eventos["ACC"]
    assert (acc.clase, acc.moneda, acc.monto_por_cuota, acc.fecha_limite, acc.fecha_pago, acc.fuente) == (
        ec.DIVIDENDO,
        "CLP",
        D(40),
        date(2026, 9, 9),
        date(2026, 9, 15),
        ec.BOLSA,
    )
    assert eventos["ACCB"].clase == ec.REPARTO
    # Los dos nemotécnicos del fondo en dólares dan un solo evento.
    assert "CFI-DDDAE" not in eventos
    assert (eventos["CFIDDDA-E"].moneda, eventos["CFIDDDA-E"].monto_por_cuota) == ("USD", D("0.0031329609"))
    assert eventos["CFIEEEB-E"].monto_por_cuota == D("7.199693879412")
    assert eventos["CFIIII"].clase == ec.REPARTO and eventos["CFIIII"].moneda == "EUR"
    # Un monto que remite al documento queda vacío; uno ilegible queda vacío y dudoso.
    assert eventos["CFIGGG"].monto_por_cuota is None and "dudoso" not in eventos["CFIGGG"].texto
    assert eventos["CFIHHH"].monto_por_cuota is None and "dudoso" in eventos["CFIHHH"].texto
    assert lectura.hojas[2].dudosos == 1
    # Los extranjeros con su nemotécnico en dólares y en pesos.
    assert {"AAPL", "AAPLCL", "WMT", "WALMARTCL"} <= set(eventos)


def test_escribe_la_tabla_de_la_skill_con_la_fecha_del_excel(tmp_path):
    excel = _excel(tmp_path / "20260920.xlsx")
    datos = tmp_path / "datos"
    datos.mkdir()
    (datos / "eventos_bolsa_20260901.csv").write_text("anterior", encoding="utf-8")
    assert bolsa.main([str(excel), "--tabla", str(datos), "--desde", "2025-01-01"]) == 0
    assert [p.name for p in datos.iterdir()] == ["eventos_bolsa_20260920.csv"]

    tabla = bolsa.cargar(datos / "eventos_bolsa_20260920.csv")
    assert tabla.bolsa_al == date(2026, 9, 20)
    assert all(e.fuente == ec.BOLSA for e in tabla.eventos)
    # El evento de 2024 queda fuera por --desde.
    assert tabla.periodo() == (date(2026, 9, 14), date(2026, 9, 15))
    assert tabla.publica_la_bolsa("CFI-DDDAE") and not tabla.publica_la_bolsa("CFI-OTRO")
    assert bolsa.tabla_vigente(datos) == datos / "eventos_bolsa_20260920.csv"


def test_baja_el_excel_mas_reciente(tmp_path, monkeypatch):
    XLSX = _excel(tmp_path / "modelo.xlsx").read_bytes()
    carpeta = tmp_path / "bajados"
    pedidas = []

    class Respuesta:
        def __init__(self, datos):
            self.datos = datos

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return self.datos

    def abrir(pedido, timeout):
        pedidas.append(pedido.full_url)
        # El 20 no hay archivo: la Bolsa responde una página HTML.
        return Respuesta(b"<html>" if "20260920" in pedido.full_url else XLSX)

    monkeypatch.setattr(bolsa.urllib.request, "urlopen", abrir)
    ruta = bolsa.descargar(carpeta, date(2026, 9, 20))
    assert ruta == carpeta / "20260919.xlsx" and ruta.read_bytes() == XLSX
    assert len(pedidas) == 2
    assert pedidas[1] == (
        "https://servicioscms.bolsadesantiago.com/Paginas/Descarga.aspx?attach=Noticias%2Favisos+generales"
        "%2F20260919+resumen+dividendos+-+repartos+-+emisiones.xlsx"
    )
    # Si ya está bajado no lo vuelve a pedir.
    assert bolsa.descargar(carpeta, date(2026, 9, 19)) == ruta and len(pedidas) == 2


def test_sin_excel_en_los_dias_probados_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(bolsa.urllib.request, "urlopen", lambda pedido, timeout: (_ for _ in ()).throw(OSError("sin red")))
    with pytest.raises(RuntimeError, match="no se encontró el Excel de la Bolsa"):
        bolsa.descargar(tmp_path, date(2026, 9, 20), dias=2)


@pytest.mark.parametrize(
    "celda, monto, dudoso",
    [
        (40, D(40), False),
        (0.0031329609, D("0.0031329609"), False),
        (1e-07, D("0.0000001"), False),
        ("12,22353550190778", D("12.22353550190778"), False),
        ("1.234,5", D("1234.5"), False),
        ("0.17699525", D("0.17699525"), False),
        ("Ver documento", None, False),
        ("(ver observaciones)", None, False),
        ("-", None, False),
        ("2 18,1848371858", None, True),
        ("1.234", None, True),
    ],
)
def test_lee_el_monto_por_cuota(celda, monto, dudoso):
    assert bolsa._monto(celda) == (monto, dudoso)


# --- Cuadrar abonos con la tabla de la Bolsa ---------------------------------

CATALOGO = Catalogo(
    [
        Instrumento("ACCION", "ACC", "CLP", "EMISOR", "ACCIONES", "CUSTODIA_ACCIONES"),
        Instrumento("FONDO D", "CFI-DDDAE", "USD", "AGF", "CFI", "CUSTODIA_ACCIONES"),
    ]
)
TABLA_BOLSA = ec.Tabla(
    [
        ec.Evento("", "ACC", ec.DIVIDENDO, "CLP", D(40), date(2026, 9, 9), date(2026, 9, 15), fuente=ec.BOLSA),
        ec.Evento(
            "", "CFIDDDA-E", ec.DIVIDENDO, "USD", D("0.0031329609"), date(2026, 9, 9), date(2026, 9, 15), fuente=ec.BOLSA
        ),
    ],
    bolsa_al=date(2026, 9, 20),
)


def _cartola(posiciones, pagos):
    c = Cartola("BICE nueva", "x.pdf", "1-9", "", date(2026, 9, 1), date(2026, 9, 30), D("1000"))
    c.cuentas = {"0": Cuenta("0", "PORTAFOLIO", "Cuenta de Inversión")}
    c.posiciones = [
        Posicion("0", "Acciones", "Acciones", False, nombre, moneda, D(q), None, None, None, None)
        for nombre, moneda, q in posiciones
    ]
    c.movimientos_caja = [
        MovimientoCaja(fecha, "0", tipo, moneda, D(0), D(monto)) for tipo, moneda, monto, fecha in pagos
    ]
    return c


def test_identifica_el_dividendo_de_una_accion():
    c = _cartola([("ACCION", "CLP", 250), ("FONDO D", "USD", 10000)], [("DIVIDENDO EN PESOS", "CLP", 10000, date(2026, 9, 15))])
    resultado = ec.conciliar([c], CATALOGO, ec.Tabla.unir(TABLA_BOLSA, ec.Tabla([])))
    assert c.movimientos_caja[0].instrumento == "ACC"
    assert (resultado.asignados, resultado.dudosos) == (1, [])


def test_una_accion_sin_dividendo_en_el_excel_al_dia_no_tiene_reparto():
    c = _cartola([("ACCION", "CLP", 250)], [("DIVIDENDO EN PESOS", "CLP", 999, date(2026, 9, 2))])
    resultado = ec.conciliar([c], CATALOGO, TABLA_BOLSA)
    assert resultado.causas == {ec.SIN_REPARTO: 1}
    assert "sin reparto publicado en la fecha: ACC" in resultado.dudosos[0]


def test_un_abono_posterior_al_excel_pide_bajar_el_mas_reciente():
    c = _cartola([("ACCION", "CLP", 250)], [("DIVIDENDO EN PESOS", "CLP", 999, date(2026, 9, 28))])
    resultado = ec.conciliar([c], CATALOGO, TABLA_BOLSA)
    assert resultado.causas == {ec.POR_BAJAR: 1}


def test_un_fondo_que_publica_la_bolsa_no_se_consulta_en_datafondos():
    c = _cartola([("FONDO D", "USD", 10000)], [("DIVIDENDO EN DOLARES", "USD", 999, date(2026, 9, 2))])
    resultado = ec.conciliar([c], CATALOGO, TABLA_BOLSA, ec.Cobertura([]))
    assert resultado.pendientes == set()
    assert resultado.causas == {ec.SIN_REPARTO: 1}


def test_un_monto_muy_chico_se_escribe_y_se_vuelve_a_leer(tmp_path):
    evento = ec.Evento("", "CFIX", ec.REPARTO, "USD", D("1E-7"), date(2026, 9, 9), date(2026, 9, 15), fuente=ec.BOLSA)
    ruta = tmp_path / "eventos_bolsa_20260920.csv"
    ec.escribir([evento], ruta)
    assert bolsa.cargar(ruta).eventos[0].monto_por_cuota == D("0.0000001")
