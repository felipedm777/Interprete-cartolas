# Eventos de capital con DataFondos

Las cartolas abonan en la caja del cliente los dividendos, repartos y
disminuciones de capital de los fondos, pero no siempre dicen de qué fondo
vienen ni qué tipo de reparto son. DataFondos publica, por fondo y serie, cada
reparto con su fecha límite, su fecha de pago y el monto por cuota: con eso un
abono se puede identificar y comprobar.

Este documento no tiene datos de clientes: los montos y nemotécnicos de ejemplo
son de fondos, que son datos públicos.

## Qué no queda claro en cada formato

| Formato | Lo que imprime | Lo que falta |
|---|---|---|
| BICE nueva | `DIVIDENDO EN PESOS`, `DIVIDENDO EN DOLARES`, `REPARTO DE DINERO`, `REPARTO DE DINERO EN USD`, `PAGO DE DIVIDENDOS` con el monto | El instrumento. El export de BICE sí lo trae, así que la salida queda incompleta sin deducirlo |
| BICE nueva | `DIVIDENDO <NEMO> (DIV <NEMO> <cantidad> * <monto>)` en cuentas Pershing | Nada: trae el papel y el monto unitario en el tipo |
| BICE antigua | `DIVIDENDO EN PESOS` con el nemotécnico | El monto por cuota, para comprobar el abono |
| Valores Security | `DIVIDENDO EN PESOS`/`EN DOLARES` y `DISMINUCION DE CAPITAL - ABONO EN CUENTA MERCANTIL` con el nemotécnico, y el movimiento de títulos con el monto por cuota | Nada que falte; sirve para comprobar contra el reparto publicado |
| Larrainvial | `ABONO POR DISMINUCION DE CAPITAL`, `DIVIDENDO EN DOLARES` con el nemotécnico | Ídem |
| Sura | `DIVIDENDO EN PESOS` con el monto | El instrumento, y sin más cartolas del mismo mes no hay con qué compararlo |
| Pershing | `MONEY FUND INCOME`, `SECURITY LIQUIDATED` | No son fondos chilenos: DataFondos no los cubre |

La cartola BICE nueva también separa el dividendo del reparto de capital en dos
abonos del mismo día, que es justamente la distinción que DataFondos publica
("DIVIDENDO PROV.", "REPARTO CAP.").

## La tabla

`skill/cartolas/datos/eventos_capital.csv`, con una fila por evento:

```
RutFondo;NemotecnicoInstrumento;Clase;Moneda;MontoPorCuota;FechaLimite;FechaPago;Anulado;Evento
9991;CFISMH1B-E;DIVIDENDO;CLP;264,8097994;2026-09-23;2026-09-29;0;DIVIDENDO PROV. $ 264,8097994
9991;CFISMH1B-E;REPARTO DE CAPITAL;CLP;349,9154356;2026-09-23;2026-09-29;0;REPARTO CAP.  $ 349,9154356
```

- `Clase` normaliza el texto del evento: `DIVIDENDO`, `REPARTO DE CAPITAL`,
  `DISMINUCION DE CAPITAL`, `EMISION LIBERADA` u `OTRO`.
- `MontoPorCuota` se lee del texto del evento, que trae todos los decimales;
  `pago_por_accion` viene redondeado a tres y no cuadra con el abono.
- `Anulado = 1` es un evento que la Bolsa informó pero que no bajó el valor
  cuota: no pagó dinero y no se usa para explicar abonos.
- `Evento` queda tal como lo publica DataFondos, para poder rastrear el dato.

Se mantiene con las respuestas de la herramienta `dividendos` guardadas como
JSON:

```
python -m cartolas.eventos_capital <respuesta.json>... [--desde 2025-08-01]
```

El comando no pisa lo que ya había: agrega los eventos nuevos y descarta los
repetidos. `--desde` deja fuera los eventos de las respuestas pagados antes de
esa fecha; los que la tabla ya tenía se mantienen.

## La cobertura

`skill/cartolas/datos/datafondos_cobertura.csv` guarda lo que devuelve
`resumen_dividendos`: cada fondo y serie que sigue DataFondos, cuántos repartos
tiene publicados, la fecha del último y cuándo los actualizó.

