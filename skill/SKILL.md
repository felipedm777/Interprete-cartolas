---
name: interprete-cartolas
description: Lee cartolas PDF de inversiones (BICE, Valores Security, Larrainvial, Sura, Pershing) y las exporta a los archivos de saldos y movimientos con el formato del export de BICE.
---

# Intérprete de cartolas

**Estado:** lee las cartolas BICE nuevas (formato de septiembre de 2026). Los otros cinco formatos del inventario (`docs/inventario.md`) todavía no tienen extractor y quedan en el reporte como no reconocidos.

## Cómo usarla

Desde la carpeta `skill/`:

```
python -m cartolas <PDF o carpetas>... --salida <carpeta> [--solo-afi] [--codigo 10038] [--fecha AAAA-MM-DD]
```

- Escribe `SALDOS_CAJA`, `SALDOS_FFMM`, `CUSTODIA_ACCIONES`, `MOVIMIENTOS_DE_CAJA`, `MOVIMIENTOS_BOLSA`, `MOVIMIENTOS_FFMM` y `MOVIMIENTOS_PERSHING` como `<ARCHIVO>_<código>_<AAAAMMDD>_V2.csv`, y `REPORTE_<código>_<AAAAMMDD>.md`.
- El código sale del nombre de los PDF (`CARTOLA_<código>_...`) y la fecha es el último cierre de las cartolas, salvo que se indiquen.
- `--solo-afi` exporta solo los portafolios de AFI Trading.
- Termina con código 1 si alguna cartola no se pudo leer o tiene cuadraturas que no cierran.

Después de correrla, revisar el reporte: cada cartola con una cuadratura que no cierra debe mirarse contra el PDF antes de usar sus filas.

## Cómo funciona

1. `extractores.detectar` identifica el formato por el contenido del PDF, no por el nombre del archivo.
2. El extractor lee los textos con coordenadas (`pdf.py`), arma las tablas por los encabezados y devuelve una `Cartola` (`modelo.py`) con cuentas, caja, posiciones, movimientos y los totales impresos.
3. `validar.py` compara lo extraído con los totales de la cartola: sumas por cuenta, grupo y sección, caja, y cantidad × precio en cada posición y movimiento.
4. `salida.py` completa con la tabla maestra (`catalogo.py`, `datos/instrumentos.csv` y `datos/alias.csv`) el nemotécnico, emisor, producto y archivo de cada instrumento, y con el número de cuenta el producto base, el tipo de APV y el régimen.
5. `exportar.py` escribe los CSV con el formato exacto del export (`formato.py`, `docs/formato-salida.md`).

## Mantener la tabla maestra

`datos/instrumentos.csv` se regenera desde un export de BICE con `python -m cartolas.catalogo "<carpeta del export>"`. Los instrumentos que no están en la tabla salen sin nemotécnico ni emisor y con un aviso en el reporte. Si la cartola nombra un instrumento distinto que el export, se agrega una fila a `datos/alias.csv` con el nombre de la cartola, la moneda y el nemotécnico.
