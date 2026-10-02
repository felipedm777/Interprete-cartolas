# Inventario de formato: estados de cuenta Pershing (custodia internacional)

Fuentes revisadas (solo lectura):

- `Training Data/BICE viejas/Corredora de bolsa/<cuenta>_MSTAT_<n>_<timestamp>.pdf`: 5 archivos, introducing broker **BICE Inversiones Corredores de Bolsa S.A.**
- `Training Data/Sura/Sura pershing-Agosto-<cliente>.pdf`: 1 archivo, introducing broker **Corredores de Bolsa Sura**.

Convención de este documento: `<CUENTA>` es el número de cuenta Pershing, `<NOMBRE>` el titular y `<COD>` el código de documento o de ejecutivo. Los números de ejemplo son sintéticos (`1,234.56`).

**Conclusión principal:** los dos orígenes usan **la misma plantilla Pershing LLC (BNY Pershing) en español**, con la misma tipografía, la misma geometría de columnas y los mismos títulos de sección. Cambian el logo del introducing broker, que es una imagen y no texto, y algunas **opciones de configuración del estado de cuenta**: columnas YTD, orden de las transacciones, orden de las secciones y bloques multimoneda. Detalle en §2.3. Un solo extractor parametrizable sirve para ambos.

---

## 1. Archivos

| Archivo | Período (texto del PDF) | Páginas | Notas |
|---|---|---|---|
| `<cuenta>_MSTAT_1_…161612.pdf` | 1 de enero de 2026 - 31 de enero de 2026 | 8 | |
| `<cuenta>_MSTAT_2_…161615.pdf` | 1 de febrero de 2026 - 28 de febrero de 2026 | 8 | |
| `<cuenta>_MSTAT_3_…161618.pdf` | 1 de marzo de 2026 - 31 de marzo de 2026 | 13 | Incluye 5 páginas extra de "Mensajes" en inglés (*PERSHING LLC (BNY PERSHING) ANNUAL DISCLOSURE…*) y una página 13 en blanco que solo trae el pie |
| `<cuenta>_MSTAT_4_…161620.pdf` | 1 de abril de 2026 - 30 de abril de 2026 | 8 | |
| `<cuenta>_MSTAT_0_…161611.pdf` | 1 de mayo de 2026 - 31 de mayo de 2026 | 8 | |
| `Sura pershing-Agosto-<cliente>.pdf` | 1 de agosto de 2026 - 31 de agosto de 2026 | 10 | Otro cliente y otra cuenta |

- **Línea de tiempo BICE:** los 5 MSTAT son **5 meses consecutivos de la misma cuenta** (ene–may 2026). El índice `<n>` del nombre **no es cronológico**: 1=ene, 2=feb, 3=mar, 4=abr, 0=may. Hay que ordenar por el período leído en el contenido. Los timestamps del nombre son todos del 2026-06-24 entre 16:16:11 y 16:16:20, o sea, una descarga en lote. Vale como fecha de descarga, no de emisión.
- **Encadenamiento probado:** `VALOR FINAL DE LA CUENTA` del mes m = `VALOR INICIAL DE LA CUENTA` del mes m+1 en los 4 empalmes (ene→feb, feb→mar, mar→abr, abr→may), con diferencia 0,00. La columna "Año hasta la Fecha" mantiene el mismo valor inicial (el de enero) en los 5 meses. Los ingresos YTD también encadenan: YTD(m) = YTD(m-1) + período(m), exacto al centavo.
- **Duplicados:** no hay. La similitud de texto entre meses es alta (0,77–0,99) porque el texto legal es el mismo, pero el período, los saldos y las transacciones difieren. El archivo de Sura es de otro cliente y otra cuenta.
- **Fecha de emisión:** no aparece impresa, y los metadatos del PDF vienen vacíos porque el anonimizador los borra. Lo práctico es usar el fin del período.
- **Moneda del reporte:** USD. Todos los totales están en USD. En Sura hay además una posición en GBP que se muestra en GBP y en su equivalente USD.
- **Página:** carta apaisada, 792 × 612 pt, rotación 0, en todos los archivos.
- **Texto:** extraíble en todas las páginas, con fuentes embebidas `C0EX….afm` y sin escaneos, así que no hace falta OCR. Las imágenes son el logo del broker arriba a la izquierda, el logo "su Cuenta de Inversiones", un QR "Acceso en línea" (solo BICE) y la banda de logos del pie (GOPAPERLESS, DALBAR, "Clearing through Pershing LLC…").
- **Tamaño:** unos 75 KB los MSTAT de 8 páginas, 473 KB el de marzo y 81 KB el de Sura.
- **Marcadores (outline):** los PDF traen tabla de contenidos (`doc.get_toc()`) con el título de cada sección y su página de inicio. Sirve para saber qué secciones existen sin parsear (ver §8).

## 2. Estructura del documento

### 2.1 Elementos de página (ambos orígenes)

- **Página 1:** logo del broker arriba a la izquierda (imagen) y "su Cuenta de Inversiones" a la derecha (imagen). A la izquierda, el bloque de dirección (x≈103, y≈126–185): `<NOMBRE>` en 1 o 2 líneas, dirección, comuna, región o ciudad y país. A la derecha, el período (x≈536–734, y≈133) y `Número de Cuenta: <CUENTA>` (y≈146).
  - Solo BICE: el nombre del ejecutivo en x≈32, y≈233, a la misma altura que "VALOR INICIAL DE LA CUENTA".
- **Páginas impares ≥3:** encabezado con logo, el período (y≈74) y el nombre del titular (y≈87). En BICE solo sale la primera línea del nombre (truncado, en la fuente original); en Sura, el nombre completo.
- **Pie de todas las páginas:**
  - `Página N de M` (x≈680–734, y≈577).
  - `Número de Cuenta: <CUENTA>` (x≈281–376, y≈590), que **no** aparece en la página 1.
  - Código de documento `<COD>` del estilo `A0000000CSF000DP-SD` (y≈598).
