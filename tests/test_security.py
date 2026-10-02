"""Pruebas sobre las cartolas Security anonimizadas.

Vienen pegadas después de una cartola BICE antigua en 10 de los PDF de
"BICE viejas"; dos de esos PDF son el mismo estado (duplicado exacto), así que
se cuentan una sola vez. Los PDF no están en el repositorio: estas pruebas
corren solo donde existen sus copias anonimizadas y comparan conteos agregados.
"""

from collections import Counter
from pathlib import Path

import pymupdf
import pytest

from cartolas.catalogo import Catalogo
from cartolas.extractores import security

DATOS = Path("/mnt/project-files/datos/anonimizado")
CARTOLAS = DATOS / "Training Data" / "BICE viejas"

pytestmark = pytest.mark.skipif(not DATOS.exists(), reason="sin las cartolas anonimizadas")


@pytest.fixture(scope="module")
def cartolas():
    vistas, resultado = set(), []
    for pdf in sorted(CARTOLAS.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        paginas = security.paginas(doc)
        texto = "".join(doc[i].get_text() for i in paginas)
        if paginas and texto not in vistas:
            vistas.add(texto)
            resultado.append(security.extraer(pdf, paginas))
    return resultado


def test_reconoce_solo_la_parte_security():
    con_security = 0
    for pdf in sorted((DATOS / "Training Data").rglob("*.pdf")):
        doc = pymupdf.open(pdf)
        paginas = security.paginas(doc)
        if not paginas:
            continue
        assert pdf.parent == CARTOLAS, pdf.name
        # La parte Security cierra el PDF, en carta apaisada, después de la BICE antigua en A4 vertical.
        assert paginas == list(range(paginas[0], doc.page_count)), pdf.name
        assert all(round(doc[i].rect.width) == 792 for i in paginas), pdf.name
        assert round(doc[paginas[0] - 1].rect.width) == 595, pdf.name
        con_security += 1
    assert con_security == 10


def test_conteos(cartolas):
    assert len(cartolas) == 9
    assert {(c.desde.isoformat(), c.hasta.isoformat()) for c in cartolas} == {("2026-04-01", "2026-04-30")}
    assert {c.institucion for c in cartolas} == {"SECURITY"}
    assert all(c.tipo_cambio_usd and c.tipo_cambio_eur for c in cartolas)
    tablas = Counter(p.tabla for c in cartolas for p in c.posiciones)
    assert tablas == {"Fondos Mutuos": 17, "CFI": 161, "Acciones": 2}
    assert sum(p.previsional for c in cartolas for p in c.posiciones) == 109
    assert Counter(s.moneda for c in cartolas for s in c.saldos_caja) == {"CLP": 15, "USD": 7}
    assert sum(len(c.movimientos_caja) for c in cartolas) == 133
    destinos = Counter(m.destino for c in cartolas for m in c.movimientos_titulos)
    assert destinos == {"FFMM": 24, "BOLSA": 22, "": 80}
    grupos = Counter(cuenta.grupo for c in cartolas for cuenta in c.cuentas.values())
    assert grupos == {"No previsional": 17, "Previsional": 10}


def test_todas_las_cuadraturas_cierran(cartolas):
    for c in cartolas:
        assert len(c.controles) >= 20, Path(c.archivo).name
        malos = [x for x in c.controles if not x.ok]
        assert not malos, (Path(c.archivo).name, malos)


def test_fondos_mutuos_en_la_tabla_maestra(cartolas):
    """Los fondos se encuentran con el nombre corto de la cartola (alias) y las
    transacciones, con la serie que se deduce de las posiciones."""
    catalogo = Catalogo.cargar()
    fondos = [p for c in cartolas for p in c.posiciones if p.tabla == "Fondos Mutuos"]
    encontrados = [p for p in fondos if catalogo.buscar(p.instrumento, p.moneda, p.precio_actual)]
    # Falta I. FUND S&P/CLX: el export no permite confirmar a qué serie corresponde.
    assert len(encontrados) == len(fondos) - 1
    movimientos = [m for c in cartolas for m in c.movimientos_titulos if m.destino == "FFMM"]
    assert all(catalogo.buscar(m.instrumento, m.moneda, m.precio) for m in movimientos)
