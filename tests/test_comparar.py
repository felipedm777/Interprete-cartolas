"""Comparación de la salida con un export, sobre archivos inventados."""

from decimal import Decimal as D

from cartolas.comparar import main
from cartolas.exportar import escribir
from cartolas.formato import CUSTODIA_ACCIONES, MOVIMIENTOS_BOLSA, SALDOS_CAJA


def _caja(rut, cuenta, moneda, monto, fecha="2026-09-30"):
    return {
        "FechaProceso": fecha,
        "RutCliente": rut,
        "Cuenta": cuenta,
        "Producto": "CUENTAS CAJA",
        "MonedaValoracionPatrimonio": moneda,
        "PatrimonioEnMonedaValoracion": D(monto),
    }


def _accion(rut, nombre, cantidad, fecha="2026-09-30"):
    return {
        "FechaProceso": fecha,
        "RutCliente": rut,
        "Cuenta": "0",
        "Instrumento": nombre,
        "Cantidad": D(cantidad),
        "TipoCambioUSD": D("950.123456789"),
    }


def _compra(rut, nombre, fecha):
    return {
        "FechaProceso": fecha,
        "RutCliente": rut,
        "Cuenta": "0",
        "Instrumento": nombre,
        "NombreTipoMovimiento": "COMPRA RV",
        "Cantidad": D(10),
    }


def _escribir(carpeta, fecha, caja, acciones, compras):
    carpeta.mkdir()
    for archivo, filas in ((SALDOS_CAJA, caja), (CUSTODIA_ACCIONES, acciones), (MOVIMIENTOS_BOLSA, compras)):
        escribir(archivo, filas, carpeta / archivo.nombre_archivo("10038", fecha))


def test_coincide(tmp_path):
    filas = ([_caja("1-9", "0", "CLP", "1000")], [_accion("1-9", "ACCION X", "5")], [])
    _escribir(tmp_path / "export", "2026-09-30", *filas)
    _escribir(tmp_path / "salida", "2026-09-30", *filas)
    assert main([str(tmp_path / "export"), str(tmp_path / "salida")]) == 0
    assert (tmp_path / "salida" / "COMPARACION_10038.md").exists()


def test_diferencias(tmp_path):
    _escribir(
        tmp_path / "export",
        "2026-09-30",
        # Otro cliente del asesor que no está en la salida: no cuenta.
        [_caja("1-9", "0", "CLP", "1000"), _caja("1-9", "0", "USD", "3"), _caja("2-7", "0", "CLP", "5")],
        [_accion("1-9", "ACCION  X", "5"), _accion("1-9", "ACCION Y", "7")],
        [_compra("1-9", "ACCION Y", "2026-09-30")],
    )
    _escribir(
        tmp_path / "salida",
        "2026-09-30",
        [_caja("1-9", "0", "CLP", "1000.0000004")],  # dentro de la tolerancia
        [_accion("1-9", "Accion X", "6"), _accion("1-9", "ACCION Z", "1")],
        # Del mes completo: solo cuenta la fecha del export.
        [_compra("1-9", "ACCION Y", "2026-09-30"), _compra("1-9", "ACCION Y", "2026-09-12")],
    )
    reporte = tmp_path / "r.md"
    assert main([str(tmp_path / "export"), str(tmp_path / "salida"), "--reporte", str(reporte)]) == 1
    texto = reporte.read_text(encoding="utf-8")
    assert "| SALDOS_CAJA | 2 | 1 | 1 | 1 | 0 | ninguna |" in texto
    assert "| CUSTODIA_ACCIONES | 2 | 2 | 1 | 1 | 1 | Cantidad (1) |" in texto
    assert "| MOVIMIENTOS_BOLSA | 1 | 1 | 1 | 0 | 0 | ninguna |" in texto
    assert "1-9 / 0 / Accion X: '6,000000' ≠ '5,000000'" in texto
    assert "2-7" not in texto


def test_saldos_de_otro_cierre(tmp_path):
    _escribir(tmp_path / "export", "2026-09-22", [_caja("1-9", "0", "CLP", "1000", "2026-09-22")], [], [])
    _escribir(
        tmp_path / "salida",
        "2026-09-30",
        [_caja("1-9", "0", "CLP", "1000"), _caja("1-9", "0", "CLP", "900", "2026-08-31")],
        [],
        [],
    )
    argumentos = [str(tmp_path / "export"), str(tmp_path / "salida"), "--reporte", str(tmp_path / "r.md")]
    assert main(argumentos + ["--fecha-saldos", "2026-09-30"]) == 0
    # Sin indicar el cierre, no hay saldos de la salida en la fecha del export.
    assert main(argumentos) == 1