- **Títulos de sección:** en banda azul, con texto en x≈44–46. Cuando una sección continúa en la página siguiente, se repite el título con `(continuación)`, también en subtítulos: `U.S. DOLLARS (continuación)`, `Productos Negociados en Bolsa (continuación)`, `Acciones (continuación )` (este último con un espacio antes del paréntesis). Los encabezados de columna también se repiten en cada página.

### 2.2 Secciones en orden

**BICE (MSTAT, los 5 iguales; en marzo solo se alarga "Mensajes"):**

1. Resumen de la Cartera (p1)
2. Resumen de Activos (p1)
3. Divulgación y Notas al pie sobre Resumen de Activos (p1). Aparece porque hay un título sin precio.
4. **Tenencias en Cartera** (p2)
5. Divulgaciones de tenencias de cartera (p3–4, texto legal)
6. **Resumen de Actividad** (Todos los montos listados están valorados) (p5)
7. **Transacciones Ordenadas por Fecha** (p5)
8. Información de Atención a Clientes (p5)
9. Información de su cuenta (p5–6)
10. **Detalles del Fondo de Money Market** (p6)
11. Mensajes (p6; en marzo, p6–10)
12. **Resumen de Ingresos y Gastos** (p6–7; en abril y mayo se parte entre páginas con "(continuación)")
13. Declaraciones e información importantes (p7–8)

**Sura:**

1. Resumen de la Cartera (p1)
2. Resumen de Activos, con gráfico circular (p1)
3. Información de Atención a Clientes (p1)
4. Información de su cuenta (p2)
5. **Tabla de Tipos de Cambio** (p2)
6. **Resumen de Ingresos y Gastos** (p2)
7. **Resumen de Actividad** (p3)
8. **Transacciones por Tipo de Actividad** (p3)
9. **Tenencias en Cartera** (p3–6), agrupadas por moneda: `U.S. DOLLARS` y luego `BRITISH POUND`
10. **Resumen de tenencias por divisa** (p6)
11. Divulgaciones de tenencias de cartera (p6–7)
12. Mensajes (p8)
13. **Detalles del Fondo de Money Market** (p9)
14. Declaraciones e información importantes (p9–10)

En **negrita** las secciones con datos para extraer. El resto es texto legal o informativo.

### 2.3 Diferencias BICE vs Sura (misma plantilla, distinta configuración)

| Aspecto | BICE | Sura |
|---|---|---|
| Resumen de la Cartera | Columnas `Este Período` + `Año hasta la Fecha`. Filas extra `Intereses Devengados` y `Valor de la cuenta con intereses acumulados` | Solo `Este Período` |
| Resumen de Activos | `Período Anterior` + `Período Actual` | Solo `Período Actual` y gráfico circular. El total se llama `Total de la Cuenta (Gráfico Circular)` |
| Transacciones | `Transacciones Ordenadas por Fecha` (lista plana) | `Transacciones por Tipo de Actividad`, con subtítulo por tipo (`Dividendos e Intereses`) y subtotal (`Total de Dividendos e Intereses`) |
| Orden de secciones | Tenencias antes de Actividad; Ingresos y Gastos al final | Ingresos y Gastos y Actividad antes de Tenencias |
| Multimoneda | No; sin subtítulo de moneda. Las categorías traen `NN.NN% de Cartera` | Subtítulos `U.S. DOLLARS` / `BRITISH POUND`, `Tabla de Tipos de Cambio` y `Resumen de tenencias por divisa` |
| Atención a Clientes | Código de ejecutivo, nombre del ejecutivo, dirección de la oficina, teléfono y `Sitio Web: WWW.BICEINVERSIONES.CL` | Solo `Número de Identificación: <COD>` |
| Identificación del broker en texto | `WWW.BICEINVERSIONES.CL`, "Acceso en línea" | Ninguna; el logo es imagen. El prefijo de 3 caracteres de `<CUENTA>` también difiere entre ambos |
| Divulgación y Notas al pie sobre Resumen de Activos | Sí (por el bono sin precio) | No |

Además, el contenido depende de la cartera, no del broker: las secciones y subsecciones solo aparecen si hay datos. Por ejemplo, la fila `Cambio Neto en la Cartera` falta en enero y febrero porque vale 0 en el período y en YTD, y `Distribuciones` solo aparece cuando hubo una.

## 3. Detalle por sección

Formato general de números y fechas:

- **Números en formato EE.UU.:** `,` para miles y `.` para decimales (`1,234.56`). Las cantidades llevan 4 decimales (`1,234.0000`), los precios y el costo unitario 4 (`123.4560`) y los montos 2.
- **Signo `$`:** solo en totales y en algunas filas resumen (`$1,234.56`). Las filas de detalle no lo llevan.
- **Negativos:** con signo menos adelante, `-1,234.56` o `-$1,234.56` (el menos va antes del `$`). No se usan paréntesis.
- **Porcentajes:** `1.23%`.
- **Valores no disponibles:** el literal `No disponible` en precio, valor, ganancia o pérdida y en la columna "Número de Cuenta" del money market.
- **Fechas:**
  - Período: texto en español, `1 de marzo de 2026 - 31 de marzo de 2026`.
  - Filas: `MM/DD/YY` (`03/31/26`).
  - Tabla de tipos de cambio: `MM/DD/YYYY` (`08/31/2026`).
- **Textos en inglés:** los tipos de actividad y las descripciones de instrumentos vienen en mayúsculas y en inglés (`MONEY FUND INCOME`, `SECURITY LIQUIDATED`, `AMAZON COM INC COM`). Las etiquetas fijas están en español.
- **Superíndices de notas al pie:** `1`, `1,5`, `5`, en Helvetica-Bold de 5,3 pt, son **originales** del PDF. Quedan pegados al texto que les sigue: `get_text("words")` produce `1,5CORP` y `Cartera1`.

