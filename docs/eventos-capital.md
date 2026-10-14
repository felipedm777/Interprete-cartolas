# Eventos de capital con la Bolsa y DataFondos

Las cartolas abonan en la caja del cliente los dividendos, repartos y
disminuciones de capital de acciones y fondos, pero no siempre dicen de qué
instrumento vienen ni qué tipo de reparto son. La Bolsa de Santiago y DataFondos
publican cada dividendo y reparto con su fecha límite, su fecha de pago y el
monto por acción o cuota: con eso un abono se puede identificar y comprobar.

Este documento no tiene datos de clientes: los montos y nemotécnicos de ejemplo
son de instrumentos, que son datos públicos.

## Qué no queda claro en cada formato

| Formato | Lo que imprime | Lo que falta |
|---|---|---|
| BICE nueva | `DIVIDENDO EN PESOS`, `DIVIDENDO EN DOLARES`, `REPARTO DE DINERO`, `REPARTO DE DINERO EN USD`, `PAGO DE DIVIDENDOS` con el monto | El instrumento. El export de BICE sí lo trae, así que la salida queda incompleta sin deducirlo |
| BICE nueva | `DIVIDENDO <NEMO> (DIV <NEMO> <cantidad> * <monto>)` en cuentas Pershing | Nada: trae el papel y el monto unitario en el tipo |
| BICE antigua | `DIVIDENDO EN PESOS` con el nemotécnico | El monto por cuota, para comprobar el abono |
| Valores Security | `DIVIDENDO EN PESOS`/`EN DOLARES` y `DISMINUCION DE CAPITAL - ABONO EN CUENTA MERCANTIL` con el nemotécnico, y el movimiento de títulos con el monto por cuota | Nada que falte; sirve para comprobar contra el reparto publicado |
| Larrainvial | `ABONO POR DISMINUCION DE CAPITAL`, `DIVIDENDO EN DOLARES` con el nemotécnico | Ídem |
| Sura | `DIVIDENDO EN PESOS` con el monto | El instrumento, y sin más cartolas del mismo mes no hay con qué compararlo |
| Pershing | `MONEY FUND INCOME`, `SECURITY LIQUIDATED` | No pasan por este emparejamiento |

La cartola BICE nueva también separa el dividendo del reparto de capital en dos
abonos del mismo día, que es justamente la distinción que publican la Bolsa y
DataFondos.

## Las fuentes

| | Bolsa de Santiago | DataFondos |
|---|---|---|
| Qué publica | Dividendos y repartos de acciones nacionales, fondos de inversión (CFI y CFM) y emisores extranjeros que se transan en la Bolsa | Repartos de unos 134 fondos y series, y la fecha de 11 acciones sin el monto |
| Cómo se obtiene | Un Excel acumulado que la Bolsa publica cada día hábil; la corrida lo baja si la tabla es anterior al último cierre, o `python -m cartolas.bolsa` | Por la API de DataFondosv2 (`/api/v1`, la misma del MCP): `resumen_dividendos` para saber qué fondos sigue y `dividendos` fondo por fondo. La corrida la consulta sola con `DATAFONDOS_API_URL` y `DATAFONDOS_API_KEY`; sin ellas, por el MCP |
| Tabla de la skill | `datos/eventos_bolsa_<AAAAMMDD>.csv`, con la fecha del Excel | `datos/eventos_capital.csv` y `datos/datafondos_cobertura.csv` |
| Para qué sirve | La fuente principal: cubre casi todo lo que traen las cartolas | Los fondos que la Bolsa no publica, y los eventos que se informaron pero no pagaron dinero (`Anulado`) |

La skill une las dos tablas. Un mismo evento puede estar en las dos; no importa,
porque lo que identifica un abono es el instrumento, no el evento.

## La tabla de la Bolsa

La Bolsa publica cada día hábil el Excel "resumen dividendos - repartos -
emisiones" en

```
https://servicioscms.bolsadesantiago.com/Paginas/Descarga.aspx?attach=Noticias%2Favisos+generales%2F<AAAAMMDD>+resumen+dividendos+-+repartos+-+emisiones.xlsx
```