```
Nemotecnico;RutFondo;Serie;Nombre;Eventos;UltimaFecha;Actualizado
CFIAMG3R-E;9879;R;AMERIS NM P CREDIT;51;2026-10-07;2026-10-07
```

Se actualiza con el mismo comando: reconoce sola una respuesta de
`resumen_dividendos` y la guarda en la cobertura en vez de la tabla. Con ella la
skill sabe, para cada fondo de la cuenta de un abono dudoso, si:

- DataFondos no lo sigue: consultarlo no sirve.
- DataFondos lo sigue y tiene repartos más nuevos que la tabla, o los actualizó
  antes del abono: **falta consultarlo** con `dividendos`.
- DataFondos lo sigue, la tabla está al día y no hay reparto en la fecha.

Sin cobertura, todo fondo que no está en la tabla queda por consultar, como en
la primera versión. La que trae la skill es del 08-10-2026, con 134 fondos y
series.

## Las causas de un abono dudoso

Cada dudoso queda como caja, con una causa en el reporte y el detalle de qué se
sabe de cada instrumento de la cuenta:

| Causa | Cuándo |
|---|---|
| Falta consultar fondos en DataFondos | Algún fondo de la cuenta está por consultar. El reporte lista esos fondos con su RUT y el nemotécnico como lo escribe DataFondos, que es lo que pide `dividendos` |
| Lo explican varios fondos | Más de un fondo de la cuenta tiene un reparto que da el monto |
| Ningún reparto publicado cuadra con el monto | Algún fondo de la cuenta tiene un reparto en la fecha, pero ninguno da el monto |
| DataFondos no tiene un reparto que lo pague | Los instrumentos de la cuenta son acciones, fondos que DataFondos no sigue o fondos sin reparto en la fecha |

El paso a paso para resolver los que faltan consultar, con el MCP de DataFondos,
está en `skill/SKILL.md`, "Eventos de capital con DataFondos".

La tabla del repositorio se armó el 08-10-2026 con los 56 fondos que aparecen en
las cartolas anonimizadas, desde agosto de 2025: 289 eventos (234 dividendos, 48
repartos de capital, 6 emisiones liberadas), con pagos del 05-08-2025 al
15-10-2026.

## Cómo se explica un abono

Para cada abono de los tipos de `TIPOS_CAJA` (los cargos `PAGO DE DIVIDENDOS`
son el pago al cliente de un dividendo ya abonado, no el evento, y el export los
deja como caja):

1. Se buscan los eventos de los fondos que la cuenta tiene en cartera, de la
   clase que corresponde al tipo del movimiento (un `REPARTO DE DINERO` acepta
   tanto `REPARTO DE CAPITAL` como `DISMINUCION DE CAPITAL`: la Bolsa y las
   cartolas le ponen los dos nombres al mismo hecho) y con fecha de pago entre
   6 días después y 12 días antes de la fecha del abono.
2. El evento explica el abono si `MontoPorCuota × cuotas de la cuenta` da el
   monto abonado, con holgura de 0,5 % y un piso de 1 peso (o 0,5 dólares) por
   el redondeo de la cartola, **o** si la cartola trae el movimiento de títulos
   del evento con el mismo monto por cuota que publica DataFondos.
3. Si un solo fondo lo explica y el movimiento no traía instrumento, se le pone
   ese nemotécnico. Si lo explican varios, o ninguno, el abono queda **dudoso**:
   se informa en el reporte y la fila sale como caja, nunca con un fondo
   inventado.
4. Si el movimiento ya traía instrumento (Security, Larrainvial, o deducido por
   `dividendos.py`) y el monto cuadra, queda **confirmado** y entra como
   cuadratura. Si para ese fondo hay un evento de la fecha y el monto no cuadra,
   es una cuadratura que **no cierra**: la cartola y DataFondos se contradicen y
   hay que mirarlo.

El paso 2 por monto por cuota impreso importa porque las cuotas del cierre no
son siempre las que tenían derecho al reparto: si el cliente compró después de
la fecha límite, `cuotas × monto` no da el abono, y el precio que imprime la
cartola sí cuadra con el publicado.

