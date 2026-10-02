---
name: interprete-cartolas
description: Lee cartolas PDF de inversiones (BICE, Valores Security, Larrainvial, Sura, Pershing) y las exporta a los archivos de saldos y movimientos con el formato del export de BICE.
---

# Intérprete de cartolas

**Estado: en construcción.** Por ahora solo está implementado el formato de salida (`cartolas/formato.py` y `cartolas/exportar.py`). Los extractores por institución se agregan a partir del inventario en `docs/inventario.md`.

## Flujo previsto

1. Identificar el formato de cada PDF por su contenido (no por el nombre del archivo) y separar las cartolas que vienen pegadas en un mismo PDF, como BICE antigua + Valores Security.
2. Extraer encabezado, saldos y movimientos leyendo palabras con coordenadas.
3. Validar las cuadraturas del formato (totales impresos, cuotas × valor cuota, saldos encadenados) y marcar el archivo si alguna no cuadra.
4. Completar con las tablas maestras los datos que la cartola no trae: nemotécnico, emisor, RUT, cuenta y portafolio.
5. Escribir `SALDOS_CAJA`, `SALDOS_FFMM`, `CUSTODIA_ACCIONES`, `MOVIMIENTOS_DE_CAJA`, `MOVIMIENTOS_BOLSA`, `MOVIMIENTOS_FFMM` y `MOVIMIENTOS_PERSHING`, y un reporte con lo que no se pudo extraer o no cuadró.
