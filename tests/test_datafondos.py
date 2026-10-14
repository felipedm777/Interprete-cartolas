"""Consulta a la API de DataFondos y su uso al correr la skill, con la API simulada."""

import argparse
import io
import json
import urllib.error
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from cartolas import __main__ as skill
from cartolas import bolsa, datafondos
from cartolas import eventos_capital as ec
from cartolas.catalogo import Catalogo, Instrumento
from cartolas.modelo import Cartola, Cuenta, MovimientoCaja, Posicion

CATALOGO = Catalogo([Instrumento("FONDO A", "CFI-AE", "CLP", "AGF", "CFI", "CUSTODIA_ACCIONES")])
CIERRE = date(2026, 9, 30)

# Lo que responde la API (y el MCP) de DataFondos, que escribe el nemotécnico
# de FONDO A con el guion en otro lugar.
RESUMEN = {
    "ok": True,
    "data": [
        {
            "rut": "9991",
            "nombre": "FONDO A",
            "serie": "A",
            "nemo": "CFIA-E",
            "total": 3,
            "ultima_fecha": "2026-09-29",
            "ultima_actualizacion": "2026-10-14 06:00:00",
        }
    ],
}
DIVIDENDOS = {
    "ok": True,
    "data": [
        {
            "rut": "9991",
            "nemo": "CFIA-E",
            "evento": "DIVIDENDO PROV. $ 2,5",
            "moneda": "$",
            "pago_por_accion": 2.5,
            "fecha_limite": "2026-09-23",
            "fecha_pago": "2026-09-29",
            "anulado": 0,
        }
    ],
    "total": 1,
}


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _cartola():
    """Un abono de 250 sin instrumento en una cuenta con 100 cuotas de FONDO A."""
    c = Cartola("BICE nueva", "x.pdf", "1-9", "", date(2026, 9, 1), CIERRE, D("1000"))
    c.cuentas = {"0": Cuenta("0", "PORTAFOLIO", "Cuenta de Inversión")}
    c.posiciones = [
        Posicion("0", "Alternativos", "Fondos De Inversión", False, "FONDO A", "CLP", D(100), None, None, None, None)
    ]
    c.movimientos_caja = [MovimientoCaja(CIERRE, "0", "DIVIDENDO EN PESOS", "CLP", D(0), D(250))]
    return c


class ClienteFalso:
    """DataFondos simulado: anota qué se le pidió."""

    def __init__(self, dividendos=None):
        self.pedidos = []
        self._dividendos = dividendos or {("9991", "CFIA-E"): DIVIDENDOS}

    def resumen(self):
        self.pedidos.append("resumen")
        return RESUMEN

    def dividendos(self, rut, nemo):
        self.pedidos.append((rut, nemo))
        if (rut, nemo) not in self._dividendos:
            raise datafondos.DataFondosError("DataFondos no tiene ese fondo")
        return self._dividendos[(rut, nemo)]


@pytest.mark.parametrize(
    "url",
    ["https://df.test", "https://df.test/", "https://df.test/api/v1", " https://df.test/api/v1/ "],
)
def test_acepta_la_url_con_o_sin_api_v1(url):
    assert datafondos.base_url(url) == "https://df.test/api/v1"


def test_sin_las_variables_de_entorno_no_consulta():
    assert datafondos.desde_entorno({}) is None
    assert datafondos.desde_entorno({"DATAFONDOS_API_URL": "https://df.test"}) is None
    cliente = datafondos.desde_entorno(
        {"DATAFONDOS_API_URL": "https://df.test", "DATAFONDOS_API_KEY": "k", "DATAFONDOS_TIMEOUT": "5"}
    )
    assert (cliente.url, cliente.timeout) == ("https://df.test/api/v1", 5.0)
    # La key no aparece al mostrar el cliente.
    assert "k'" not in repr(cliente)
    with pytest.raises(datafondos.DataFondosError, match="URL http"):
        datafondos.desde_entorno({"DATAFONDOS_API_URL": "df.test", "DATAFONDOS_API_KEY": "k"})


def test_pide_los_repartos_del_fondo_con_la_key_en_el_encabezado(monkeypatch):
    pedidos = []

    def abrir(pedido, timeout):
        pedidos.append((pedido.full_url, pedido.get_header("X-api-key"), timeout))
        return Respuesta(json.dumps(DIVIDENDOS).encode())

    monkeypatch.setattr(datafondos.urllib.request, "urlopen", abrir)
    cliente = datafondos.Cliente("https://df.test", "clave", 7)
    assert cliente.dividendos("9991", "CFIA-E") == DIVIDENDOS
    assert pedidos == [("https://df.test/api/v1/fondos/9991/dividendos?nemo=CFIA-E", "clave", 7)]
    with pytest.raises(datafondos.DataFondosError, match="RUT de fondo"):
        cliente.dividendos("../fondos", "CFIA-E")


