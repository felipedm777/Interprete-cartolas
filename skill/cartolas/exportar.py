"""Escritura de los archivos de saldos y movimientos."""

from collections.abc import Iterable, Mapping
from pathlib import Path

from .formato import Archivo
from .numeros import escribir_numero


def escribir(archivo: Archivo, filas: Iterable[Mapping[str, object]], ruta: Path) -> None:
    """Escribe ``filas`` (diccionarios por nombre de columna) en ``ruta``.

    Las columnas que falten en una fila quedan vacías; una clave que no sea
    columna del archivo es un error, para no perder datos en silencio.
    """
    nombres = set(archivo.encabezados)
    lineas = [";".join(archivo.encabezados)]
    for fila in filas:
        sobrantes = set(fila) - nombres
        if sobrantes:
            raise KeyError(f"{archivo.tipo} no tiene las columnas {sorted(sobrantes)}")
        celdas = []
        for col in archivo.columnas:
            valor = fila.get(col.nombre)
            if col.decimales is None:
                celdas.append("" if valor is None else str(valor))
            else:
                celdas.append(escribir_numero(valor, col.decimales))
        lineas.append(";".join(celdas))
    with open(ruta, "w", encoding=archivo.codificacion, newline="") as f:
        f.write("\r\n".join(lineas) + "\r\n")
