"""Extractor de las cartolas Pershing (en construcción)."""

import pymupdf

FORMATO = "Pershing"


def paginas(doc: pymupdf.Document) -> list[int]:
    return []


def extraer(ruta, paginas=None):
    raise NotImplementedError(FORMATO)
