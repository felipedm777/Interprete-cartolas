"""Uso: python -m cartolas <PDF o carpeta>... --salida <carpeta> [opciones]

Lee las cartolas, valida sus cuadraturas y escribe los 7 archivos de saldos y
movimientos de cada institución más un reporte con lo que no cuadró o no se
pudo exportar.
"""

import argparse
import hashlib
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pymupdf

from . import dividendos
from .catalogo import Catalogo
from .exportar import escribir
from .extractores import detectar
from .formato import ARCHIVOS
from .modelo import Cartola
from .numeros import leer_monto
from .salida import Salida, generar
from .validar import validar


@dataclass
class Resultado:
    ruta: Path
    cartola: Cartola | None = None
    salida: Salida | None = None
    # Motivo por el que el archivo (o una de sus partes) no se procesó.
    error: str = ""
    # Duplicado de otro archivo: no se procesa, pero tampoco es un error.
    duplicado: bool = False


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


def _huella(doc: pymupdf.Document) -> str:
    """Hash del texto: dos PDF con el mismo contenido pueden diferir en los bytes."""
    texto = "\f".join(p.get_text() for p in doc)
    return hashlib.sha256(re.sub(r"\s+", " ", texto).encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cartolas", description=__doc__.splitlines()[2])
    parser.add_argument("entradas", nargs="+", help="PDF o carpetas con PDF")
    parser.add_argument("--salida", required=True, help="carpeta donde escribir los CSV y el reporte")
    parser.add_argument(
        "--codigo",
        help="código para el nombre de los archivos BICE (por defecto, el de los PDF o BICE)",
    )
    parser.add_argument("--fecha", help="fecha para el nombre de los archivos, AAAA-MM-DD (por defecto, el último cierre)")
    parser.add_argument("--solo-afi", action="store_true", help="exportar solo los portafolios de AFI Trading")
    parser.add_argument(
        "--tipo-cambio-eur",
        help="tipo de cambio del euro al último cierre (p. ej. 1102,72109), para las cartolas que no lo "
        "traen; por defecto se toma de otra cartola con el mismo cierre",
    )
    args = parser.parse_args(argv)

    archivos = _pdfs(args.entradas)
    if not archivos:
        parser.error("no se encontraron PDF")
    codigo = args.codigo or _codigo(archivos) or "BICE"

    resultados = _extraer(archivos)
    _preferir_definitivas(resultados)
    cartolas = [r.cartola for r in resultados if r.cartola]
    _completar_tipo_cambio(resultados)
    _completar_euro(resultados, leer_monto(args.tipo_cambio_eur) if args.tipo_cambio_eur else None)
    catalogo = Catalogo.cargar()
    dividendos.inferir(cartolas, catalogo)
    for r in resultados:
        if r.cartola:
            r.cartola.controles += validar(r.cartola)
            r.salida = generar(r.cartola, catalogo, solo_afi=args.solo_afi)

    # Un juego de archivos por institución; BICE con el código del asesor.
    juegos: dict[str, list[Resultado]] = defaultdict(list)
    for r in resultados:
        if r.cartola:
            juegos[codigo if r.cartola.institucion == "BICE" else r.cartola.institucion].append(r)
    carpeta = Path(args.salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    resumen = []
    for nombre, parte in juegos.items():
        fecha = args.fecha or max(r.cartola.hasta for r in parte).isoformat()
        total = Salida()
        for r in parte:
            total.extender(r.salida)
        for tipo, archivo in ARCHIVOS.items():
            escribir(archivo, total.filas.get(tipo, []), carpeta / archivo.nombre_archivo(nombre, fecha))
        resumen.append((nombre, fecha, total))

    fecha_reporte = args.fecha or (
        max(c.hasta for c in cartolas).isoformat() if cartolas else date.today().isoformat()
    )
    nombres = "_".join(n for n, _, _ in resumen) or codigo
    reporte = carpeta / f"REPORTE_{nombres}_{fecha_reporte.replace('-', '')}.md"
    reporte.write_text(_reporte(resultados, resumen), encoding="utf-8")

    sin_cuadrar = sum(1 for c in cartolas if not all(x.ok for x in c.controles))
    fallidos = sum(1 for r in resultados if r.error and not r.duplicado)
    duplicados = sum(1 for r in resultados if r.duplicado)
    print(
        f"{len(cartolas)} cartolas en {len(archivos)} PDF ({duplicados} duplicados); "
        f"{sin_cuadrar} con cuadraturas que no cierran; {fallidos} no se pudieron leer."
    )
    for nombre, fecha, total in resumen:
        filas = ", ".join(f"{tipo} {len(total.filas.get(tipo, []))}" for tipo in ARCHIVOS)
        print(f"  {nombre} al {fecha}: {filas}")
    print(f"Reporte: {reporte}")
    return 1 if sin_cuadrar or fallidos else 0


def _extraer(archivos: list[Path]) -> list[Resultado]:
    resultados: list[Resultado] = []
    vistos: dict[str, Path] = {}
    for ruta in archivos:
        try:
            doc = pymupdf.open(ruta)
            huella = _huella(doc)
            if huella in vistos:
                resultados.append(
                    Resultado(ruta, error=f"duplicado: mismo contenido que {vistos[huella].name}", duplicado=True)
                )
                continue
            vistos[huella] = ruta
            partes = detectar(doc)
        except Exception as e:  # un PDF problemático no detiene el resto
            resultados.append(Resultado(ruta, error=f"error: {e}"))
            continue
        if not partes:
            resultados.append(Resultado(ruta, error="formato no reconocido o todavía sin extractor"))
        for extractor, paginas in partes:
            try:
                resultados.append(Resultado(ruta, extractor.extraer(ruta, paginas)))
            except Exception as e:
                resultados.append(Resultado(ruta, error=f"{extractor.FORMATO}: error: {e}"))
    return resultados


def _preferir_definitivas(resultados: list[Resultado]) -> None:
    """Si llega un informe provisorio y la cartola definitiva del mismo cliente y
    período, se deja solo la definitiva. Otras repeticiones quedan con aviso."""
    grupos: dict[tuple, list[Resultado]] = defaultdict(list)
    for r in resultados:
        c = r.cartola
        if c and c.rut:
            grupos[(c.institucion, c.rut, c.desde, c.hasta)].append(r)
    for grupo in grupos.values():
        if len(grupo) < 2:
            continue
        definitivas = [r for r in grupo if not r.cartola.provisoria]
        for r in grupo:
            if definitivas and r.cartola.provisoria:
                r.error = f"informe provisorio reemplazado por la cartola definitiva {definitivas[0].ruta.name}"
                r.cartola, r.duplicado = None, True
        quedan = [r for r in grupo if r.cartola]
        if len(quedan) > 1:
            for r in quedan:
                otros = ", ".join(o.ruta.name for o in quedan if o is not r)
                r.cartola.avisos.append(f"Hay otra cartola del mismo cliente y período ({otros}): revisar si está repetida")


def _completar_tipo_cambio(resultados: list[Resultado]) -> None:
    """Las cartolas BICE antiguas no traen tipo de cambio: se usa el de otra
    cartola con el mismo cierre, de preferencia del mismo PDF."""
    con_tc = [r for r in resultados if r.cartola and r.cartola.tipo_cambio_usd]
    for r in resultados:
        c = r.cartola
        if c is None or c.tipo_cambio_usd:
            continue
        candidatos = [o for o in con_tc if o.cartola.hasta == c.hasta]
        mismo_pdf = [o for o in candidatos if o.ruta == r.ruta]
        if mismo_pdf:
            fuente = mismo_pdf[0].cartola
            c.tipo_cambio_usd = fuente.tipo_cambio_usd
            c.avisos.append(
                f"La cartola no trae tipo de cambio: se usó el USD {fuente.tipo_cambio_usd} "
                f"de la cartola {fuente.formato} del mismo PDF"
            )
        elif candidatos:
            valor, _ = Counter(o.cartola.tipo_cambio_usd for o in candidatos).most_common(1)[0]
            c.tipo_cambio_usd = valor
            c.avisos.append(
                f"La cartola no trae tipo de cambio: se usó el USD {valor} de otras cartolas "
                f"con cierre {c.hasta:%d-%m-%Y}"
            )
        elif _tiene_dolares(c):
            c.avisos.append(
                "La cartola no trae tipo de cambio y no hay otra con el mismo cierre: "
                "los equivalentes en pesos de lo que está en USD quedan vacíos"
            )


def _completar_euro(resultados: list[Resultado], indicado: Decimal | None) -> None:
    """Las cartolas BICE no traen el tipo de cambio del euro, que el export pone
    en todas las filas de saldos: se usa el de otra cartola con el mismo cierre
    (Security y Larrainvial lo traen) o, en las del último cierre, el indicado."""
    cartolas = [r.cartola for r in resultados if r.cartola]
    ultimo = max((c.hasta for c in cartolas), default=None)
    for c in cartolas:
        if c.tipo_cambio_eur:
            continue
        otros = Counter(o.tipo_cambio_eur for o in cartolas if o.tipo_cambio_eur and o.hasta == c.hasta)
        if otros:
            c.tipo_cambio_eur = otros.most_common(1)[0][0]
            c.avisos.append(
                f"La cartola no trae el tipo de cambio del euro: se usó {c.tipo_cambio_eur} de otras "
                f"cartolas con cierre {c.hasta:%d-%m-%Y}"
            )
        elif indicado and c.hasta == ultimo:
            c.tipo_cambio_eur = indicado


def _tiene_dolares(c: Cartola) -> bool:
    return any(
        x.moneda == "USD"
        for x in [*c.saldos_caja, *c.posiciones, *c.movimientos_caja, *c.movimientos_titulos]
    )


def _reporte(resultados: list[Resultado], resumen: list[tuple[str, str, Salida]]) -> str:
    lineas = ["# Reporte de extracción", ""]
    lineas += [
        "| Archivo | Formato | Período | Cuadraturas | Posiciones | Mov. caja | Mov. títulos | Avisos |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for r in resultados:
        c, s = r.cartola, r.salida
        if c is None:
            lineas.append(f"| {r.ruta.name} | {r.error} | | | | | | |")
            continue
        malos = [x for x in c.controles if not x.ok]
        estado = "OK" if not malos else f"{len(malos)} no cuadran"
        lineas.append(
            f"| {r.ruta.name} | {c.formato} | {c.desde:%d-%m-%Y} al {c.hasta:%d-%m-%Y} | "
            f"{estado} ({len(c.controles)}) | {len(c.posiciones)} | {len(c.movimientos_caja)} | "
            f"{len(c.movimientos_titulos)} | {len(c.avisos) + len(s.avisos)} |"
        )
    lineas += ["", "## Filas exportadas", ""]
    for nombre, fecha, total in resumen:
        lineas.append(f"- **{nombre}** al {fecha}:")
        for tipo in ARCHIVOS:
            lineas.append(f"  - {tipo}: {len(total.filas.get(tipo, []))}")
    for r in resultados:
        c, s = r.cartola, r.salida
        if c is None:
            continue
        malos = [x for x in c.controles if not x.ok]
        if not (malos or c.avisos or s.avisos or s.omitidos):
            continue
        lineas += ["", f"## {r.ruta.name} ({c.formato})", ""]
        for x in malos:
            lineas.append(f"- **No cuadra:** {x.regla}. {x.detalle}")
        lineas += _sin_repetir("Aviso", c.avisos + s.avisos)
        lineas += _sin_repetir("No exportado", s.omitidos)
    return "\n".join(lineas) + "\n"


def _sin_repetir(prefijo: str, textos: list[str]) -> list[str]:
    return [f"- {prefijo}: {t}" + (f" (×{n})" if n > 1 else "") for t, n in Counter(textos).items()]


if __name__ == "__main__":
    sys.exit(main())