Es acumulado: trae los pagos desde 2022 hasta los ya anunciados, así que basta
el más reciente. Para una fecha sin archivo (fin de semana, feriado) la Bolsa
responde una página HTML en vez del Excel: `python -m cartolas.bolsa` prueba
desde hoy hacia atrás, hasta 10 días, y se queda con el primero que es un Excel
de verdad. Los cinco de septiembre de 2026 que se probaron están contenidos en
el del 09-10-2026, salvo entre 0 y 6 eventos por archivo que la Bolsa corrigió
después.

De sus 16 hojas se leen las 4 que pagan dinero por acción o cuota:

| Hoja | Clase de evento | Nemotécnicos |
|---|---|---|
| Dividendos acciones nacionales | `DIVIDENDO`, o `REPARTO DE CAPITAL` si el tipo dice "Reparto" | El de la acción |
| Dividendos CFI nacionales | Ídem | El de pesos y el de dólares (`CFICPD2A-E` y `CFI-CPD2AE`), que son el mismo sin el guion |
| Repartos CFI-CFM | `REPARTO DE CAPITAL`, aunque el tipo diga "Provisorio" | Ídem |
| Dividendos emisores extranjeros | `DIVIDENDO` | El de dólares y el de pesos (`AAPL` y `AAPLCL`): se guardan los dos |

Las demás (fechas sin derecho, emisiones de pago y liberadas, canjes,
divisiones, stock splits, spin offs, llamados de capital, ofertas públicas y los
dividendos de emisores colombianos del convenio Cross-Listing) no traen un monto
en dinero que se pueda cuadrar con un abono.

Cómo se lee cada fila:

- El encabezado se busca por su texto ("Nombre Emisor") y las columnas por su
  nombre, no por su posición.
- `MontoPorCuota` es la celda "Por Acción / cuota". Casi siempre es un número.
  Si es texto, se acepta un número con coma decimal (`7,199693879412`) o con
  punto y más de tres decimales (`0.17699525`). "Ver documento", "(ver
  observaciones)" y "-" quedan sin monto. Cualquier otro texto (`2 18,1848371858`)
  queda sin monto y **dudoso**, con el texto original en `Evento`.
- La moneda: `$` es CLP, `US$` es USD, `EURO` es EUR y `Soles` es PEN.
- Una fila sin nemotécnico o sin fecha de pago no es un evento que se pueda
  cuadrar: se descarta y se cuenta.

`python -m cartolas.bolsa` imprime la cuadratura de cada hoja: filas con
contenido = eventos leídos + filas descartadas. Con el Excel del 09-10-2026:

| Hoja | Filas | Eventos | Descartadas | Con monto | Dudosos |
|---|---:|---:|---:|---:|---:|
| Dividendos acciones nacionales | 1.069 | 1.060 | 9 | 1.060 | 0 |
| Dividendos CFI nacionales | 12.401 | 12.382 | 19 | 12.245 | 1 |
| Repartos CFI-CFM | 8.094 | 8.069 | 25 | 6.954 | 1 |
| Dividendos emisores extranjeros | 4.309 | 4.308 | 1 | 4.308 | 0 |

La tabla guarda los eventos pagados desde el 1 de enero del año anterior al
Excel (`--desde` cambia la fecha): 16.132 eventos, con pagos del 01-01-2025 al
04-01-2027. Tiene las mismas columnas que la de DataFondos; `RutFondo` queda
vacío porque la Bolsa no lo publica. Al escribir la nueva se borra la anterior.

```
python -m cartolas.bolsa                         # baja el más reciente
python -m cartolas.bolsa <AAAAMMDD>.xlsx         # usa uno ya bajado
python -m cartolas.bolsa --desde 2024-01-01      # guarda más historia
```

Bajarlo necesita internet y leerlo, la librería `openpyxl`. La skill lee solo el
CSV, o un Excel con `python -m cartolas ... --bolsa <archivo.xlsx>`.

## La tabla de DataFondos

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

