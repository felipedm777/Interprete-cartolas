"""Pruebas sobre la parte BICE de las cartolas antiguas anonimizadas.

Los PDF de "BICE viejas" traen una cartola BICE de formato antiguo y, en la
mayoría, una cartola Valores Security pegada después. Estas pruebas corren
solo donde existen las copias anonimizadas y comparan conteos agregados.
"""

from collections import Counter
from pathlib import Path

import pymupdf
import pytest

from cartolas.__main__ import _huella, main
from cartolas.extractores import bice_antigua, detectar
from cartolas.validar import validar

DATOS = Path("/mnt/project-files/datos/anonimizado")
CARPETA = DATOS / "Training Data" / "BICE viejas"

pytestmark = pytest.mark.skipif(not CARPETA.exists(), reason="sin las cartolas anonimizadas")


@pytest.fixture(scope="module")
def cartolas():
    """Una por PDF distinto: hay un par de archivos con el mismo contenido."""
    vistas, resultado = set(), []
    for pdf in sorted(CARPETA.glob("*.pdf")):
        doc = pymupdf.open(pdf)
        huella = _huella(doc)
        if huella in vistas:
            continue
        vistas.add(huella)
        resultado.append(bice_antigua.extraer(pdf, bice_antigua.paginas(doc)))
    return resultado


def test_reconoce_la_parte_bice_de_las_viejas():
    for pdf in sorted((DATOS / "Training Data").rglob("*.pdf")):
        doc = pymupdf.open(pdf)
        paginas = bice_antigua.paginas(doc)
        if pdf.parent != CARPETA:
            assert not paginas, pdf.name
            continue
        assert paginas == list(range(len(paginas))) and len(paginas) >= 4, pdf.name
        # Lo que sigue, si hay algo, es la cartola Security en páginas apaisadas.
        resto = range(len(paginas), doc.page_count)
        assert all(doc[i].rect.width > doc[i].rect.height for i in resto), pdf.name
        partes = [e for e, _ in detectar(doc)]
        assert partes[0] is bice_antigua, pdf.name


def test_conteos(cartolas):
    assert len(cartolas) == 11
    tablas = Counter(p.tabla for c in cartolas for p in c.posiciones)
    assert tablas == {
        "Fondos Mutuos": 33,
        "Fondos Inversión Bice": 3,
        "Acciones": 8,
        "CFI": 5,
        "Depósitos a Plazo": 11,
    }
    assert sum(len(c.saldos_caja) for c in cartolas) == 4
    assert sum(len(c.movimientos_caja) for c in cartolas) == 26
    assert sum(len(c.movimientos_titulos) for c in cartolas) == 25
    assert {(c.desde.isoformat(), c.hasta.isoformat()) for c in cartolas} == {("2026-04-01", "2026-04-30")}
    assert all(c.tipo_cambio_usd is None and c.institucion == "BICE" for c in cartolas)


def test_todas_las_cuadraturas_cierran(cartolas):
    total = 0
    for c in cartolas:
        controles = c.controles + validar(c)
        total += len(controles)
        malos = [x for x in controles if not x.ok]
        assert not malos, (Path(c.archivo).name, malos)
    assert total > 500


def test_exporta_un_juego_de_archivos_por_institucion(tmp_path):
    assert main([str(p) for p in sorted(CARPETA.glob("*.pdf"))] + ["--salida", str(tmp_path)]) == 0
    for institucion in ("BICE", "SECURITY"):
        assert len(list(tmp_path.glob(f"*_{institucion}_20260430_V2.csv"))) == 7
    reporte = next(tmp_path.glob("REPORTE_*.md")).read_text(encoding="utf-8")
    assert "duplicado" in reporte
    # Sin tipo de cambio propio, la parte BICE usa el de la cartola Security.
    assert "se usó el USD" in reporte
