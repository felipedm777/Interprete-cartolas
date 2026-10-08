"""Pruebas sobre las cartolas mensuales Sura anonimizadas.

Son 7 cartolas de agosto de 2026, cada una de un cliente distinto. La carpeta
trae además un estado Pershing que no es de este formato. Estas pruebas corren
solo donde existen las copias anonimizadas y comparan conteos agregados.
"""

import csv
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pymupdf
import pytest

from cartolas.__main__ import main
from cartolas.extractores import detectar, sura
from cartolas.validar import validar

DATOS = Path("/mnt/project-files/datos/anonimizado")
CARPETA = DATOS / "Training Data" / "Sura"

pytestmark = pytest.mark.skipif(not DATOS.exists(), reason="sin las cartolas anonimizadas")


def _cartolas_sura() -> list[Path]:
    return sorted(p for p in CARPETA.glob("*.pdf") if "pershing" not in p.name.lower())


@pytest.fixture(scope="module")
def cartolas():
    resultado = []
    for pdf in _cartolas_sura():
        doc = pymupdf.open(pdf)
        resultado.append(sura.extraer(pdf, sura.paginas(doc)))
    return resultado


def test_reconoce_solo_las_cartolas_sura():
    esperadas = set(_cartolas_sura())
    reconocidos = 0
    for pdf in sorted((DATOS / "Training Data").rglob("*.pdf")):
        doc = pymupdf.open(pdf)
        paginas = sura.paginas(doc)
        if pdf not in esperadas:
            assert not paginas, pdf.name
            continue
        assert paginas == list(range(doc.page_count)), pdf.name
        assert [e for e, _ in detectar(doc)] == [sura], pdf.name
        reconocidos += 1
    assert reconocidos == 7


def test_conteos(cartolas):
    assert len(cartolas) == 7
    assert Counter(p.tabla for c in cartolas for p in c.posiciones) == {
        "Fondos Mutuos Otras AGF": 17,
        "CFI": 16,
        "Acciones": 2,
    }
    assert Counter(p.seccion for c in cartolas for p in c.posiciones) == {
        "Fondos Mutuos": 17,
        "Fondos de Inversión": 16,
        "Acciones": 2,
    }
    assert Counter(p.previsional for c in cartolas for p in c.posiciones) == {True: 19, False: 16}
    assert Counter(p.moneda for c in cartolas for p in c.posiciones) == {"CLP": 29, "USD": 6}
    # Un FI recién comprado viene sin precio ni saldo.
    assert sum(p.precio_actual is None and p.valor_clp is None for c in cartolas for p in c.posiciones) == 1
    assert Counter(s.moneda for c in cartolas for s in c.saldos_caja) == {"CLP": 6, "USD": 4}
    assert Counter(m.moneda for c in cartolas for m in c.movimientos_caja) == {"CLP": 13, "USD": 2}
    assert Counter((m.tipo, m.destino) for c in cartolas for m in c.movimientos_titulos) == {
        ("INVERSION FM", "FFMM"): 7,
        ("RESCATE FM", "FFMM"): 1,
        ("COMPRA RV", "BOLSA"): 1,
        ("RESCATE CUSTODIA", "BOLSA"): 1,
    }
    assert all(c.institucion == "SURA" and c.rut == "" and c.nombre for c in cartolas)
    assert sum(c.tipo_cambio_usd is not None for c in cartolas) == 4
    assert all(c.desde.day == 1 and (c.hasta + timedelta(days=1)).day == 1 for c in cartolas)


def test_tipos_de_movimiento_de_caja(cartolas):
    assert Counter(m.tipo for c in cartolas for m in c.movimientos_caja) == {
        "DIVIDENDO EN PESOS": 8,
        "ABONO CUENTA INVERSION $": 2,
        "FACTURA COMPRA RV": 1,
        "RETIRO DESDE CTA INVERSIÓN": 1,
        "ABONO ORIGINADO POR PAGO RESCATES $ OWP": 1,
        "ABONO USDS DESDE CUENTA": 2,
    }


def test_cuentas(cartolas):
    cuentas = {n: cuenta for c in cartolas for n, cuenta in c.cuentas.items()}
    assert set(cuentas) == {"0", "BON_F", "CVN_A", "CVN_B", "DCN", "DCR"}
    assert (cuentas["0"].producto_base, cuentas["0"].tipo_apv) == ("CUENTA INVERSION", "")
    assert {n: (c.tipo_apv, c.regimen) for n, c in cuentas.items() if n != "0"} == {
        "BON_F": ("DAPVC", "APORTE"),
        "CVN_A": ("CV", "APORTE"),
        "CVN_B": ("CV", "BONIFICACIÓN"),
        "DCN": ("DC", "BONIFICACIÓN"),
        "DCR": ("DC", "BONIFICACIÓN"),
    }
    assert all(c.producto_base == "APV PRIME" for n, c in cuentas.items() if n != "0")
    # Todo lo usado está en las cuentas de su cartola.
    for c in cartolas:
        usadas = {
            x.cuenta for x in [*c.saldos_caja, *c.posiciones, *c.movimientos_caja, *c.movimientos_titulos]
        }
        assert usadas == set(c.cuentas), Path(c.archivo).name


def test_todas_las_cuadraturas_cierran(cartolas):
    total = 0
    for c in cartolas:
        controles = c.controles + validar(c)
        total += len(controles)
        malos = [x for x in controles if not x.ok]
        assert not malos, (Path(c.archivo).name, malos)
    assert total > 120


def test_exporta_el_juego_de_archivos_sura(tmp_path):
    assert main([*map(str, _cartolas_sura()), "--salida", str(tmp_path)]) == 0
    archivos = {p.name.split("_SURA_")[0]: p for p in tmp_path.glob("*_SURA_20260831_V2.csv")}
    assert len(archivos) == 7
    filas = {}
    for tipo, ruta in archivos.items():
        codificacion = "utf-8" if tipo == "MOVIMIENTOS_PERSHING" else "cp1252"
        with open(ruta, encoding=codificacion, newline="") as f:
            filas[tipo] = list(csv.DictReader(f, delimiter=";"))
    assert {tipo: len(f) for tipo, f in filas.items()} == {
        "SALDOS_CAJA": 10,
        "SALDOS_FFMM": 17,
        "CUSTODIA_ACCIONES": 18,
        "MOVIMIENTOS_DE_CAJA": 15,
        "MOVIMIENTOS_BOLSA": 2,
        "MOVIMIENTOS_FFMM": 8,
        "MOVIMIENTOS_PERSHING": 0,
    }
    # Las acciones por nemotécnico y 5 FI por alias.
    assert sum(bool(f["NemotecnicoInstrumento"]) for f in filas["CUSTODIA_ACCIONES"]) == 7
    assert all(f["RutCliente"] == "" for f in filas["SALDOS_CAJA"])
    reporte = next(tmp_path.glob("REPORTE_*.md")).read_text(encoding="utf-8")
    assert "no cuadran" not in reporte