La tabla del repositorio se armó el 08-10-2026 con los 56 fondos que aparecen en
las cartolas anonimizadas, desde agosto de 2025: 289 eventos.

### La consulta a la API de DataFondos

DataFondos es el repositorio DataFondosv2. Su MCP es una capa delgada sobre su
API de solo lectura: `resumen_dividendos` es `GET /api/v1/dividendos/resumen` y
`dividendos` es `GET /api/v1/fondos/{rut}/dividendos?nemo=`, con la misma
respuesta (`{"ok": true, "data": [...]}`). Por eso `datafondos.py` lee las
respuestas de la API con el mismo código que las del MCP.

Con `DATAFONDOS_API_URL` y `DATAFONDOS_API_KEY` en el entorno (una key nominal
con el scope `valores:read`), cada corrida, antes de conciliar:

1. pide el resumen y actualiza la cobertura;
2. calcula, sin tocar las cartolas, qué fondos pediría consultar la
   conciliación (`eventos_capital.pendientes`);
3. pide `dividendos` de cada uno con el RUT y el nemotécnico con que DataFondos
   lo lista, y agrega a la tabla los repartos pagados desde el 1 de enero del
   año anterior (o desde el inicio de las cartolas, si es antes);
4. concilia con la tabla actualizada.

Las respuestas quedan en `<carpeta de salida>/datafondos/`. Una falla (sin red,
key inválida o sin permiso, límite de consultas) no detiene la corrida: queda
en el reporte y se concilia con las tablas que había. `python -m
cartolas.datafondos` hace lo mismo a mano: sin argumentos actualiza la
cobertura y comprueba la conexión; con `--fondo RUT NEMOTECNICO` agrega los
repartos de esos fondos.

Probado con una API simulada que sirve la tabla del repositorio: con la tabla
sin los repartos pagados desde julio de 2026, la corrida de las 480 cartolas
BICE de septiembre consultó 12 fondos, agregó 42 repartos y dio el mismo
resultado que con la tabla completa (585 confirmados, 5 identificados, 10
dudosos sin la tabla de la Bolsa) y los mismos archivos.

### La cobertura de DataFondos

`skill/cartolas/datos/datafondos_cobertura.csv` guarda lo que devuelve
`resumen_dividendos`: cada fondo y serie que sigue DataFondos, cuántos repartos
tiene publicados, la fecha del último y cuándo los actualizó.

```
Nemotecnico;RutFondo;Serie;Nombre;Eventos;UltimaFecha;Actualizado
CFIAMG3R-E;9879;R;AMERIS NM P CREDIT;51;2026-10-07;2026-10-07
```

La corrida la actualiza desde la API. Por el MCP, se actualiza con el mismo
comando de la tabla: reconoce sola una respuesta de `resumen_dividendos` y la
guarda en la cobertura en vez de la tabla. La que trae
la skill es del 08-10-2026, con 134 fondos y series.

## Qué se sabe de cada instrumento de la cuenta

Para un abono que ningún evento explica, la skill dice qué se sabe de cada
instrumento de la cuenta en la fecha del abono, en este orden:

1. Tiene un evento publicado en la fecha, pero el monto no da.
2. La Bolsa publica sus eventos: si el Excel de la tabla es del día del abono o
   posterior, **no hay reparto publicado en la fecha** (el evento que lo pagó
   tendría que estar, porque se anuncia antes de pagarse); si es anterior, **falta
   bajar el Excel al día**.
3. Es una acción u otro instrumento que no es un fondo y la Bolsa no lo publica.
   Sin tabla de la Bolsa, falta bajarla.
4. Es un fondo que la Bolsa no publica: se mira la cobertura de DataFondos.
   DataFondos no lo sigue; lo sigue y tiene repartos más nuevos que la tabla, o
   los actualizó antes del abono (**falta consultarlo** con `dividendos`); o lo
   sigue, la tabla está al día y no hay reparto en la fecha. Sin cobertura, todo
   fondo que no está en la tabla queda por consultar.

## Las causas de un abono dudoso