@pytest.mark.parametrize(
    "falla, mensaje",
    [
        (urllib.error.HTTPError("u", 401, "", {}, io.BytesIO(b'{"ok": false, "error": "API key"}')), "DATAFONDOS_API_KEY"),
        (urllib.error.HTTPError("u", 403, "", {}, io.BytesIO(b"")), "valores:read"),
        (urllib.error.HTTPError("u", 429, "", {}, io.BytesIO(b"")), "límite"),
        (urllib.error.URLError("sin red"), "no se pudo conectar"),
    ],
)
def test_explica_por_que_fallo_la_consulta(monkeypatch, falla, mensaje):
    def abrir(pedido, timeout):
        raise falla

    monkeypatch.setattr(datafondos.urllib.request, "urlopen", abrir)
    with pytest.raises(datafondos.DataFondosError, match=mensaje):
        datafondos.Cliente("https://df.test", "clave").resumen()


def test_una_respuesta_que_no_es_json_apunta_a_la_url(monkeypatch):
    monkeypatch.setattr(datafondos.urllib.request, "urlopen", lambda p, timeout: Respuesta(b"<html>"))
    with pytest.raises(datafondos.DataFondosError, match="DATAFONDOS_API_URL"):
        datafondos.Cliente("https://df.test", "clave").resumen()


def test_actualiza_la_cobertura_y_agrega_los_repartos_consultados(tmp_path):
    cliente = ClienteFalso()
    cobertura = datafondos.actualizar_cobertura(cliente, tmp_path / "cobertura.csv", tmp_path / "json")
    seguido = cobertura.buscar("CFI-AE")
    assert (seguido.rut_fondo, seguido.actualizado) == ("9991", date(2026, 10, 14))
    assert json.loads((tmp_path / "json" / "resumen.json").read_text(encoding="utf-8")) == RESUMEN

    tabla = tmp_path / "eventos_capital.csv"
    fondos = [seguido, ec.Seguido("CFI-X", "1234")]
    consulta = datafondos.consultar(cliente, fondos, tabla, date(2025, 1, 1), tmp_path / "json")
    assert (consulta.consultados, consulta.leidos, consulta.agregados) == (["CFIA-E"], 1, 1)
    assert consulta.fallas == ["CFI-X: DataFondos no tiene ese fondo"]
    assert [(e.nemotecnico, e.monto_por_cuota) for e in ec.Tabla.cargar(tabla).eventos] == [("CFIA-E", D("2.5"))]
    assert (tmp_path / "json" / "CFIA-E.json").exists()
    # Consultar de nuevo no repite el evento.
    assert datafondos.consultar(cliente, [seguido], tabla).agregados == 0


def test_pide_cada_fondo_pendiente_con_el_nemotecnico_de_datafondos():
    cobertura = ec.Cobertura(ec._cobertura_json(RESUMEN))
    fondos, sin_rut = datafondos.fondos_por_consultar({("CFI-AE", "2026-09"), ("CFI-AE", "2026-08")}, cobertura)
    assert [(f.rut_fondo, f.nemotecnico) for f in fondos] == [("9991", "CFIA-E")]
    assert datafondos.fondos_por_consultar({("CFI-OTRO", "2026-09")}, cobertura) == ([], ["CFI-OTRO"])


# Una tabla con los repartos de otro fondo: le falta FONDO A.
OTRO = ec.Evento("5", "CFI-Z", ec.DIVIDENDO, "CLP", D(1), date(2026, 9, 1), date(2026, 9, 5))


def test_los_pendientes_se_calculan_sin_tocar_las_cartolas():
    c = _cartola()
    cobertura = ec.Cobertura(ec._cobertura_json(RESUMEN))
    assert ec.pendientes([c], CATALOGO, ec.Tabla([OTRO]), cobertura) == {("CFI-AE", "2026-09")}
    tabla = ec.Tabla(ec._desde_json(DIVIDENDOS))
    assert ec.pendientes([c], CATALOGO, tabla, cobertura) == set()
    assert c.movimientos_caja[0].instrumento == "" and not c.avisos


def _args(**kwargs):
    return argparse.Namespace(**{"sin_internet": False, "eventos_capital": None, "bolsa": "no", **kwargs})


def test_al_correr_consulta_en_datafondos_los_fondos_que_faltan(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "RUTA_TABLA", tmp_path / "eventos_capital.csv")
    monkeypatch.setattr(ec, "RUTA_COBERTURA", tmp_path / "datafondos_cobertura.csv")
    ec.escribir([OTRO], ec.RUTA_TABLA)
    cliente = ClienteFalso()
    monkeypatch.setattr(datafondos, "desde_entorno", lambda: cliente)
    c = _cartola()

    lineas = skill._actualizar_tablas(_args(), [c], CATALOGO, tmp_path / "salida", argparse.ArgumentParser())
    assert cliente.pedidos == ["resumen", ("9991", "CFIA-E")]
    assert lineas == [
        "Se actualizó desde DataFondos la cobertura de la skill: 1 fondos y series.",
        "Se consultaron 1 fondos en DataFondos: 1 repartos nuevos en la tabla de la skill.",
    ]
    assert sorted(p.name for p in (tmp_path / "salida" / "datafondos").iterdir()) == ["CFIA-E.json", "resumen.json"]

    # Con la tabla actualizada, la conciliación identifica el fondo del abono.
    resultado = ec.conciliar([c], CATALOGO, ec.Tabla.cargar(ec.RUTA_TABLA), ec.Cobertura.cargar(ec.RUTA_COBERTURA))
    assert (resultado.asignados, resultado.dudosos) == (1, [])
    assert c.movimientos_caja[0].instrumento == "CFI-AE"