### 3.1 Resumen de la Cartera (p1, bloque derecho x≈433–734)

Etiquetas en x≈433. BICE tiene dos columnas numéricas (bordes derechos ≈655 y ≈734); Sura tiene una (≈734).

```
                                         Este Período   Año hasta la Fecha
VALOR INICIAL DE LA CUENTA                  $1,234.56        $1,234.56
Dividendos, Intereses y Otros Ingresos          12.34            56.78
Cambio Neto en la Cartera¹                      12.34            56.78     (solo si ≠ 0)
VALOR FINAL DE LA CUENTA                    $1,234.56        $1,234.56
Intereses Devengados                            $0.00                      (BICE)
Valor de la cuenta con intereses acumulados $1,234.56                      (BICE, dos líneas)
Ingresos Anuales Estimados                     $12.34
¹ El cambio neto en la cartera es la diferencia entre el valor de la cuenta al final y valor de la cuenta al inicio después de la actividad.
```

El set de filas es variable: Pershing solo imprime las filas con valor. En otros meses pueden aparecer depósitos, retiros, cargos o valores recibidos o entregados, que no se han visto en estas muestras. Hay que parsear por etiqueta.

### 3.2 Resumen de Activos (p1)

- Encabezado BICE: `Porcentaje | Tipo del activo | Período Anterior | Período Actual`.
- Encabezado Sura: `Porcentaje | Tipo del activo | Período Actual`.
- Filas observadas: `Efectivo, Fondos de Dinero y Depósitos Bancarios`, `Acciones`, `Productos Negociados en Bolsa`.
- Total: `Total de la Cuenta` (BICE) o `Total de la Cuenta (Gráfico Circular)` (Sura).
- Los títulos sin precio (el bono en BICE) **no aparecen** aquí.

### 3.3 Tenencias en Cartera

La geometría es idéntica en ambos orígenes. Bordes derechos aproximados de las columnas numéricas: 183, 239, 312, 388, 466, 560, 626/698, 734.

**a) Efectivo, Fondos de Dinero y Depósitos Bancarios › Money Market** (sweep `BNY MELLON US DOLLAR LIQD SERV`)

```
Fecha Inicial | Cantidad | Número de Cuenta | Actividades Finalizando el | Saldo de Apertura | Saldo al Cierre | Ingresos Devengados | Ingresos en este Año | Rédito a 30 Días | Rédito Actual
```

- Una línea con el nombre del fondo y una fila de datos. "Número de Cuenta" dice `No disponible`.
- `Actividades Finalizando el` es el último día hábil del mes, no el fin del período.
- Subtotales: `Total de Money Market` y `Total de Efectivo, Fondos de Dinero y Depósitos Bancarios`.
- Cantidad = Saldo al Cierre (1 cuota = 1 USD).

**b) Títulos de deuda/ingresos fijos › Bonos Corporativos** (BICE: `CORP GROUP BANKING SA NT REG S ESCROW 6.750% 03/15/23`, bono en default)

```
Fecha de Adquisición | Cantidad | Costo por Unidad | Base de Costo Actual | Precio de Mercado | Valor de Mercado | Ganancia o Pérdida No Realizada | Intereses Devengado
```

Estructura del bloque, con 5 líneas por instrumento:

1. Nombre, con la nota `1,5` pegada, y a la derecha `Código de Identificación de Títulos: P31ESCAA7`.
2. Tres líneas de atributos (`B/E DTD …`, `SECURITY 1ST CPN …`, `AND SEP 15 Moody Rating …`).
3. Fila de datos, con `No disponible` en precio, valor y G/P.
4. `Base de Costo Original: $…`.

Los subtotales `Total de Bonos Corporativos` y `Total de Títulos de deuda/ingresos fijos` **ocupan dos líneas**: los montos van en la primera y la cantidad nominal en la línea de abajo. El encabezado de categoría dice `0.00% de Cartera (en secuencia según la Fecha de Vencimiento)`.

**c) Acciones › Acciones Ordinarias** y **d) Productos Negociados en Bolsa** (ETF), en USD

```
Fecha de Adquisición | Cantidad | Costo por Unidad | Base de Costo Actual | Precio de Mercado | Valor de Mercado | Ganancia o Pérdida No Realizada | Ingresos Anuales Estimados | Rédito Estimado
```

Bloque por instrumento:

1. Nombre (con ISIN si es ADR: `ALIBABA GROUP HLDG LTD SPONSORED ADR ISIN#US01609W1027`) y a la derecha `Código de Identificación de Títulos: <TICKER>`.
2. `Opción de Dividendos: Efectivo` (en ETF: `…; Opción de Ganancias de Capital:` + una 3.ª línea `Efectivo`) y a la derecha `CUSIP: <CUSIP>`.
3. **Una fila por lote** (fecha de adquisición).
4. Si hay más de un lote: `Total Cubierto` y `Total`. También podría existir `Total No Cubierto`, no visto.

Con un solo lote no hay fila de total. Las columnas EAI y Rédito pueden venir **vacías**, así que no sirve contar tokens.

Subtotales: `Total de Acciones Ordinarias`, `Total de Acciones`, `Total de Productos Negociados en Bolsa`, `Total de U.S. Dollars`. Este último tiene su propio encabezado: `Base de Costo Actual | Valor de Mercado | Ganancia o Pérdida No Realizada | Intereses Devengados | Ingresos Anuales Estimados`.

**e) Posiciones en moneda no USD** (Sura, `BRITISH POUND`)

```
Descripción | Cantidad | Precio de Mercado | Valor de Mercado | Divisa | Ingresos Anuales Estimados | Rédito Estim.
```