Cada dudoso queda como caja, con una causa en el reporte y el detalle de qué se
sabe de cada instrumento de la cuenta. La causa es la primera de esta lista que
aplica:

| Causa | Cuándo |
|---|---|
| Falta bajar el Excel de la Bolsa al día | Algún instrumento de la cuenta lo publica la Bolsa y el Excel de la tabla es anterior al abono, o no hay tabla de la Bolsa y la cuenta tiene acciones |
| Falta consultar fondos en DataFondos | Algún fondo de la cuenta que la Bolsa no publica está por consultar. El reporte lista esos fondos con su RUT y el nemotécnico como lo escribe DataFondos, que es lo que pide `dividendos` |
| Lo explican varios instrumentos | Más de un instrumento de la cuenta tiene un reparto que da el monto |
| Ningún reparto publicado cuadra con el monto | Algún instrumento de la cuenta tiene un reparto en la fecha, pero ninguno da el monto |
| Ni la Bolsa ni DataFondos publican un reparto que lo pague | Los instrumentos de la cuenta no tienen reparto publicado en la fecha, son fondos que ninguno de los dos sigue, o son instrumentos que la Bolsa no publica |

El paso a paso para resolver los que faltan, con el Excel de la Bolsa y el MCP
de DataFondos, está en `skill/SKILL.md`, "Eventos de capital con la Bolsa y
DataFondos".

## Cómo se explica un abono

Para cada abono de los tipos de `TIPOS_CAJA` (los cargos `PAGO DE DIVIDENDOS`
son el pago al cliente de un dividendo ya abonado, no el evento, y el export los
deja como caja):

1. Se buscan los eventos de los instrumentos que la cuenta tiene en cartera, de
   la clase que corresponde al tipo del movimiento (un `REPARTO DE DINERO` acepta
   tanto `REPARTO DE CAPITAL` como `DISMINUCION DE CAPITAL`: la Bolsa y las
   cartolas le ponen los dos nombres al mismo hecho), en la moneda del abono y
   con fecha de pago entre 6 días después y 12 días antes de la fecha del abono.
2. El evento explica el abono si `MontoPorCuota × cuotas de la cuenta` da el
   monto abonado, con holgura de 0,5 % y un piso de 1 peso (o 0,5 dólares) por
   el redondeo de la cartola, **o** si la cartola trae el movimiento de títulos
   del evento con el mismo monto por cuota publicado.
3. Si un solo instrumento lo explica y el movimiento no traía instrumento, se le
   pone ese nemotécnico. Si lo explican varios, o ninguno, el abono queda
   **dudoso**: se informa en el reporte y la fila sale como caja, nunca con un
   instrumento inventado.
4. Si el movimiento ya traía instrumento (Security, Larrainvial, o deducido por
   `dividendos.py`) y el monto cuadra, queda **confirmado** y entra como
   cuadratura. Si para ese instrumento hay un evento de la fecha y el monto no
   cuadra, es una cuadratura que **no cierra**: la cartola y lo publicado se
   contradicen y hay que mirarlo. Si no hay ningún evento de ese instrumento en
   la fecha, queda **sin comprobar**: sale con el instrumento de la cartola y se
   anota en el reporte.

El paso 2 por monto por cuota impreso importa porque las cuotas del cierre no
son siempre las que tenían derecho al reparto: si el cliente compró después de
la fecha límite, `cuotas × monto` no da el abono, y el precio que imprime la
cartola sí cuadra con el publicado.

Las cuotas se suman por cuenta y nemotécnico, así que un instrumento con varias
posiciones en la misma cuenta se trata como uno solo.

Los nemotécnicos se comparan sin guiones ni espacios: un mismo fondo y serie se
escribe `CFI-AMG3RE` o `CFIAMG3R-E`, el export de BICE usa los dos, DataFondos a
veces publica solo uno y la Bolsa pone uno en la columna de pesos y el otro en la
de dólares.

## Agregar una institución nueva

