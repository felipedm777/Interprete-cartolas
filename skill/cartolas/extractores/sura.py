"""Extractor de las cartolas Sura (en construcción)."""

import pymupdf

FORMATO = "Sura"


def paginas(doc: pymupdf.Document) -> list[int]:
    return []


def extraer(ruta, paginas=None):
    raise NotImplementedError(FORMATO)