- La fila trae Cantidad, precio local y valor local con `GBP`. La línea siguiente trae el valor en USD con `USD`. EAI también va en dos líneas, local y USD.
- Siguen las líneas `Código de Identificación de Títulos: ANTO:GB`, `CUSIP: G0398N128` y `Precio estimado partir de: 08/28/26`. Esta última solo aparece cuando la fecha del precio difiere del cierre.
- **No hay base de costo ni G/P** para esta posición.
- Totales en dos líneas (GBP y USD): `Total de Acciones Ordinarias`, `Total de Acciones` y `TOTAL DE BRITISH POUND`, este último con columnas `Valor de Mercado Divisa | Intereses Acumulados | Ingresos Anuales Estimados`.

**Total final:** `Total Tenencias en Cartera` (BICE) o `Total Tenencias en Cartera - U.S. DOLLARS` (Sura), con columnas `Base de Costo Actual | Valor de Mercado | Ganancia o Pérdida No Realizada | Intereses Acumulados | Ingresos Anuales Estimados`.

- La base de costo total incluye el money market (su costo es su saldo).
- En Sura **excluye** la posición GBP, que no tiene costo, pero el valor de mercado total sí la incluye.

**Tablas que cruzan páginas:** en Sura las tenencias ocupan las páginas 3 a 6. El cambio de página puede caer entre instrumentos o entre la fila de un instrumento y su total (el total GBP quedó en la p6 bajo `Acciones (continuación )`).

### 3.4 Resumen de tenencias por divisa (solo multimoneda)

- Columnas dinámicas, una por moneda: `BRITISH POUND (GBP) | U.S. DOLLARS (USD)`.
- Filas: `Efectivo, Fondos de Dinero y Depósitos Bancarios` (el texto se parte en 2 líneas y el número queda en la primera), `Acciones`, `Productos Negociados en Bolsa`, `Total de valor de mercado local`, `Total de valor de mercado (USD)`, `Porcentaje de cartera`.

### 3.5 Tabla de Tipos de Cambio (solo multimoneda)

- Columnas: `Divisa | Equivalente en USD | Unidades por USD`. Fila de ejemplo: `BRITISH POUND  1.2345  0.8100`.
- Nota al pie: `Los tipos de cambio están basados en tipos de cambio interbancarios al MM/DD/YYYY.`

### 3.6 Resumen de Actividad (Todos los montos listados están valorados)

```
<categoría> | Créditos por este Períodos | Débitos por este Períodos | Neto por este Período | Créditos Durante este Año | Débitos Durante este Año | Neto Durante este Año
```

- "Períodos" viene con la errata del original.
- Bordes derechos aproximados: 307, 390, 472, 568, 651, 734.
- Categorías observadas: `Dividendos e Intereses`, `Distribuciones`, `Cargos`, `Impuestos Retenidos`, y la fila total `Totales`.
- Los débitos llevan signo negativo (`-$1,234.56`).
- Una categoría aparece si tiene movimiento en el período **o en el año**. En Sura salen `Cargos` e `Impuestos Retenidos` con 0 en el período y valores YTD distintos de 0.

### 3.7 Transacciones (Ordenadas por Fecha | por Tipo de Actividad)

```
Fecha de Proces. o Liquid. | Tipo de Actividad | Descripción | Cantidad | Precio | Intereses Devengados | Monto | Divisa
```

Posiciones aproximadas: fecha x 37–68, tipo x 111–182, descripción x 248–460. Bordes derechos de las columnas numéricas: cantidad ≈498, precio ≈555, intereses ≈623, monto ≈702. La divisa va en x 711–725.

Cada transacción ocupa **2 líneas**:

- **Línea 1:** fecha, tipo y descripción (1.ª parte), más los números.
- **Línea 2:** bajo "Tipo de Actividad", el **identificador del título** (CUSIP o código Pershing: `P31ESCAA7`, `PER981831` para el fondo BNY Mellon). Bajo "Descripción", la continuación del texto.

En Sura, el tipo de actividad de la línea 1 queda 1 pt más abajo que la fecha. Agrupar filas con tolerancia de ±2–3 pt.

- **Cierre de la tabla:** `Valor Total de las Transacciones` (total de intereses devengados y total de monto + `USD`), seguido de `Es posible que el precio y la cantidad se hayan redondeado.`
- **En Sura:** subtítulo por tipo (`Dividendos e Intereses`) y subtotal (`Total de Dividendos e Intereses`) antes del total general.
- **Tipos observados:** `MONEY FUND INCOME` (dividendo del sweep) y `SECURITY LIQUIDATED` (pago de liquidación del bono escrow, sin cantidad ni precio).
- **No hay en estas muestras** compras, ventas, dividendos de acciones, retenciones, comisiones ni transferencias. Los YTD de Sura muestran que sí ocurrieron en otros meses: hacen falta muestras con esos tipos antes de cerrar el extractor.

### 3.8 Detalles del Fondo de Money Market

```
Fecha | Tipo de Actividad | Descripción | Monto | Saldo
```

- Encabezado del bloque: `Fondo de Money Market con Transferencia Automática`, luego el nombre del fondo y `Rédito actual: N.NN% Actividades que Finalizando el: MM/DD/YY`.
- Filas:
  - `Saldo de Apertura`
  - `Depósito` (descripción `INCOME REINVEST` o `MONEY FUND PURCHASE`)
  - `Saldo al Cierre` (con `$`, solo en la columna Saldo)
  - `Total de Todos los Fondos de Money Market`
- No se vio el retiro (redención), que probablemente se llama `Retiro`; no está verificado.
- Aquí los tipos vienen en español; las descripciones, en inglés.

### 3.9 Resumen de Ingresos y Gastos

```
                                     Período Actual            Año hasta la Fecha
                                 Gravable   No Gravable     Gravable   No Gravable
Ingresos por Dividendos
  Acciones | Fondos Money Market | Otros Dividendos
  Total de ingresos
Distribuciones
  Otras Distribuciones
  Total de Distribuciones
Gastos
  Cargos (Títulos no Estadounidenses)
  Total de gastos
```

Bordes derechos aproximados: 415, 492, 645, 734.

## 4. Saldos y movimientos