El emparejamiento no depende del formato: usa las posiciones de cada cuenta,
con su cantidad, y los movimientos de caja, con fecha, cuenta, tipo, moneda y
monto. Para una institución nueva basta con que su extractor los entregue así y
con agregar a `TIPOS_CAJA` los nombres que da a sus abonos por dividendos o
repartos (y a `TIPOS_TITULOS` los movimientos de títulos que imprime con el
monto por cuota, si los trae).

## Lo que no alcanza a cubrir

- **Fondos que no se transan en la Bolsa y DataFondos no sigue.** Quedan
  dudosos y el detalle los nombra.
- **Disminuciones de capital por rescate de cuotas.** El fondo paga un precio
  por cuota rescatada, no un monto por cada cuota en circulación, y la Bolsa no
  las publica en la hoja de repartos: salen con el instrumento de la cartola y
  quedan sin comprobar.
- **Abonos anteriores a la tabla de la Bolsa.** La tabla guarda los pagos desde
  el 1 de enero del año anterior al Excel; para cartolas más antiguas hay que
  regenerarla con `--desde`.
- **Dividendos reinvertidos.** No pasan por la caja, así que no hay abono que
  explicar; siguen apareciendo como aporte al fondo.

## Resultado contra los datos anonimizados (13-10-2026)

Con el Excel de la Bolsa del 09-10-2026 y la tabla de DataFondos del 08-10-2026.

Las 480 cartolas BICE de septiembre de 2026 (`Cartolas BICE SFTP/202609`)
tienen 606 abonos por eventos de capital:

| | Solo DataFondos | Bolsa y DataFondos |
|---|---:|---:|
| Confirmados (instrumento y monto cuadran con el reparto publicado) | 585 | 591 |
| Identificados con la tabla (no traían instrumento) | 5 | 12 |
| Dudosos | 10 | 3 |
| Por revisar (la cartola y lo publicado se contradicen) | 0 | 0 |
| Con instrumento, sin un reparto publicado que los compruebe | 6 | 0 |

Comparada con el export de BICE del mismo período, la salida cambia solo en
`MOVIMIENTOS_DE_CAJA` y solo para mejor: los 3 abonos que antes salían como caja
y el export trae con su instrumento (`LIPIGAS`, `MALLPLAZA` y `CFI-CARSGE`) ahora
salen con ese instrumento y su producto. Ningún instrumento asignado difiere del
export, y los otros 6 archivos quedan idénticos.

Los 3 dudosos que quedan no los explica ninguna fuente:

| Dudosos | Por qué |
|---:|---|
| 2 | Dividendos en dólares del mismo día en dos cuentas cuyos fondos no tienen reparto publicado en la fecha; la otra posición es `IBIT`, que no publica la Bolsa |
| 1 | Dividendo en pesos de una cuenta con `CFIBCIRFCL`, que no publican ni la Bolsa ni DataFondos, y `CFIVNTFIIV`, cuyos dividendos mensuales se pagaron el 03-09 y el 06-10 |

Con las 59 cartolas de `Training Data`, por formato:

| Formato | Abonos | Confirmados | Identificados | Dudosos | Sin comprobar | Por revisar |
|---|---:|---:|---:|---:|---:|---:|
| BICE nueva | 23 | 21 | 2 | 0 | 0 | 0 |
| BICE antigua | 4 | 4 (antes 3) | 0 | 0 | 0 | 0 |
| Valores Security | 89 | 89 (antes 77) | 0 | 0 | 0 | 0 |
| Larrainvial | 2 | 1 | 0 | 0 | 1 | 0 |
| Sura | 8 | 0 | 3 | 5 | 0 | 0 |
| Pershing | 0 | | | | | |

El abono sin comprobar de Larrainvial es una disminución de capital por rescate
de cuotas, que la Bolsa no publica. Los 5 dudosos de Sura siguen como antes: 3
de una cuenta con un fondo que tiene un reparto en la fecha que no da el monto y
dos acciones sin dividendo en la fecha ("Ningún reparto publicado cuadra con el
monto"), y 2 de fondos sin reparto en la fecha ("Ni la Bolsa ni DataFondos
publican un reparto que lo pague"). Los archivos de salida de `Training Data`
quedan idénticos a los de antes de la Bolsa.
