"""Un extractor por formato de cartola.

Formatos identificados en docs/inventario.md: BICE nueva, BICE antigua,
Valores Security / AGF Security, Larrainvial, Sura y Pershing. Cada módulo
expone ``FORMATO``, ``reconoce(doc)`` y ``extraer(ruta)``.
"""

import pymupdf

from . import bice_nueva

EXTRACTORES = (bice_nueva,)


def detectar(doc: pymupdf.Document):
    """Extractor que reconoce el documento por su contenido, o None."""
    for extractor in EXTRACTORES:
        if extractor.reconoce(doc):
            return extractor
    return None