**Aportan saldos:**

| Sección | Tipo de saldo |
|---|---|
| Tenencias › Money Market | Caja (sweep en USD). Cantidad = saldo |
| Tenencias › Acciones / Acciones Ordinarias | Acciones, incluidos ADR |
| Tenencias › Productos Negociados en Bolsa | ETF |
| Tenencias › Títulos de deuda/ingresos fijos | Bonos (en la muestra: valor `No disponible`, que cuenta como 0) |
| Tenencias › bloque por moneda (BRITISH POUND …) | Acciones extranjeras en moneda local más su equivalente USD |
| Resumen de Activos / Resumen de tenencias por divisa | Solo totales por clase y moneda, para validar |

No se vieron en estas muestras: fondos mutuos, depósitos a plazo o CD, opciones, productos estructurados ni saldo de caja libre fuera del sweep. La plantilla los contempla (aparecen en las divulgaciones), pero no tenemos su layout.

**Aportan movimientos:**

| Sección | Tipo de movimiento |
|---|---|
| Transacciones (Ordenadas por Fecha / por Tipo de Actividad) | Todos los eventos de caja y de títulos del período. Es la fuente principal |
| Detalles del Fondo de Money Market | Barridos del sweep (reinversión de dividendos, compra o venta de cuotas). **Duplican económicamente** las transacciones: `MONEY FUND INCOME` corresponde a `Depósito INCOME REINVEST`, y `SECURITY LIQUIDATED` a `Depósito MONEY FUND PURCHASE`. Usar solo para cuadrar, no para exportar |
| Resumen de Actividad / Resumen de Ingresos y Gastos | Totales por categoría (período y YTD), para validar |

## 5. Mapeo al formato de Example

El Example Export es de BICE (portafolio 10038) y **no trae ninguna fila Pershing**. `MOVIMIENTOS_PERSHING` solo tiene encabezado: utf-8 sin BOM, CRLF, `;`. Tampoco hay filas Pershing en `CUSTODIA_ACCIONES`, `SALDOS_*` ni `MOVIMIENTOS_DE_CAJA`, así que **varias decisiones de mapeo no se pueden inferir del ejemplo** y hay que preguntarlas (marcadas con ❓).

Conversión de formato, común a todos los destinos:

- Números en formato EE.UU. a coma decimal sin separador de miles (`1,234.5600` → `1234,560000`). El ejemplo usa 6 decimales en saldos, 4 en cantidad y precio de movimientos y 2 en montos; a veces omite el 0 inicial (`,9530`).
- Fechas `MM/DD/YY` a `YYYY-MM-DD`.

### 5.1 MOVIMIENTOS_PERSHING (una fila por transacción de la sección Transacciones)

| Columna destino | Fuente en el PDF |
|---|---|
| Cantidad | `Cantidad` (vacía en dividendos e ingresos; con valor en compras y ventas). ❓ signo en ventas |
| FechaProceso | `Fecha de Proces. o Liquid.` de la fila. ❓ o fecha de cierre del período / fecha de proceso del export |
| RutCliente | **Sin fuente.** Pershing no imprime RUT. Requiere una tabla maestra `CuentaPershing → RUT`. El titular BICE tiene el mismo nombre ficticio que un cliente de las cartolas Larrainvial, así que un cruce por nombre es posible pero frágil |
| Cuenta | **Sin fuente** (en el ejemplo es la subcuenta interna BICE: 0, 1, 90…). ❓ |
| CuentaPershing | `Número de Cuenta:` (p1 arriba a la derecha y pie de cada página). ❓ con o sin guion |
| Portafolio | **Sin fuente** (nombre de portafolio AFITRADING; tabla maestra) |
| ProductoBase | **Sin fuente.** Probablemente constante (¿`CUENTA INVERSION`?). ❓ |
| Producto | Derivable de la clase del instrumento en Tenencias (Acciones, Productos Negociados en Bolsa, Money Market, Bonos), cruzando por CUSIP o código. ❓ vocabulario (¿`ACCIONES`/`ETF` como en CUSTODIA?) |
| Instrumento | `Descripción` (línea 1 + continuación de la línea 2) |
| NemotecnicoInstrumento | Identificador de la línea 2 (CUSIP o código Pershing). Para tener el ticker hay que cruzarlo con `CUSIP:` → `Código de Identificación de Títulos:` en Tenencias. Si el título ya no está en cartera, el ticker no está disponible |
| MonedaInstrumento | Moneda del bloque de Tenencias del título, o `Divisa` |
| Emisor | **Sin fuente** (se puede usar la descripción o dejarlo vacío) |
| NumeroRerferencia | **Sin fuente** (Pershing no imprime número de operación) |
| NombreTipoMovimiento | `Tipo de Actividad` (en inglés: `MONEY FUND INCOME`, `SECURITY LIQUIDATED`…). ❓ traducir al vocabulario BICE (`COMPRA RV`, `DIVIDENDO EN DOLARES`…) o dejarlo literal |
| Moneda | `Divisa` (USD) |
| PrecioTIR | `Precio` |
| MontoNeto | `Monto`. ❓ convención de signo (Pershing: crédito +, débito −; el ejemplo BICE pone `COMPRA RV` con monto positivo) |

### 5.2 MOVIMIENTOS_DE_CAJA (si se decide duplicar ahí los eventos de caja Pershing ❓)

| Columna destino | Fuente |
|---|---|
| FechaProceso | Fecha de la transacción |
| RutCliente, Cuenta, Portafolio, ProductoBase | Sin fuente (igual que en 5.1) |
| Producto | ¿`CUENTAS CAJA`? ❓ |
| Instrumento | `Descripción` |
| nombreTipoMovimiento | `Tipo de Actividad` |
| Moneda | `Divisa` |
| abono / cargo | `Monto` > 0 va a abono; `Monto` < 0 va a cargo (en valor absoluto) |
| TipoAPV, DescripcionTipoRegimenTributario | Vacíos (no es APV) |

