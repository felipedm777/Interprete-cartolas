"""Pruebas sobre los estados de cuenta Pershing anonimizados.

Son 6 estados con la misma plantilla y distinta configuración: 5 meses
consecutivos de una cuenta que llega por BICE y 1 mes de otra cuenta que llega
por Sura, con una posición en libras. Estas pruebas corren solo donde existen
las copias anonimizadas y comparan conteos agregados.
"""

import csv
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pymupdf
import pytest

from cartolas.__main__ import main
from cartolas.extractores import detectar, pershing
from cartolas.validar import validar

DATOS = Path("/mnt/project-files/datos/anonimizado")
CORREDORA = DATOS / "Training Data" / "BICE viejas" / "Corredora de bolsa"
SURA = DATOS / "Training Data" / "Sura"

pytestmark = pytest.mark.skipif(not DATOS.exists(), reason="sin las cartolas anonimizadas")


def _estados() -> list[Path]:
    return sorted(CORREDORA.glob("*_MSTAT_*.pdf")) + sorted(SURA.glob("Sura pershing-*.pdf"))


@pytest.fixture(scope="module")
def cartolas():
    resultado = []
    for pdf in _estados():
        doc = pymupdf.open(pdf)
        resultado.append(pershing.extraer(pdf, pershing.paginas(doc)))
    return resultado


def test_reconoce_solo_los_estados_pershing():
    estados = set(_estados())
    reconocidos = 0
    for pdf in sorted((DATOS / "Training Data").rglob("*.pdf")):
        doc = pymupdf.open(pdf)
        paginas = pershing.paginas(doc)
        if pdf not in estados:
            assert not paginas, pdf.name
            continue
        assert paginas == list(range(doc.page_count)), pdf.name
        assert [e for e, _ in detectar(doc)] == [pershing], pdf.name
        reconocidos += 1
    assert reconocidos == 6


def test_conteos(cartolas):
    assert len(cartolas) == 6
    assert Counter(p.tabla for c in cartolas for p in c.posiciones) == {"Bonos": 5, "Acciones": 3, "ETF": 9}
    assert Counter(p.moneda for c in cartolas for p in c.posiciones) == {"USD": 16, "GBP": 1}
    assert all(p.nemotecnico and p.valor_clp is None for c in cartolas for p in c.posiciones)
    # Las acciones y los ETF traen precio y valor; el bono en default, no.
    assert all(
        (p.precio_actual is not None and p.valor_usd is not None) == (p.tabla != "Bonos")
        for c in cartolas
        for p in c.posiciones
    )
    # Solo la posición en libras viene sin base de costo.
    assert sum(p.precio_promedio is None for c in cartolas for p in c.posiciones) == 1
    assert Counter(s.moneda for c in cartolas for s in c.saldos_caja) == {"USD": 6}
    assert Counter(m.tipo for c in cartolas for m in c.movimientos_titulos) == {
        "MONEY FUND INCOME": 6,
        "SECURITY LIQUIDATED": 1,
    }
    assert Counter(m.producto for c in cartolas for m in c.movimientos_titulos) == {"MONEY MARKET": 6, "BONOS": 1}
    assert all(
        m.destino == "PERSHING" and m.nemotecnico and m.moneda == "USD" and m.cantidad is None and m.monto
        for c in cartolas
        for m in c.movimientos_titulos
    )
    assert all(c.institucion == "PERSHING" and c.rut == "" and c.tipo_cambio_usd is None for c in cartolas)
    assert all(c.nombre for c in cartolas)
    assert all(c.desde.day == 1 and (c.hasta + timedelta(days=1)).day == 1 for c in cartolas)
    cuentas = [c.cuentas for c in cartolas]
    assert all(len(x) == 1 for x in cuentas)
    assert len({n for x in cuentas for n in x}) == 2
    assert all(
        (cuenta.grupo, cuenta.producto_base, cuenta.portafolio) == ("Pershing", "CUENTA INVERSION", "")
        for x in cuentas
        for cuenta in x.values()
    )


def test_todas_las_cuadraturas_cierran(cartolas):
    total = 0
    for c in cartolas:
        controles = c.controles + validar(c)
        total += len(controles)
        malos = [x for x in controles if not x.ok]
        assert not malos, (Path(c.archivo).name, malos)
    assert total >= 200


def test_sin_avisos_de_lectura(cartolas):
    """Solo el aviso del RUT: ninguna sección, fila o transacción quedó sin leer."""
    assert Counter(a for c in cartolas for a in c.avisos) == {
        "El estado Pershing no trae RUT: RutCliente queda vacío": 6
    }


def test_continuidad_entre_meses(cartolas):
    meses = sorted((c for c in cartolas if c.archivo.startswith(str(CORREDORA))), key=lambda c: c.desde)
    assert len(meses) == 5 and len({n for c in meses for n in c.cuentas}) == 1
    for anterior, siguiente in zip(meses, meses[1:]):
        assert siguiente.desde == anterior.hasta + timedelta(days=1)
        nombre = Path(siguiente.archivo).name
        assert anterior.totales["valor_final"] == siguiente.totales["valor_inicial"], nombre
        # Los ingresos del año se acumulan mes a mes.
        assert anterior.totales["ingresos_anio"] + siguiente.totales["ingresos"] == siguiente.totales["ingresos_anio"]


def test_exporta_el_juego_de_archivos_pershing(tmp_path):
    # La carpeta de BICE trae solo el bono y el money market: las acciones
    # vienen en el estado de Sura.
    assert main([str(CORREDORA), str(_estados()[-1]), "--salida", str(tmp_path)]) == 0
    archivos = sorted(tmp_path.glob("*_PERSHING_20260831_V2.csv"))
    assert len(archivos) == 7

    def filas(tipo: str) -> int:
        archivo = tmp_path / f"{tipo}_PERSHING_20260831_V2.csv"
        codificacion = "utf-8" if tipo == "MOVIMIENTOS_PERSHING" else "cp1252"
        with open(archivo, encoding=codificacion, newline="") as f:
            return len(list(csv.reader(f, delimiter=";"))) - 1

    assert filas("MOVIMIENTOS_PERSHING") == 7
    assert filas("CUSTODIA_ACCIONES") == 12
    assert filas("SALDOS_CAJA") == 6
    assert filas("MOVIMIENTOS_DE_CAJA") == 0
    reporte = next(tmp_path.glob("REPORTE_*.md")).read_text(encoding="utf-8")
    assert "no cuadran" not in reporte
    assert reporte.count("la tabla Bonos no tiene archivo de destino") == 5