def test_sin_la_api_configurada_el_reporte_lo_dice(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "RUTA_TABLA", tmp_path / "eventos_capital.csv")
    lineas = skill._actualizar_tablas(_args(), [_cartola()], CATALOGO, tmp_path, argparse.ArgumentParser())
    assert lineas == [
        "No se consultó DataFondos: faltan las variables DATAFONDOS_API_URL y DATAFONDOS_API_KEY (ver README)."
    ]


def test_una_falla_de_datafondos_no_detiene_la_corrida(tmp_path, monkeypatch):
    class Caido(ClienteFalso):
        def resumen(self):
            raise datafondos.DataFondosError("no se pudo conectar con DataFondos: sin red")

    monkeypatch.setattr(datafondos, "desde_entorno", lambda: Caido())
    lineas = skill._actualizar_tablas(_args(), [_cartola()], CATALOGO, tmp_path, argparse.ArgumentParser())
    assert lineas == [
        "No se pudo consultar DataFondos (no se pudo conectar con DataFondos: sin red): se usaron la tabla y "
        "la cobertura de la skill."
    ]


def test_sin_internet_no_actualiza_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(datafondos, "desde_entorno", lambda: pytest.fail("no debía consultar DataFondos"))
    monkeypatch.setattr(bolsa, "actualizar", lambda *a, **k: pytest.fail("no debía bajar el Excel"))
    args = _args(sin_internet=True, bolsa=None)
    assert skill._actualizar_tablas(args, [_cartola()], CATALOGO, tmp_path, argparse.ArgumentParser()) == []


@pytest.mark.parametrize(
    "tabla_al, baja",
    [(date(2026, 10, 9), False), (date(2026, 9, 30), False), (date(2026, 9, 15), True), (None, True)],
)
def test_baja_el_excel_de_la_bolsa_solo_si_la_tabla_es_anterior_al_cierre(tmp_path, monkeypatch, tabla_al, baja):
    bajados = []

    def actualizar(carpeta):
        bajados.append(carpeta)
        return Path("eventos_bolsa_20261013.csv"), bolsa.Lectura(date(2026, 10, 13), [], [])

    monkeypatch.setattr(bolsa, "fecha_vigente", lambda: tabla_al)
    monkeypatch.setattr(bolsa, "actualizar", actualizar)
    lineas = skill._actualizar_bolsa(tmp_path / "bolsa", CIERRE)
    assert bajados == ([tmp_path / "bolsa"] if baja else [])
    assert lineas == (
        ["Se bajó el Excel de la Bolsa del 13-10-2026 y se actualizó la tabla de la skill (eventos_bolsa_20261013.csv)."]
        if baja
        else []
    )


def test_si_no_puede_bajar_el_excel_sigue_con_la_tabla_que_tiene(tmp_path, monkeypatch):
    def actualizar(carpeta):
        raise RuntimeError("no se encontró el Excel de la Bolsa")

    monkeypatch.setattr(bolsa, "fecha_vigente", lambda: date(2026, 9, 15))
    monkeypatch.setattr(bolsa, "actualizar", actualizar)
    assert skill._actualizar_bolsa(tmp_path, CIERRE) == [
        "No se pudo bajar el Excel de la Bolsa (no se encontró el Excel de la Bolsa): se usó la tabla del "
        "Excel del 15-09-2026."
    ]


def test_el_comando_actualiza_la_cobertura_y_los_fondos_indicados(tmp_path, monkeypatch, capsys):
    cliente = ClienteFalso()
    monkeypatch.setattr(datafondos, "desde_entorno", lambda: cliente)
    tabla, cobertura = tmp_path / "eventos_capital.csv", tmp_path / "cobertura.csv"
    argumentos = ["--tabla", str(tabla), "--cobertura", str(cobertura), "--desde", "2026-01-01"]
    assert datafondos.main(argumentos) == 0
    assert cliente.pedidos == ["resumen"] and not tabla.exists()
    assert datafondos.main(argumentos + ["--fondo", "9991", "CFIA-E"]) == 0
    assert len(ec.Tabla.cargar(tabla)) == 1
    assert "1 fondos consultados: 1 eventos, 1 nuevos" in capsys.readouterr().out
    # Un fondo que DataFondos no tiene se informa y el comando termina con error.
    assert datafondos.main(argumentos + ["--fondo", "1234", "CFI-X"]) == 1


def test_el_comando_sin_las_variables_explica_que_falta(capsys):
    with pytest.raises(SystemExit):
        datafondos.main([])
    assert "DATAFONDOS_API_URL" in capsys.readouterr().err