### 5.3 SALDOS_CAJA (money market sweep ❓: ¿caja o fondo?)

| Columna destino | Fuente |
|---|---|
| FechaProceso | Fin del período (o `Actividades Finalizando el`) ❓ |
| RutCliente, Cuenta, Portafolio, ProductoBase | Sin fuente (tabla maestra). Además, SALDOS no tiene columna CuentaPershing ❓ dónde va la cuenta |
| Producto | ¿`CUENTAS CAJA`? ❓ |
| MonedaValoracionPatrimonio | `USD` |
| PatrimonioEnMonedaValoracion / patrimonioUSD | `Saldo al Cierre` del money market |
| patrimonioCLP | Sin fuente: USD × TipoCambioUSD externo |
| TipoAPV, DescripcionTipoRegimenTributario | Vacíos |
| EnTransito | `NO` (constante) |
| TipoCambioUSD / TipoCambioEUR | **Sin fuente** en el PDF (dólar y euro observados de la fecha de proceso) |

Alternativa: llevarlo a **SALDOS_FFMM** como fondo (`Instrumento` = `BNY MELLON US DOLLAR LIQD SERV`, `Cantidad` = cuotas, precio = 1). ❓

### 5.4 CUSTODIA_ACCIONES (acciones, ADR, ETF; una fila por instrumento, sumando los lotes)

| Columna destino | Fuente |
|---|---|
| Producto | `ACCIONES` (sección Acciones) / `ETF` (Productos Negociados en Bolsa), según el vocabulario del ejemplo ❓ |
| Instrumento | Línea de nombre (sin el sufijo `ISIN#…`, o con él ❓) |
| NemotecnicoInstrumento | `Código de Identificación de Títulos:` (ticker; en GBP viene `ANTO:GB`) |
| MonedaInstrumento | Subtítulo de moneda (`U.S. DOLLARS` → USD, `BRITISH POUND` → GBP); en BICE, implícito USD |
| Emisor | Sin fuente (se puede repetir la descripción) |
| Cantidad | Fila `Total` si hay varios lotes; si no, la del único lote (o la suma de lotes) |
| PrecioCierreEnMonedaValoracion | `Precio de Mercado` (en la moneda del instrumento; para GBP, ❓ si convertir a USD con la Tabla de Tipos de Cambio) |
| PrecioPromedioCompra | `Base de Costo Actual` total / Cantidad. Vacío para GBP (sin costo) |
| MonedaValoracionPatrimonio | `USD` |
| PatrimonioEnMonedaValoracion / patrimonioUSD | `Valor de Mercado` (USD; para GBP la línea `… USD`) |
| patrimonioCLP, TipoCambioUSD, TipoCambioEUR | Sin fuente (tipo de cambio externo) |
| TipoAPV, DescripcionTipoRegimenTributario | Vacíos |
| EnTransito | `NO` |

**Bonos** (Títulos de deuda/ingresos fijos): **no hay archivo destino** en el Example. El bono escrow de la muestra tiene precio y valor `No disponible`. ❓ omitir, o exportar con valor 0 a CUSTODIA o a un archivo nuevo.

### 5.5 Columnas sin fuente en ningún archivo Pershing

`RutCliente`, `Cuenta` (interna BICE), `Portafolio`, `ProductoBase`, `Emisor`, `NumeroRerferencia`, `patrimonioCLP`, `TipoCambioUSD`, `TipoCambioEUR`, `TipoAPV`, `DescripcionTipoRegimenTributario` (vacíos) y `EnTransito` (constante). Las cuatro primeras necesitan una **tabla maestra por CuentaPershing** que mantenga Felipe.

## 6. Cuadraturas (probadas numéricamente)

Tolerancia observada: **0,00** en todas las sumas impresas. Las excepciones por redondeo de precio unitario o de tipo de cambio se indican en la tabla.

| # | Cuadratura | MSTAT ene–may (5) | Sura ago |
|---|---|---|---|
| 1 | VALOR INICIAL + Dividendos, Intereses y Otros Ingresos + Cambio Neto = VALOR FINAL (período y YTD) | 0,00 en los 5 | 0,00 |
| 2 | VALOR FINAL(m) = VALOR INICIAL(m+1) | 0,00 en 4 empalmes | n/a |
| 3 | YTD(m) = YTD(m-1) + período(m) (ingresos) | 0,00 | n/a |
| 4 | Resumen de Activos: Período Anterior = VALOR INICIAL; Período Actual = VALOR FINAL; suma de clases = total | 0,00 | 0,00 (la clase Acciones = acciones USD + equivalente USD de las GBP) |
| 5 | Money market: Saldo de Apertura + Depósitos − Retiros = Saldo al Cierre (Detalles) = Saldo al Cierre (Tenencias) = Cantidad | 0,00 | 0,00 |
| 6 | Total Tenencias: Base de Costo = Σ costo de títulos + saldo money market; Valor de Mercado = VALOR FINAL | 0,00 | 0,00 (el costo excluye GBP) |
| 7 | Resumen de Actividad: Σ filas = Totales y Créditos + Débitos = Neto (6 columnas) | 0,00 | 0,00 |
| 8 | Σ Monto de transacciones = Valor Total de las Transacciones = Neto por este Período (Totales de Actividad) | 0,00 | 0,00 |
| 9 | Por lote: Cantidad × Precio de Mercado = Valor de Mercado | n/a | ≤ 0,005 |
| 10 | Por lote: Valor de Mercado − Base de Costo = Ganancia o Pérdida No Realizada | n/a | 0,00 |
| 11 | Por lote: Cantidad × Costo por Unidad ≈ Base de Costo | n/a | hasta ±0,10 (costo unitario redondeado a 4 decimales). **No usar con tolerancia estricta** |
| 12 | Σ lotes = Total / Total de <subcategoría> / Total de <categoría> / Total de <moneda> (costo, valor, G/P, EAI) | n/a | 0,00 |
| 13 | Valor local × `Equivalente en USD` = valor USD (GBP) | n/a | 0,00 en la muestra, pero la tasa tiene 4 decimales: tolerancia ≈ valor_local × 0,00005 + 0,01. `1/Unidades por USD` **no** cuadra (error de unidades USD) |
| 14 | Resumen de tenencias por divisa = totales por moneda de Tenencias | n/a | 0,00 |
| 15 | Resumen de Ingresos y Gastos (Total de ingresos YTD) = Resumen de Actividad (Dividendos e Intereses YTD) | 0,00 | 0,00 |

