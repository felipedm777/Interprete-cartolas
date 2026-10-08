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
repetidos. `resumen_dividendos` dice, en una llamada, qué fondos tiene
DataFondos y hasta cuándo, y sirve para saber a qué fondos pedirles el detalle.

La tabla del repositorio se armó el 08-10-2026 con los 56 fondos que aparecen en
las cartolas anonimizadas, desde agosto de 2025: 289 eventos (234 dividendos, 48
repartos de capital, 6 emisiones liberadas), con pagos del 05-08-2025 al
15-10-2026.

## Cómo se explica un abono

Para cada movimiento de caja de los tipos de `TIPOS_CAJA`:

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

## Lo que no alcanza a cubrir

- **Dividendos de acciones.** DataFondos publica los repartos de los fondos; los
  `PAGO DE DIVIDENDOS` de acciones chilenas y los dividendos de ETF extranjeros
  de las cuentas Pershing quedan dudosos. Solo se consultan los nemotécnicos que
  empiezan con `CFI` o `CFM`, que son los de fondos.
- **Fondos que DataFondos no sigue.** Quedan listados en el reporte, con el mes,
  para pedirlos y ampliar la tabla.
- **Dividendos reinvertidos.** No pasan por la caja, así que no hay abono que
  explicar; siguen apareciendo como aporte al fondo.

## Resultado contra los datos anonimizados (08-10-2026)

Con las 480 cartolas BICE de septiembre de 2026 (`Cartolas BICE SFTP/202609`):

| | Abonos |
|---|---:|
| Confirmados (instrumento y monto cuadran con el reparto publicado) | 583 |
| Identificados con la tabla (no traían instrumento) | 3 |
| Dudosos | 31 |
| Contradicciones con la cartola | 0 |

De los 31 dudosos, 22 son dividendos de acciones o de ETF extranjeros y 9 son de
fondos que no están en la tabla. Comparada con el export de BICE del mismo
período, la salida de los portafolios de AFI queda **idéntica** a la de antes de
este cambio: los tres abonos identificados son de portafolios que el export no
trae. De los dos que el export sí permite comprobar en `Training Data`
(`CFILBKA2-E` y `CFIAFOGAPA`), los dos coinciden con el instrumento del export.

Con las 59 cartolas de `Training Data` (los 6 formatos): 100 abonos confirmados
y 5 identificados, 6 dudosos y ninguna contradicción. Los 5 identificados son 2
de BICE nueva —que con solo 20 cartolas del mes no se pueden deducir comparando
clientes— y 3 de Sura, que no traen instrumento y antes salían como caja.
