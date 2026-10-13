---
name: interprete-cartolas
description: Lee cartolas PDF de inversiones (BICE, Valores Security, Larrainvial, Sura, Pershing) y las exporta a los archivos de saldos y movimientos con el formato del export de BICE.
---

# Intérprete de cartolas

**Estado:** lee las cartolas BICE nuevas (desde septiembre de 2026), las BICE antiguas, la cartola Valores Security que viene pegada a ellas, los informes Larrainvial, las cartolas mensuales Sura y los estados Pershing (`docs/inventario.md`). Sura y Pershing no traen RUT: esas filas salen con `RutCliente` vacío para completarlo después.

## Cómo usarla

Desde la carpeta de esta skill (la que contiene `cartolas/`; en el repositorio, `skill/`), con Python y `pymupdf`:

```
python -m cartolas <PDF o carpetas>... --salida <carpeta> [--solo-afi] [--codigo 10038] [--fecha AAAA-MM-DD] [--tipo-cambio-eur 1102,72109] [--eventos-capital <tabla.csv>] [--bolsa <tabla.csv o Excel>]
```

- Escribe un juego de 7 archivos por institución: `SALDOS_CAJA`, `SALDOS_FFMM`, `CUSTODIA_ACCIONES`, `MOVIMIENTOS_DE_CAJA`, `MOVIMIENTOS_BOLSA`, `MOVIMIENTOS_FFMM` y `MOVIMIENTOS_PERSHING`. Los de BICE se llaman `<ARCHIVO>_<código>_<AAAAMMDD>_V2.csv` y los de otras instituciones `<ARCHIVO>_<INSTITUCIÓN>_<AAAAMMDD>_V2.csv` (p. ej. `SALDOS_CAJA_SECURITY_20260430_V2.csv`). Además deja un `REPORTE_<juegos>_<AAAAMMDD>.md`.
- El código sale del nombre de los PDF (`CARTOLA_<código>_...`; si no lo trae, `BICE`) y la fecha de cada juego es el último cierre de sus cartolas, salvo que se indiquen.
- Un PDF puede traer dos cartolas (BICE antigua + Security): cada una sale en el juego de su institución. Los PDF con el mismo contenido se procesan una sola vez.
- Si una cartola no trae tipo de cambio (BICE antigua, Pershing, Sura sin filas en USD), se usa el de otra con el mismo cierre, de preferencia del mismo PDF, y queda anotado en el reporte.
- Las cartolas BICE no traen el tipo de cambio del euro, que el export pone en todos los saldos: se toma de otra cartola con el mismo cierre (Security y Larrainvial lo traen) o de `--tipo-cambio-eur`, que vale para las cartolas del último cierre.
- Los dividendos y repartos de la cartola BICE nueva no dicen de qué instrumento son: si el monto por cuota cuadra con el de otro cliente el mismo día, o si la cuenta tiene una sola posición que pueda pagarlos, van con el nemotécnico y producto de ese instrumento, como en el export. Conviene correr juntas todas las cartolas del mes.
- Los abonos por eventos de capital (dividendos, repartos y disminuciones de capital) se comprueban además contra los que publican la Bolsa de Santiago (`datos/eventos_bolsa_<AAAAMMDD>.csv`, acciones, fondos y emisores extranjeros) y DataFondos (`datos/eventos_capital.csv`, fondos): eso identifica el instrumento de los abonos que no lo traen y distingue un dividendo de una devolución de capital. Lo que las tablas no explican queda como caja, con su causa en el reporte, nunca con un instrumento supuesto. Seguir "Eventos de capital con la Bolsa y DataFondos" en cada corrida. `--bolsa <archivo>` usa otra tabla de la Bolsa (o un Excel de la Bolsa) y `--bolsa no` no la usa; `--eventos-capital <archivo.csv>` usa otra tabla de DataFondos y `--eventos-capital no` no usa ninguna de las dos.
- Si llegan el informe provisorio y la cartola definitiva de un mismo cliente y período (Larrainvial), se usa la definitiva.
- `--solo-afi` exporta solo los portafolios de AFI Trading (solo BICE nueva trae el portafolio).
- Termina con código 1 si algún PDF no se pudo leer o alguna cartola tiene cuadraturas que no cierran.

Después de correrla, revisar el reporte: cada cartola con una cuadratura que no cierra debe mirarse contra el PDF antes de usar sus filas.

Si hay un export de BICE del mismo día (o los exports diarios del mes), `python -m cartolas.comparar <carpeta del export> <carpeta de salida>` compara fila por fila los clientes de la salida y deja `COMPARACION_<código>.md` con las columnas que difieren y las filas que están en uno solo.

## Cómo funciona

1. `extractores.detectar` identifica por el contenido, no por el nombre del archivo, qué cartolas trae el PDF y en qué páginas.
2. El extractor lee los textos con coordenadas (`pdf.py`), arma las tablas por los encabezados y devuelve una `Cartola` (`modelo.py`) con cuentas, caja, posiciones, movimientos y los totales impresos.
3. Cada extractor deja sus cuadraturas contra los totales impresos, y `validar.py` agrega las comunes: cantidad × precio en cada posición y movimiento, y las sumas por cuenta y sección cuando la cartola las trae.
4. `dividendos.py` y `eventos_capital.py` completan de qué instrumento es cada dividendo o reparto que la cartola no identifica: el primero comparando el monto por cuota entre clientes, el segundo contra los repartos que publican la Bolsa (`bolsa.py`) y DataFondos.
5. `salida.py` completa con la tabla maestra (`catalogo.py`, `datos/instrumentos.csv` y `datos/alias.csv`) el nemotécnico, emisor, producto y archivo de cada instrumento, y con el número de cuenta el producto base, el tipo de APV y el régimen (las cartolas que no son de BICE los traen en la cuenta).
6. `exportar.py` escribe los CSV con el formato exacto del export (`formato.py`, `docs/formato-salida.md`).