Tampoco cuadra lo siguiente, pero porque no es comparable: `Cargos` del Resumen de Actividad (YTD) ≠ `Total de gastos` del Resumen de Ingresos y Gastos. El segundo solo incluye `Cargos (Títulos no Estadounidenses)`, mientras que Actividad incluye todos los cargos de la cuenta.

## 7. Riesgos y particularidades

1. **Avisos del anonimizador ("con avisos" en RESUMEN.txt).** Según `herramientas/anonimizar_cartolas.py` (`Verificador.revisar` → `avisos`; reporte: `revisar nombres sueltos: …`), un aviso significa que en la copia **quedó un nombre de pila suelto** (≥3 letras) igual al nombre de pila de alguno de los 451 clientes. **No bloquea la copia.** El token concreto solo figura en el `reporte_anonimizacion.txt` privado de Felipe.
   - En los 5 MSTAT, lo más probable es que sea el **nombre del ejecutivo BICE**: aparece en `Información de Atención a Clientes` y en la columna izquierda de la p1, es un nombre de pila común y el archivo de Sura, sin aviso, no tiene nombre de ejecutivo.
   - **Para la extracción no afecta ningún número.** Sí hay que tenerlo en cuenta en tres cosas:
     - (a) no confundirlo con el titular;
     - (b) `pdftotext -layout` lo funde en la misma línea que `VALOR INICIAL DE LA CUENTA`, así que un regex de línea debe tomar solo los montos de la derecha;
     - (c) son nombres reales del personal BICE: no copiarlos a fixtures, tests ni ejemplos del repositorio.
2. **Texto reemplazado al final del orden de texto.** El titular (o solo parte de él), la dirección y la cuenta (p1 y pie de cada página) están en Helvetica al final del flujo. Además, el email y el código de ejecutivo de Sura, y el nombre del encabezado de las páginas impares de Sura. Con `page.get_text()` sin ordenar, `Número de Cuenta:` queda seguido de `Página N de M`. **Hay que leer por coordenadas.** Los superíndices de notas (`1`, `1,5`, `5`, Helvetica-Bold 5,3 pt) son originales: no sirve "Helvetica = anonimizado" como regla.
3. **El titular en BICE ocupa 2 líneas en la p1** y solo la 1.ª se repite en el encabezado de las páginas impares. No hay separación fiable entre nombre y dirección. No usar el nombre como llave: usar `<CUENTA>`.
4. **Sin RUT en el documento.** RutCliente, Cuenta y Portafolio dependen de una tabla maestra externa.
5. **Columnas que cambian según configuración y contenido.** Resumen de la Cartera con 1 o 2 columnas; Resumen de Activos con 1 o 2; columnas EAI y Rédito vacías en algunas filas; filas del resumen solo cuando ≠ 0. Asignar columnas por **borde derecho** anclado a las palabras del encabezado de cada tabla, no por posición fija ni por número de tokens.
6. **Bloques multilínea.** Instrumentos con 2–5 líneas de descripción antes de los lotes; transacciones en 2 líneas; totales de bonos con la cantidad en la línea siguiente; posiciones no USD con valor local y USD en dos líneas. Superíndices pegados al texto (`1,5CORP`, `Cartera1`).
7. **Tablas que cruzan páginas,** con título y encabezados repetidos y `(continuación)` (incluida la variante `Acciones (continuación )`). Hay que ignorar encabezado y pie de página y los títulos repetidos.
8. **Doble conteo:** Transacciones vs Detalles del Fondo de Money Market describen los mismos eventos. Exportar solo desde Transacciones.
9. **Títulos sin precio** (`No disponible`): quedan fuera del valor total y del Resumen de Activos, pero sí suman a la Base de Costo total. El cobro por liquidación del bono escrow aparece como `SECURITY LIQUIDATED` / `Distribuciones` y en el Resumen de la Cartera como `Cambio Neto en la Cartera`, no como ingreso.
10. **Posición no USD sin base de costo:** PrecioPromedioCompra queda vacío. Además, el total de costo de la cuenta no incluye esa posición.
11. **Tipos de actividad en inglés,** con vocabulario abierto. En la muestra solo hay 2 (`MONEY FUND INCOME`, `SECURITY LIQUIDATED`). **Faltan muestras** con compras, ventas, dividendos de acciones, retenciones (`Impuestos Retenidos`), cargos y transferencias para fijar sus layouts y signos.
12. **Orden de los archivos MSTAT:** el índice del nombre no es cronológico (`_0` = el mes más reciente).
13. **Páginas extra:** el anexo anual en inglés dentro de "Mensajes" y la página final en blanco (marzo) no deben romper el parser. Conviene ignorar secciones no listadas.
14. **Identificar el broker** para elegir la configuración: por carpeta de origen, por `WWW.BICEINVERSIONES.CL` en el texto o por el prefijo de `<CUENTA>`. El logo es imagen.

## 8. Enfoque recomendado de extracción

1. **pymupdf con palabras y coordenadas** (`page.get_text("words")`, más `get_text("dict")` cuando haga falta el tamaño de fuente). Es la base:
   - Agrupar en filas por `y` con tolerancia de ±2,5 pt.
   - Descartar la zona de encabezado y pie: y < 95 en páginas impares ≥3 e y > 570.
   - Descartar superíndices: spans con tamaño < 6 pt.
   - Por qué: el layout es de columnas con números alineados a la derecha, sin líneas de tabla. Las coordenadas son estables entre meses y entre brokers, y el texto anonimizado queda bien ubicado por posición aunque esté al final del flujo.
