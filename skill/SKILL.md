---
name: interprete-cartolas
description: Lee cartolas PDF de inversiones (BICE, Valores Security, Larrainvial, Sura, Pershing) y las exporta a los archivos de saldos y movimientos con el formato del export de BICE.
---

# Intérprete de cartolas

**Estado:** lee las cartolas BICE nuevas (desde septiembre de 2026), las BICE antiguas, la cartola Valores Security que viene pegada a ellas, los informes Larrainvial, las cartolas mensuales Sura y los estados Pershing (`docs/inventario.md`). Sura y Pershing no traen RUT: esas filas salen con `RutCliente` vacío para completarlo después.

## Cómo usarla

Desde la carpeta `skill/`:

```
python -m cartolas <PDF o carpetas>... --salida <carpeta> [--solo-afi] [--codigo 10038] [--fecha AAAA-MM-DD]
```

- Escribe un juego de 7 archivos por institución: `SALDOS_CAJA`, `SALDOS_FFMM`, `CUSTODIA_ACCIONES`, `MOVIMIENTOS_DE_CAJA`, `MOVIMIENTOS_BOLSA`, `MOVIMIENTOS_FFMM` y `MOVIMIENTOS_PERSHING`. Los de BICE se llaman `<ARCHIVO>_<código>_<AAAAMMDD>_V2.csv` y los de otras instituciones `<ARCHIVO>_<INSTITUCIÓN>_<AAAAMMDD>_V2.csv` (p. ej. `SALDOS_CAJA_SECURITY_20260430_V2.csv`). Además deja un `REPORTE_<juegos>_<AAAAMMDD>.md`.
- El código sale del nombre de los PDF (`CARTOLA_<código>_...`; si no lo trae, `BICE`) y la fecha de cada juego es el último cierre de sus cartolas, salvo que se indiquen.
- Un PDF puede traer dos cartolas (BICE antigua + Security): cada una sale en el juego de su institución. Los PDF con el mismo contenido se procesan una sola vez.
- Si una cartola no trae tipo de cambio (BICE antigua, Pershing, Sura sin filas en USD), se usa el de otra con el mismo cierre, de preferencia del mismo PDF, y queda anotado en el reporte.
- Si llegan el informe provisorio y la cartola definitiva de un mismo cliente y período (Larrainvial), se usa la definitiva.
- `--solo-afi` exporta solo los portafolios de AFI Trading (solo BICE nueva trae el portafolio).
- Termina con código 1 si algún PDF no se pudo leer o alguna cartola tiene cuadraturas que no cierran.

Después de correrla, revisar el reporte: cada cartola con una cuadratura que no cierra debe mirarse contra el PDF antes de usar sus filas.

Si hay un export de BICE del mismo día (o los exports diarios del mes), `python -m cartolas.comparar <carpeta del export> <carpeta de salida>` compara fila por fila los clientes de la salida y deja `COMPARACION_<código>.md` con las columnas que difieren y las filas que están en uno solo.

## Cómo funciona

1. `extractores.detectar` identifica por el contenido, no por el nombre del archivo, qué cartolas trae el PDF y en qué páginas.
2. El extractor lee los textos con coordenadas (`pdf.py`), arma las tablas por los encabezados y devuelve una `Cartola` (`modelo.py`) con cuentas, caja, posiciones, movimientos y los totales impresos.
3. Cada extractor deja sus cuadraturas contra los totales impresos, y `validar.py` agrega las comunes: cantidad × precio en cada posición y movimiento, y las sumas por cuenta y sección cuando la cartola las trae.
4. `salida.py` completa con la tabla maestra (`catalogo.py`, `datos/instrumentos.csv` y `datos/alias.csv`) el nemotécnico, emisor, producto y archivo de cada instrumento, y con el número de cuenta el producto base, el tipo de APV y el régimen (las cartolas que no son de BICE los traen en la cuenta).
5. `exportar.py` escribe los CSV con el formato exacto del export (`formato.py`, `docs/formato-salida.md`).

## Mantener la tabla maestra

`datos/instrumentos.csv` se regenera desde un export de BICE con `python -m cartolas.catalogo "<carpeta del export>"`. Los instrumentos que no están en la tabla salen sin nemotécnico ni emisor y con un aviso en el reporte. Si la cartola nombra un instrumento distinto que el export, se agrega una fila a `datos/alias.csv` con el nombre de la cartola, la moneda y el nemotécnico.