## Eventos de capital con la Bolsa y DataFondos

Hacerlo en cada corrida. A la Bolsa no se le envía nada; a DataFondos solo el RUT y el nemotécnico de fondos, nunca nombres, RUT ni montos de clientes. Lo que devuelven son datos públicos de instrumentos.

1. **Antes de correr la skill**, desde la carpeta de la skill, bajar el Excel de dividendos y repartos más reciente de la Bolsa: `python -m cartolas.bolsa --carpeta <carpeta de salida>/bolsa`. Necesita internet y `openpyxl` (`pip install openpyxl`). Escribe `datos/eventos_bolsa_<AAAAMMDD>.csv` con la fecha del Excel y borra la anterior. Revisar que la última línea diga que los eventos "cuadran con el Excel" y mirar las filas descartadas y los dudosos que informa por hoja. Si no hay internet, se puede pasar un Excel ya bajado: `python -m cartolas.bolsa <archivo.xlsx>`.
2. Si el MCP de DataFondos está conectado, llamar `resumen_dividendos`, guardar la respuesta completa en `<carpeta de salida>/datafondos/resumen.json` y agregarla con `python -m cartolas.eventos_capital <carpeta de salida>/datafondos/resumen.json`. Eso actualiza `datos/datafondos_cobertura.csv`: qué fondos sigue DataFondos y hasta cuándo tiene sus repartos.
3. Correr la skill.
4. Si el reporte trae la tabla "Fondos por consultar en DataFondos", llamar `dividendos` con el RUT y el nemotécnico de cada fila, guardar cada respuesta en `<carpeta de salida>/datafondos/<nemotécnico>.json` y agregarlas todas con `python -m cartolas.eventos_capital <carpeta de salida>/datafondos/*.json --desde <1 de enero del año anterior>`. Volver a correr la skill. Repetir hasta que el reporte no pida más fondos o DataFondos no traiga nada nuevo. Con la tabla de la Bolsa al día, solo quedan por consultar los fondos que la Bolsa no publica.
5. Informar por institución, desde la sección "Eventos de capital" del reporte, los abonos confirmados, identificados, por revisar, sin comprobar y dudosos por causa.

Sin internet ni el MCP, la skill usa las tablas que trae y el informe dice qué falta actualizar o consultar.

Qué significa cada causa de un abono dudoso (todos quedan como caja):

| Causa | Qué hacer |
|---|---|
| Falta bajar el Excel de la Bolsa al día | El abono es posterior al Excel de la tabla, o no hay tabla de la Bolsa: paso 1 |
| Falta consultar fondos en DataFondos | Pasos 2 y 4 |
| Lo explican varios instrumentos | Varios instrumentos de la cuenta pagan ese monto: mirar el PDF o el export. No se elige uno |
| Ningún reparto publicado cuadra con el monto | Un instrumento de la cuenta tiene un reparto en la fecha pero el monto no da: puede pagarlo otro instrumento de la cuenta o venir de cuotas de otra fecha |
| Ni la Bolsa ni DataFondos publican un reparto que lo pague | Instrumentos sin reparto publicado en la fecha, fondos que ninguno de los dos sigue, o instrumentos que la Bolsa no publica. El detalle nombra cada caso |

Un abono **por revisar** es una cuadratura que no cierra: la cartola trae el instrumento y para ese instrumento hay un reparto publicado con otro monto. Mirarlo contra el PDF. Un abono **sin comprobar** trae su instrumento, pero ningún reparto publicado lo paga (por ejemplo, una disminución de capital por rescate de cuotas): sale con el instrumento de la cartola y queda anotado en el reporte.

Las reglas están en `docs/eventos-capital.md`.

## Agregar una institución nueva a los eventos de capital

`eventos_capital.py` no depende del formato de la cartola ni de la fuente de los repartos. Necesita que el extractor entregue las posiciones de cada cuenta con su cantidad y nombre (o nemotécnico) y los movimientos de caja con fecha, cuenta, tipo, moneda y monto. Si la institución nombra sus abonos por dividendos o repartos de otra forma, agregar esos tipos a `TIPOS_CAJA` con la clase de evento que los paga, y a `TIPOS_TITULOS` los movimientos de títulos que imprime con el monto por cuota. Agregar también una prueba en `tests/test_eventos_capital.py`.

## Mantener la tabla maestra

`datos/instrumentos.csv` se regenera desde uno o más exports de BICE con `python -m cartolas.catalogo "<carpeta del export>" ["<otra carpeta>" ...]`; si un nemotécnico aparece con nombres distintos, queda el del último día. Los instrumentos que no están en la tabla salen sin nemotécnico ni emisor y con un aviso en el reporte. Si la cartola nombra un instrumento distinto que el export, se agrega una fila a `datos/alias.csv` con el nombre de la cartola, la moneda y el nemotécnico.