2. **Segmentar por secciones** con `doc.get_toc()`, que da el título y la página de inicio, y confirmar con el título en x≈44–46 (aceptando `(continuación)`). Las secciones de datos son: Resumen de la Cartera, Resumen de Activos, Tenencias en Cartera, Resumen de tenencias por divisa, Tabla de Tipos de Cambio, Resumen de Actividad, Transacciones Ordenadas por Fecha / por Tipo de Actividad, Detalles del Fondo de Money Market y Resumen de Ingresos y Gastos.
3. **Columnas:** en cada tabla, leer la fila de encabezado y usar el **borde derecho (x1) de cada palabra de encabezado** como ancla de su columna. Asignar cada número al ancla más cercana por x1. Esto absorbe la diferencia BICE/Sura (1 o 2 columnas) y las celdas vacías.
4. **Tenencias como máquina de estados:** moneda (`U.S. DOLLARS` / `BRITISH POUND`) → categoría → subcategoría → instrumento (línea con `Código de Identificación de Títulos:`) → atributos (`CUSIP:`, `Opción de Dividendos`, líneas de bono) → lotes (fila que empieza con `MM/DD/YY`) → totales (`Total…`).
   - Para cantidad y valor por instrumento, preferir las filas `Total` cuando existan. Si no, sumar los lotes y validar contra el subtotal.
   - En el bloque no USD, la línea `… USD` siguiente da el valor en dólares.
5. **Transacciones:** una fila con fecha inicia un registro; la línea siguiente sin fecha aporta el identificador (columna Tipo) y la continuación de la descripción. Los subtítulos y subtotales por tipo (Sura) se reconocen por estar en x≈37 sin fecha.
6. **Metadatos:**
   - Período por regex `(\d{1,2}) de (\w+) de (\d{4}) - (\d{1,2}) de (\w+) de (\d{4})` (meses en español).
   - `<CUENTA>` = palabra a la derecha de `Número de Cuenta:` en el pie (y≈590) o en la p1 (y≈146–147).
   - Moneda = USD salvo bloques por divisa.
7. **Validación automática** con las cuadraturas 1, 4–8, 9, 10, 12 y 13 de §6, que cuadran al centavo; la 11 solo como advertencia. Si hay varios meses de la misma cuenta, validar también el encadenamiento (2) y el YTD (3).
8. **Descartados:**
   - **pdfplumber `extract_tables`:** no hay líneas de tabla. La estrategia "lines" devuelve 1 tabla vacía y la estrategia "text" corta palabras (`Ganan|cia`, `Acciones Ordinar|ias`).
   - **`pdftotext -layout` + regex:** útil para exploración rápida, pero funde bloques lado a lado (el ejecutivo con VALOR INICIAL, las dos columnas de "ENVÍO ELECTRÓNICO") y el espaciado varía.
   - **OCR:** innecesario.

---

## 9. Extractor (`skill/cartolas/extractores/pershing.py`)

**Reconocimiento.** Todas las páginas, si el PDF es de la plantilla Pershing LLC (marca `Pershing LLC`, `Número de Cuenta:` y los títulos de sección). Lee igual los estados con broker BICE y Sura; no reconoce las cartolas Sura ni las BICE antiguas que mencionan "Patrimonio Custodia Pershing". Las secciones se ubican por su título y las columnas por coordenadas; los números van en formato EE.UU. y "No disponible" queda vacío.

**Decisiones por defecto:**

- Juego de archivos `*_PERSHING_<fecha>_V2.csv`. RUT y portafolio vacíos, como decidió Felipe para Pershing; `Cuenta` y `CuentaPershing` = el `Número de Cuenta` impreso, con producto base CUENTA INVERSION.
- SALDOS_CAJA: el saldo al cierre del money market (sweep) en USD.
- CUSTODIA_ACCIONES: acciones y ADR con producto `ACCIONES`, ETF con `ETF`; una fila por título sumando sus lotes. Nemotécnico = `Código de Identificación de Títulos`; instrumento = la descripción sin el sufijo `ISIN#`. Valorizado en USD (`Valor de Mercado`; para la acción en libras, su línea en USD). Precio promedio = base de costo / cantidad (vacío si no hay costo).
- Bonos: se leen y se cuadran, pero no tienen archivo de destino y quedan en el reporte como no exportados.
- MOVIMIENTOS_PERSHING: una fila por transacción, con el tipo de actividad literal en inglés (`MONEY FUND INCOME`, `SECURITY LIQUIDATED`…), cantidad y precio como vienen (vacíos en ingresos), monto con su signo impreso y producto según la clase del título en Tenencias (`MONEY MARKET`, `BONOS`, `ACCIONES`, `ETF`). No se duplican en MOVIMIENTOS_DE_CAJA: la sección Detalles del Fondo de Money Market solo se usa para cuadrar.
- Tipo de cambio: el estado no trae USD→CLP; se usa el de otra cartola con el mismo cierre (en la muestra, Larrainvial o Security) y queda anotado en el reporte. La tasa GBP→USD de la Tabla de Tipos de Cambio se usa solo para cuadrar.

**Resultado en los 6 estados:** 203 cuadraturas de §6, todas cierran, y en los 5 MSTAT el valor final de cada mes es el inicial del siguiente y los ingresos del año acumulan mes a mes. Se leen 17 posiciones (9 ETF, 3 acciones —una en libras—, 5 veces el mismo bono sin precio), 6 saldos de money market y 7 transacciones (6 `MONEY FUND INCOME` y 1 `SECURITY LIQUIDATED`), todas con producto y nemotécnico. Ningún título Pershing está en la tabla maestra, así que salen sin emisor.
