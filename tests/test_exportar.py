import csv
from decimal import Decimal
from pathlib import Path

import pytest

from cartolas.exportar import escribir
from cartolas.formato import ARCHIVOS, SALDOS_CAJA

# Copias anonimizadas del export de ejemplo. No están en el repositorio: la
# prueba de ida y vuelta corre solo donde existe esta carpeta.
EJEMPLO = Path("/mnt/project-files/datos/anonimizado/Example Export")


def test_encabezado_y_fin_de_linea(tmp_path):
    ruta = tmp_path / "s.csv"
    escribir(
        SALDOS_CAJA,
        [{"FechaProceso": "2026-09-22", "PatrimonioEnMonedaValoracion": Decimal("1234")}],
        ruta,
    )
    contenido = ruta.read_bytes()
    lineas = contenido.split(b"\r\n")
    assert lineas[0].decode() == ";".join(SALDOS_CAJA.encabezados)
    assert lineas[1].startswith(b"2026-09-22;;;;;;;1234,000000;")
    assert contenido.endswith(b"\r\n") and b"\n" not in contenido.replace(b"\r\n", b"")


def test_columna_desconocida(tmp_path):
    with pytest.raises(KeyError):
        escribir(SALDOS_CAJA, [{"Inventada": 1}], tmp_path / "s.csv")


def test_nombre_archivo():
    assert SALDOS_CAJA.nombre_archivo("10038", "2026-09-22") == "SALDOS_CAJA_10038_20260922_V2.csv"


@pytest.mark.skipif(not EJEMPLO.exists(), reason="sin el export de ejemplo anonimizado")
@pytest.mark.parametrize("tipo", sorted(ARCHIVOS))
def test_reproduce_el_export_de_ejemplo(tipo, tmp_path):
    """Leer el ejemplo y volver a escribirlo debe dar exactamente los mismos bytes."""
    archivo = ARCHIVOS[tipo]
    (original,) = EJEMPLO.glob(f"{tipo}_*.csv")
    with open(original, encoding=archivo.codificacion, newline="") as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    numericas = {c.nombre for c in archivo.columnas if c.decimales is not None}
    for fila in filas:
        for nombre in numericas:
            if fila[nombre]:
                fila[nombre] = Decimal(fila[nombre].replace(",", "."))
    salida = tmp_path / original.name
    escribir(archivo, filas, salida)
    assert salida.read_bytes() == original.read_bytes()
