"""Uso: python -m cartolas <PDF o carpeta>... --salida <carpeta> [opciones]

Lee las cartolas, valida sus cuadraturas y escribe los 7 archivos de saldos y
movimientos más un reporte con lo que no cuadró o no se pudo exportar.
"""

import argparse
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pymupdf

from .catalogo import Catalogo
from .exportar import escribir
from .extractores import detectar
from .formato import ARCHIVOS
from .modelo import Cartola
from .salida import Salida, generar
from .validar import validar


def _pdfs(rutas: list[str]) -> list[Path]:
    archivos = []
    for r in map(Path, rutas):
        if r.is_dir():
            archivos += sorted(p for p in r.rglob("*") if p.suffix.lower() == ".pdf")
        else:
            archivos.append(r)
    return archivos


def _codigo(archivos: list[Path]) -> str | None:
    """Código del asesor que BICE pone en el nombre: CARTOLA_<código>_<AAAAMM>_<rut>.pdf."""
    codigos = Counter(
        m.group(1) for a in archivos if (m := re.match(r"CARTOLA_(\d+)_\d{6}_", a.name))
    )
    return codigos.most_common(1)[0][0] if codigos else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cartolas", description=__doc__.splitlines()[2])
    parser.add_argument("entradas", nargs="+", help="PDF o carpetas con PDF")
    parser.add_argument("--salida", required=True, help="carpeta donde escribir los CSV y el reporte")
    parser.add_argument("--codigo", help="código para el nombre de los archivos (por defecto, el de los PDF)")
    parser.add_argument("--fecha", help="fecha para el nombre de los archivos, AAAA-MM-DD (por defecto, el último cierre)")
    parser.add_argument("--solo-afi", action="store_true", help="exportar solo los portafolios de AFI Trading")
    args = parser.parse_args(argv)

    archivos = _pdfs(args.entradas)
    if not archivos:
        parser.error("no se encontraron PDF")
    codigo = args.codigo or _codigo(archivos)
    if not codigo:
        parser.error("no se pudo deducir el código de los nombres de archivo; indícalo con --codigo")

    catalogo = Catalogo.cargar()
    total = Salida()
    resultados: list[tuple[Path, Cartola | None, Salida | None, str]] = []
    for ruta in archivos:
        try:
            doc = pymupdf.open(ruta)
            extractor = detectar(doc)
            if extractor is None:
                resultados.append((ruta, None, None, "formato no reconocido o todavía sin extractor"))
                continue
            cartola = extractor.extraer(ruta)
            cartola.controles = validar(cartola)
            salida = generar(cartola, catalogo, solo_afi=args.solo_afi)
            total.extender(salida)
            resultados.append((ruta, cartola, salida, ""))
        except Exception as e:  # un PDF problemático no detiene el resto
            resultados.append((ruta, None, None, f"error: {e}"))

    cartolas = [c for _, c, _, _ in resultados if c]
    fecha = args.fecha or (max(c.hasta for c in cartolas).isoformat() if cartolas else date.today().isoformat())
    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    for tipo, archivo in ARCHIVOS.items():
        escribir(archivo, total.filas.get(tipo, []), carpeta / archivo.nombre_archivo(codigo, fecha))
    reporte = carpeta / f"REPORTE_{codigo}_{fecha.replace('-', '')}.md"
    reporte.write_text(_reporte(resultados, total), encoding="utf-8")

    sin_cuadrar = sum(1 for _, c, _, _ in resultados if c and not all(x.ok for x in c.controles))
    fallidos = sum(1 for _, c, _, _ in resultados if c is None)
    print(f"{len(cartolas)} de {len(archivos)} cartolas procesadas; {sin_cuadrar} con cuadraturas que no cierran.")
    for tipo in ARCHIVOS:
        print(f"  {tipo}: {len(total.filas.get(tipo, []))} filas")
    print(f"Reporte: {reporte}")
    return 1 if sin_cuadrar or fallidos else 0


def _reporte(resultados, total: Salida) -> str:
    lineas = ["# Reporte de extracción", ""]
    lineas += ["| Archivo | Formato | Período | Cuadraturas | Posiciones | Mov. caja | Mov. títulos | Avisos |"]
    lineas += ["|---|---|---|---|---:|---:|---:|---:|"]
    for ruta, c, s, error in resultados:
        if c is None:
            lineas.append(f"| {ruta.name} | {error} | | | | | | |")
            continue
        malos = [x for x in c.controles if not x.ok]
        estado = "OK" if not malos else f"{len(malos)} no cuadran"
        avisos = len(c.avisos) + len(s.avisos)
        lineas.append(
            f"| {ruta.name} | {c.formato} | {c.desde:%d-%m-%Y} al {c.hasta:%d-%m-%Y} | "
            f"{estado} ({len(c.controles)}) | {len(c.posiciones)} | {len(c.movimientos_caja)} | "
            f"{len(c.movimientos_titulos)} | {avisos} |"
        )
    lineas += ["", "## Filas exportadas", ""]
    for tipo in ARCHIVOS:
        lineas.append(f"- {tipo}: {len(total.filas.get(tipo, []))}")
    for ruta, c, s, _ in resultados:
        if c is None:
            continue
        malos = [x for x in c.controles if not x.ok]
        if not (malos or c.avisos or s.avisos or s.omitidos):
            continue
        lineas += ["", f"## {ruta.name}", ""]
        for x in malos:
            lineas.append(f"- **No cuadra:** {x.regla}. {x.detalle}")
        for a in c.avisos + s.avisos:
            lineas.append(f"- Aviso: {a}")
        for o in s.omitidos:
            lineas.append(f"- No exportado: {o}")
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    sys.exit(main())
