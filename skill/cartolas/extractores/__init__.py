"""Un extractor por formato de cartola.

Formatos identificados en docs/inventario.md: BICE nueva, BICE antigua,
Valores Security / AGF Security, Larrainvial, Sura y Pershing. Cada módulo
expone:

- ``FORMATO``: nombre del formato para el reporte.
- ``paginas(doc)``: índices de las páginas del PDF que son de ese formato
  (lista vacía si no hay ninguna). Un PDF puede traer más de una cartola: las
  BICE antiguas traen pegada una cartola Security del mismo cliente.
- ``extraer(ruta, paginas)``: la ``Cartola`` de esas páginas, con sus
  cuadraturas propias en ``controles``. ``validar.validar`` agrega las comunes.
"""

import pymupdf

from . import bice_antigua, bice_nueva, security

EXTRACTORES = (bice_nueva, bice_antigua, security)


def detectar(doc: pymupdf.Document) -> list[tuple[object, list[int]]]:
    """(extractor, páginas) de cada cartola que trae el documento."""
    partes = []
    for extractor in EXTRACTORES:
        paginas = extractor.paginas(doc)
        if paginas:
            partes.append((extractor, paginas))
    return partes