Las cuotas se suman por cuenta y nemotécnico, así que un fondo con varias
posiciones en la misma cuenta se trata como una sola.

Los nemotécnicos se comparan sin guiones: un mismo fondo y serie se escribe
`CFI-AMG3RE` o `CFIAMG3R-E`, el export de BICE usa los dos y DataFondos a veces
publica solo uno.

## Agregar una institución nueva

El emparejamiento no depende del formato: usa las posiciones de cada cuenta,
con su cantidad, y los movimientos de caja, con fecha, cuenta, tipo, moneda y
monto. Para una institución nueva basta con que su extractor los entregue así y
con agregar a `TIPOS_CAJA` los nombres que da a sus abonos por dividendos o
repartos (y a `TIPOS_TITULOS` los movimientos de títulos que imprime con el
monto por cuota, si los trae).

## Lo que no alcanza a cubrir

- **Dividendos de acciones.** DataFondos publica los repartos de los fondos y
  sigue solo 11 acciones, sin el monto por acción: los dividendos de acciones
  quedan dudosos. Solo se consultan los nemotécnicos que empiezan con `CFI` o
  `CFM`, que son los de fondos.
- **Fondos que DataFondos no sigue.** Quedan dudosos y el detalle los nombra; no
  se piden porque DataFondos no los tiene.
- **Dividendos reinvertidos.** No pasan por la caja, así que no hay abono que
  explicar; siguen apareciendo como aporte al fondo.

## Resultado contra los datos anonimizados (08-10-2026)

Con las 480 cartolas BICE de septiembre de 2026 (`Cartolas BICE SFTP/202609`):

| | Abonos |
|---|---:|
| Confirmados (instrumento y monto cuadran con el reparto publicado) | 585 |
| Identificados con la tabla (no traían instrumento) | 5 |
| Dudosos | 10 |
| Contradicciones con la cartola | 0 |

Comparada con el export de BICE del mismo período, la salida de los portafolios
de AFI queda **idéntica** a la de antes de este cambio: los cinco abonos
identificados son de portafolios que el export no trae. De los dos que el export
sí permite comprobar en `Training Data` (`CFILBKA2-E` y `CFIAFOGAPA`), los dos
coinciden con el instrumento del export.

Los 10 dudosos se buscaron uno por uno en DataFondos y ninguno se puede
confirmar con lo que publica:

| Dudosos | Por qué DataFondos no los explica |
|---:|---|
| 4 | Dividendos de acciones (el export confirma dos: `LIPIGAS` y `MALLPLAZA`). DataFondos sigue solo 11 acciones y ninguna de estas; `CHILE`, que sí sigue, no pagó dividendo en septiembre |
| 4 | Los fondos de la cuenta que podrían pagarlos no están en DataFondos (`CFI-CARSGE`, que es el que dice el export, `CFISDA5F-E`, `CFIBCIRFCL`, `CFIVNTFIIV`) o están sin repartos ese mes (`CFIBTGPLAA`, `CFILCEUP-E`) |
| 2 | Dividendos en dólares del mismo día en dos cuentas, que no cuadran con ningún reparto publicado de los fondos de la cuenta. El único fondo de esas cuentas sin repartos en la tabla es `CFI-ANM7AE`, que DataFondos sigue sin ningún reparto publicado |

Con la cobertura, la skill llega sola a esa misma revisión: los 10 quedan con la
causa "DataFondos no tiene un reparto que lo pague", ninguno por consultar, y el
detalle de cada uno nombra las acciones, los fondos que DataFondos no sigue y
los que no tienen reparto en la fecha.

Con las 59 cartolas de `Training Data` (los 6 formatos): 102 abonos confirmados
y 5 identificados, 5 dudosos y ninguna contradicción. Los 5 identificados son 2
de BICE nueva —que con solo 20 cartolas del mes no se pueden deducir comparando
clientes— y 3 de Sura, que no traen instrumento y antes salían como caja. Los 5
dudosos son de Sura: 3 de una cuenta con acciones y un fondo con un reparto en
la fecha que no da el monto ("Ningún reparto publicado cuadra con el monto") y 2
de fondos que DataFondos sigue sin un reparto en la fecha ("DataFondos no tiene
un reparto que lo pague").
