"""Pruebas sobre las cartolas BICE nuevas anonimizadas.

Los PDF y el export de ejemplo no están en el repositorio; estas pruebas corren
solo donde existen sus copias anonimizadas y comparan conteos agregados.
"""

import csv
from collections import defaultdict
from pathlib import Path

import pymupdf
import pytest

from cartolas.__main__ import main
from cartolas.extractores import bice_nueva, detectar
from cartolas.validar import validar

DATOS = Path("/mnt/project-files/datos/anonimizado")
CARTOLAS = DATOS / "Training Data" / "BICE nuevas"
EJEMPLO = DATOS / "Example Export"

pytestmark = pytest.mark.skipif(not CARTOLAS.exists(), reason="sin las cartolas anonimizadas")


@pytest.fixture(scope="module")
def cartolas():
    return [bice_nueva.extraer(p) for p in sorted(CARTOLAS.glob("*.pdf"))]


def test_reconoce_solo_bice_nueva():
    for pdf in sorted((DATOS / "Training Data").rglob("*.pdf")):
        doc = pymupdf.open(pdf)
        partes = [(e, paginas) for e, paginas in detectar(doc) if e is bice_nueva]
        if pdf.parent == CARTOLAS:
            assert partes == [(bice_nueva, list(range(doc.page_count)))], pdf.name
        else:
            assert not partes, pdf.name


def test_conteos(cartolas):
    assert len(cartolas) == 20
    assert sum(len(c.posiciones) for c in cartolas) == 185
    assert sum(len(c.saldos_caja) for c in cartolas) == 23
    assert sum(len(c.movimientos_caja) for c in cartolas) == 78
    assert sum(len(c.movimientos_titulos) for c in cartolas) == 337
    assert {(c.desde.isoformat(), c.hasta.isoformat()) for c in cartolas} == {("2026-09-01", "2026-09-30")}


def test_todas_las_cuadraturas_cierran(cartolas):
    for c in cartolas:
        malos = [x for x in validar(c) if not x.ok]
        assert not malos, (Path(c.archivo).name, malos)


@pytest.mark.skipif(not EJEMPLO.exists(), reason="sin el export de ejemplo anonimizado")
def test_salida_coincide_con_el_export_de_ejemplo(tmp_path):
    """Las posiciones que están en ambos deben coincidir en todo lo que no depende
    de la fecha. El export es del 22-09 y las cartolas del 30-09, así que
    cantidades y precio promedio pueden cambiar si hubo compras entre medio."""
    assert main([str(CARTOLAS), "--salida", str(tmp_path)]) == 0
    campos = [
        "Portafolio", "ProductoBase", "Producto", "NemotecnicoInstrumento", "MonedaInstrumento",
        "Emisor", "MonedaValoracionPatrimonio", "TipoAPV", "DescripcionTipoRegimenTributario",
    ]  # fmt: skip
    for tipo, pares_minimos in (("SALDOS_FFMM", 36), ("CUSTODIA_ACCIONES", 134)):
        nuestras = _leer(next(tmp_path.glob(f"{tipo}_10038_20260930_V2.csv")))
        ejemplo = defaultdict(list)
        for r in _leer(next(EJEMPLO.glob(f"{tipo}_*.csv"))):
            ejemplo[(r["RutCliente"], r["Cuenta"], r["Instrumento"])].append(r)
        pares = misma_cantidad = 0
        for r in nuestras:
            candidatos = ejemplo.get((r["RutCliente"], r["Cuenta"], r["Instrumento"]))
            if not candidatos:
                continue
            pares += 1
            e = candidatos[0]
            assert [r[c] for c in campos] == [e[c] for c in campos]
            misma_cantidad += any(x["Cantidad"] == r["Cantidad"] for x in candidatos)
        assert pares >= pares_minimos
        assert misma_cantidad >= pares - 2


def _leer(ruta: Path) -> list[dict]:
    with open(ruta, encoding="cp1252", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))
