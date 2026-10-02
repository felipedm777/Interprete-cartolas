"""Pruebas sobre los informes patrimoniales de Larrainvial anonimizados.

Son 14 informes mensuales de 2 clientes: 12 provisorios y 2 cartolas
definitivas. Estas pruebas corren solo donde existen las copias anonimizadas
y comparan conteos agregados.
"""

from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import pymupdf
import pytest

from cartolas.__main__ import main
from cartolas.extractores import detectar, larrainvial
from cartolas.validar import validar

DATOS = Path("/mnt/project-files/datos/anonimizado")
CARPETA = DATOS / "Training Data" / "Larrainvial"

pytestmark = pytest.mark.skipif(not DATOS.exists(), reason="sin las cartolas anonimizadas")


@pytest.fixture(scope="module")
def cartolas():
    resultado = []
    for pdf in sorted(CARPETA.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        resultado.append(larrainvial.extraer(pdf, larrainvial.paginas(doc)))
    return resultado


def test_reconoce_solo_los_informes_larrainvial():
    reconocidos = 0
    for pdf in sorted((DATOS / "Training Data").rglob("*.pdf")):
        doc = pymupdf.open(pdf)
        paginas = larrainvial.paginas(doc)
        if pdf.parent != CARPETA:
            assert not paginas, pdf.name
            continue
        assert paginas == list(range(doc.page_count)), pdf.name
        assert [e for e, _ in detectar(doc)] == [larrainvial], pdf.name
        reconocidos += 1
    assert reconocidos == 14


def test_conteos(cartolas):
    assert len(cartolas) == 14
    assert Counter(p.tabla for c in cartolas for p in c.posiciones) == {
        "CFI": 46,
        "Fondos Mutuos Otras AGF": 7,
    }
    assert Counter(p.seccion for c in cartolas for p in c.posiciones) == {"Alternativos": 44, "Renta fija": 9}
    assert Counter(s.moneda for c in cartolas for s in c.saldos_caja) == {"CLP": 13, "USD": 8}
    assert Counter(m.moneda for c in cartolas for m in c.movimientos_caja) == {"CLP": 8, "USD": 5}
    assert Counter((m.tipo, m.destino) for c in cartolas for m in c.movimientos_titulos) == {
        ("COMPRA RV", "BOLSA"): 5,
        ("INGRESO RV", "BOLSA"): 1,
        ("DISMINUCION DE CAPITAL", "BOLSA"): 1,
        ("INVERSION FM", "FFMM"): 2,
        ("RESCATE FM", "FFMM"): 4,
    }
    assert Counter(c.provisoria for c in cartolas) == {True: 12, False: 2}
    assert len({c.rut for c in cartolas}) == 2
    assert all(c.institucion == "LARRAINVIAL" and c.tipo_cambio_usd and c.tipo_cambio_eur for c in cartolas)
    assert all(c.desde.day == 1 and (c.hasta + timedelta(days=1)).day == 1 for c in cartolas)
    assert all(list(c.cuentas) == ["0"] and c.cuentas["0"].producto_base == "CUENTA INVERSION" for c in cartolas)


def test_tipos_de_movimiento_de_caja(cartolas):
    tipos = Counter(m.tipo for c in cartolas for m in c.movimientos_caja)
    assert tipos == {
        "FACTURA COMPRA RV": 2,
        "DIVIDENDO EN DOLARES": 1,
        "OPERACION DOLAR": 1,
        "CARGO EN DOLARES": 1,
        "CARGO COMPROMISO DE INVERSION $ OWP": 2,
        "ABONO ORIGINADO POR PAGO RESCATES $ OWP": 2,
        "ABONO ORIGINADO POR PAGO RESCATE US$ OWP": 2,
        "ABONO POR DISMINUCION DE CAPITAL": 1,
        "RETIRO DE CTA CTE": 1,
    }


def test_todas_las_cuadraturas_cierran(cartolas):
    total = 0
    for c in cartolas:
        controles = c.controles + validar(c)
        total += len(controles)
        malos = [x for x in controles if not x.ok]
        assert not malos, (Path(c.archivo).name, malos)
    assert total > 350


def test_continuidad_del_patrimonio_entre_meses(cartolas):
    por_rut = defaultdict(list)
    for c in cartolas:
        por_rut[c.rut].append(c)
    transiciones = 0
    for meses in por_rut.values():
        meses.sort(key=lambda c: c.desde)
        for anterior, siguiente in zip(meses, meses[1:]):
            if siguiente.desde != anterior.hasta + timedelta(days=1):
                continue
            transiciones += 1
            assert anterior.totales["patrimonio_fin"] == siguiente.totales["patrimonio_inicio"], Path(
                siguiente.archivo
            ).name
    assert transiciones == 11


def test_exporta_el_juego_de_archivos_larrainvial(tmp_path):
    assert main([str(CARPETA), "--salida", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*_LARRAINVIAL_*_V2.csv"))) == 7
    reporte = next(tmp_path.glob("REPORTE_*.md")).read_text(encoding="utf-8")
    assert "no cuadran" not in reporte
