"""Lectura de texto con coordenadas y armado de tablas sin líneas.

Las cartolas no traen tablas con bordes, así que las columnas se arman a
partir de los encabezados y cada valor se asigna por posición.
"""

from dataclasses import dataclass

import pymupdf


@dataclass(frozen=True)
class Span:
    texto: str
    x0: float
    y0: float
    x1: float
    y1: float
    tamano: float
    negrita: bool
    fuente: str

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass
class Columna:
    etiqueta: str
    x0: float
    x1: float
    y1: float


def leer_spans(pagina: pymupdf.Page) -> list[Span]:
    """Fragmentos de texto de la página en coordenadas visuales.

    Aplica la rotación de la página, así que en una página girada 90° las
    coordenadas quedan como se ve la página. Descarta texto vacío y blanco.
    """
    matriz = pagina.rotation_matrix
    spans = []
    for bloque in pagina.get_text("dict")["blocks"]:
        for linea in bloque.get("lines", []):
            for s in linea["spans"]:
                texto = s["text"].strip()
                if not texto or s.get("color") == 0xFFFFFF:
                    continue
                r = pymupdf.Rect(s["bbox"]) * matriz
                fuente = s["font"]
                negrita = bool(s["flags"] & 16) or "bold" in fuente.lower() or fuente.endswith("b")
                spans.append(
                    Span(texto, r.x0, r.y0, r.x1, r.y1, round(s["size"], 1), negrita, fuente)
                )
    return spans


def armar_columnas(encabezados: list[Span]) -> list[Columna]:
    """Agrupa los fragmentos de encabezado que se solapan en x en una columna.

    Las etiquetas de 2 líneas ("Número" / "cuenta") se unen de arriba abajo.
    """
    grupos: list[list[Span]] = []
    for s in sorted(encabezados, key=lambda s: s.x0):
        for g in grupos:
            x0 = min(p.x0 for p in g)
            x1 = max(p.x1 for p in g)
            if s.x0 < x1 + 1 and s.x1 > x0 - 1:
                g.append(s)
                break
        else:
            grupos.append([s])
    columnas = []
    for g in grupos:
        etiqueta = " ".join(p.texto for p in sorted(g, key=lambda p: p.y0))
        columnas.append(
            Columna(etiqueta, min(p.x0 for p in g), max(p.x1 for p in g), max(p.y1 for p in g))
        )
    return columnas


def columna_de(span: Span, columnas: list[Columna]) -> str:
    """Etiqueta de la columna con más solape horizontal; si no hay, la más cercana."""
    mejor, solape = None, 0.0
    for c in columnas:
        o = min(span.x1, c.x1) - max(span.x0, c.x0)
        if o > solape:
            mejor, solape = c, o
    if mejor is None:
        mejor = min(columnas, key=lambda c: abs((c.x0 + c.x1) / 2 - span.xc))
    return mejor.etiqueta
