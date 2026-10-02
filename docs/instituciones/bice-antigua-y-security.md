# BICE viejas: inventario de formato

Alcance: los 12 PDF sueltos de `Training Data/BICE viejas/` (`Document_<n>.pdf` y `Abril_del_2026 (1).pdf`). No incluye la subcarpeta `Corredora de bolsa` (estados Pershing).

Privacidad: aquí no aparecen nombres, RUT, direcciones, emails, teléfonos, números de cuenta, folios ni montos reales. Los números son sintéticos y las cuentas se escriben como `<CUENTA>`, `<N>`, etc.

---

## 0. Resumen ejecutivo

- **Hay dos formatos en la carpeta, no uno.** Cada archivo trae una cartola **BICE Inversiones de formato antiguo** (parte A: A4 vertical, 4 a 7 páginas). En **10 de los 12 archivos** viene pegada a continuación, en el mismo PDF, una **"CARTOLA CONSOLIDADA DE INVERSIONES" de Valores Security S.A. CdB / AGF Security S.A.** (parte B: carta horizontal, 4 a 14 páginas). Las dos partes son del mismo cliente (mismo RUT) y del mismo mes. Solo `Abril_del_2026 (1).pdf` y `Document_639264687123145217.pdf` son BICE puras.
- **Período:** todos los archivos cubren **01-04-2026 al 30-04-2026**. Cada archivo tiene un solo cliente y un solo mes. La parte A tiene fecha de emisión 30-04-2026 y la parte B dice "Emisión: 26-05-2026 hh:mm:ss" o "27-05-2026 hh:mm:ss".
- **Duplicado:** `Document_639264713336299367.pdf` y `Document_639264718245976399.pdf` son **el mismo estado con el mismo cliente ficticio**. El texto y las palabras con coordenadas son idénticos página por página, y el render también. Los bytes solo difieren en el `/ID` del trailer PDF (62 bytes). Es un duplicado exacto que hay que descartar.
- **Cruce con Example Export:** hay 11 RUT distintos en 12 archivos. 10 de esos 11 RUT (es decir, 11 de los 12 archivos) aparecen en `RutCliente`. Falta el de `Document_639264687123145217.pdf`. **El export no sirve para validar los montos**: es del 2026-09-22 (cinco meses después) y solo incluye las cuentas del asesor (portafolios "AFITRADING"). Esas cuentas corresponden casi siempre a las **antiguas cuentas Security migradas a BICE**. **Sí sirve** como catálogo (nemotécnico, nombre largo, Emisor, Producto, TipoAPV/Régimen) y como chequeo parcial de cantidades de la parte B: unas 2/3 de las posiciones CFI de Security tienen el mismo nemotécnico y la misma cantidad en el export.
- **Cuadraturas:** los totales impresos cuadran con el detalle en las dos partes con tolerancia de redondeo ≤ 1 peso, o ≤ 0,01 en US$. Hay dos excepciones previsibles. En la parte A, "Ganancia/Pérdida" excluye los Depósitos a Plazo. En la parte B, el precio de los dividendos de CFI en USD no multiplica a un monto en CLP (detalle en §6).
- **Texto extraíble** en el 100 % de las páginas (no hay escaneos). **Recomendación:** pymupdf `get_text("words")` con columnas por coordenadas. pdfplumber `extract_tables` no sirve aquí (§8).

---

## 1. Archivos

| Archivo | Págs. | Parte A BICE (págs.) | Parte B Security (págs.) | Emisión B | Secciones parte A | Secciones parte B | RUT en export |
|---|---|---|---|---|---|---|---|
| `Abril_del_2026 (1).pdf` | 7 | 7 | — | — | Inv $, Inv US$, RV $, FM $, DAP US$, Dividendos, Caja $, Títulos $ | — | sí |
| `Document_639264679165525057` | 15 | 7 | 8 | 27-05-2026 | Inv $, Inv US$, DAP $, Caja $ (2 cuentas), Caja US$, Títulos $ (2 cuentas) | No prev.: FM CLP, CFI; Caja; Transacciones; Mov. caja | sí |
| `Document_639264679749897455` | 13 | 5 | 8 | 27-05-2026 | Inv $, RV $, FM $, Dividendos, Caja $ | No prev.: FM CLP, CFI; Caja; Transacciones; Mov. caja | sí |
| `Document_639264680219114118` | 11 | 5 | 6 | 27-05-2026 | Inv $, Inv US$, FM $, FM US$ | No prev.: FM USD, CFI; Caja | sí |
| `Document_639264681825825528` | 14 | 6 | 8 | 27-05-2026 | Inv $, FM $, Caja $, Títulos $ | No prev.: FM CLP, CFI; Caja; Transacciones; Mov. caja | sí |
| `Document_639264687123145217` | 4 | 4 | — | — | Inv $, FM $ | — | **no** |
| `Document_639264704609744529` | 18 | 7 | 11 | 26-05-2026 | Inv $, Inv US$, Inv APV $, RV $, FM $, FM US$, FM APV $, DAP $ | No prev. y prev.: FM CLP, CFI; Caja; Transacciones; Mov. caja | sí |
| `Document_639264707616629209` | 12 | 4 | 8 | 26-05-2026 | Inv US$, FM US$ | No prev.: FM CLP, FM USD, CFI; Caja; Transacciones; Mov. caja | sí |
| `Document_639264709325214359` | 8 | 4 | 4 | 26-05-2026 | Inv $, FM $ | Prev.: FM CLP (APV) | sí |
| `Document_639264710737711076` | 11 | 4 | 7 | 26-05-2026 | Inv APV $, FM APV $ | Prev.: CFI; Caja; Transacciones; Mov. caja | sí |
| `Document_639264713336299367` | 20 | 6 | 14 | 26-05-2026 | Inv $, FM $, Dividendos, Caja $, Títulos $ | No prev. y prev.: FM CLP, FM USD, Acciones nacionales, CFI; Caja (CLP/USD/EUR); Transacciones; Mov. caja | sí |
| `Document_639264718245976399` | 20 | 6 | 14 | 26-05-2026 | **duplicado exacto del anterior** | ídem | sí (mismo RUT) |

Datos generales:

- **Período:** todos los archivos dicen 01-04-2026 al 30-04-2026. En la parte A aparece como `Período: 01-04-2026 al 30-04-2026` y `Fecha Emisión: 30-04-2026`; en la parte B, como `Desde el 01-04-2026 al 30-04-2026 Emisión: dd-mm-yyyy hh:mm:ss`.
- **Clientes y meses:** cada archivo trae un solo cliente y un solo mes. La parte A y la parte B tienen el mismo RUT.
- **Moneda del reporte:** la parte A se divide por moneda (`$`, `US$`, `APV $`) y no trae tipo de cambio. La parte B valoriza todo en `$` y trae en cada página la cabecera `USD: x  €: y  UF: z`.
- **Página:** la parte A es A4 vertical (595 × 842 pt, rotación 0) con fuentes Poppins-Regular y Poppins-Bold. La parte B es carta horizontal **nativa** (792 × 612 pt, rotación 0, no está girada) con fuentes MyriadPro, Calibri y MicrosoftSansSerif. El texto anonimizado está en Helvetica o Helvetica-Bold.
- **Tamaño:** entre 143 y 412 KB. Cada archivo trae entre 7 y 35 imágenes (logos y gráficos); todo el texto es extraíble.
- **Metadatos:** están vacíos (sin productor ni fechas).
- **Nombres `Document_<n>`:** `n` son *ticks* .NET y se decodifican a fechas entre 2026-10-01 16:11 y 17:17. Son la hora en que se generaron los PDF; no tienen relación con el período. El duplicado se guardó unos 8 minutos después del original.
- **Duplicados o casi duplicados:** hay un solo par, y es exacto (ver §0). Los demás archivos tienen RUT y contenido distintos.

---

## 2. Estructura del documento

Para saber en qué parte está una página:

- **Parte B (Security):** la página mide 792 × 612, o el texto contiene `VALORES SECURITY S.A. CDB | AGF SECURITY S.A.`. Además, la numeración `Página N de M` vuelve a empezar en 1.
- **Parte A (BICE):** el pie dice `BICE Inversiones Corredores de Bolsa S.A. | BICE Inversiones Administradora General de Fondos S.A.`.

### Parte A: cartola BICE Inversiones (formato antiguo)

| Pág. | Título de página (negrita, y ≈ 91) | ¿Siempre? | Bloques |
|---|---|---|---|
| 1 | (sin barra de navegación) | siempre | Datos del cliente, Ejecutivo, Período; "Análisis del portafolio según exposición a renta variable"; "Resumen de sus inversiones"; gráfico de torta por moneda |
| 2.. | `DETALLE DE INVERSIONES EN $` | si hay activos en $ | "Resumen Cartera en $", "Resumen de Movimientos Caja en $", "Resumen de sus inversiones en $", "Dividendos del Período" (a veces) |
| .. | `DETALLE DE INVERSIONES EN US$` | si hay activos en US$ | lo mismo en US$, sin dividendos en la muestra |
| .. | `DETALLE DE INVERSIONES EN APV $` | si hay APV | lo mismo en APV $ |
| .. | `DETALLE DE CARTERAS` (1–2 págs.) | siempre | "Detalle Cartera Renta Variable en $", "Detalle Cartera Fondos Mutuos en $ / US$ / APV $", "Detalle Cartera Depósitos a Plazo en $ / US$" |
| .. | `DETALLE DE MOVIMIENTOS` (0–2 págs.) | solo si hubo movimientos | "Detalle de movimientos de Caja en $ / US$", "Movimientos de Títulos en $" |
| última | `GLOSARIO` | siempre | Definiciones (A)…(J), (1), (2), regímenes APV y notas |

- Desde la página 2 hay una barra de navegación fija con 7 pestañas: `RESUMEN DE SUS INVERSIONES | INVERSIONES EN $ | INVERSIONES EN US$ | INVERSIONES EN APV | DETALLE DE CARTERAS | DETALLE DE MOVIMIENTOS | GLOSARIO`. Siempre muestra las 7 pestañas, aunque la sección no exista, así que no sirve para saber qué secciones trae el archivo.
- Las páginas 2+ repiten Ejecutivo, Período y Fecha Emisión, pero **no** los datos del cliente. **El RUT de la parte A solo aparece en la página 1.**
- Cada sub-bloque se reconoce por su título exacto, en negrita y alineado a la izquierda (x = 8).
- Pie de página: `Para mayor información, consulte el glosario al final de su cartola.`, luego `<< < Página N de M > >>` y la línea "Mesa Central…".
- En la muestra no aparecen detalles de Renta Fija, Libreta de Ahorro, Forward, Venta Corta, Simultáneas, Operaciones en Tránsito ni Pershing. En la página 1 esas filas siempre son 0, pero las tablas de detalle podrían existir en otros clientes.

### Parte B: cartola consolidada Valores Security / AGF Security

Todas las páginas llevan la misma cabecera: el título, `VALORES SECURITY S.A. CDB | AGF SECURITY S.A.`, el período y la emisión, `Rut :`, `Nombre :`, `Dirección :`, `E-mail :` y la línea `USD: … €: … UF: …`.

| Pág. | Título | ¿Siempre? | Bloques |
|---|---|---|---|
| 1 | `CARTOLA CONSOLIDADA DE INVERSIONES` | siempre | "Resumen Inversión" (Activos Directos, Activos Bajo Mandato, Ahorro Previsional, Caja, TOTAL PATRIMONIO) y "Rentabilidades" |
| 2 | `CARTOLA CONSOLIDADA DE INVERSIONES` | siempre | "DETALLE DE INVERSIONES POR PRODUCTOS", "DETALLE DE INVERSIONES POR CLASE DE ACTIVOS" y perfil de riesgo |
| .. | `DETALLE DE INVERSIONES NO PREVISIONALES` | si hay | `FONDOS MUTUOS` → `FONDOS SECURITY - CLP` / `FONDOS SECURITY - USD`; `ACCIONES Y CFI` → `ACCIONES NACIONALES` / `CUOTAS` |
| .. | `DETALLE DE INVERSIONES PREVISIONALES` | si hay APV | los mismos sub-bloques |
| .. | `DETALLE DE INVERSIONES` | si hay caja | `CAJA` → `RESUMEN DE SALDOS EN CAJA` |
| .. | `DETALLE DE MOVIMIENTOS` | si hubo movimientos | `INFORME DE TRANSACCIONES`; `MOVIMIENTOS DE CAJA` → `CAJA: PESOS` / `CAJA: DOLAR` / `CAJA: EURO` |
| última | `RENTABILIDAD CLIENTE` | siempre | Gráfico y texto de metodología, sin datos útiles |

Las páginas 1, 2 y la última llevan al pie un párrafo legal en mayúsculas (`LA INFORMACIÓN CONTENIDA EN ESTA CARTOLA…`). El número de página (`Página N de M`) va a la derecha.

---

## 3. Detalle por sección

Convenciones numéricas en las dos partes:

- Separador de miles `.` y decimales `,`. Los negativos llevan `-` delante (p. ej. `-1.234.567`); no se usan paréntesis.
- Los porcentajes llevan `%` en la parte A (`12,34%`). En la parte B, las columnas `%` no traen el símbolo (`12,34`).
- Las celdas no llevan símbolo de moneda; la moneda sale del título del bloque o de la columna `MDA` / `CLP|USD|EUR`.

### Parte A (BICE)

**Página 1:**
- Etiquetas `Cliente:`, `Rut:`, `Email:`, `Teléfono` (la primera vez sin dos puntos) y `Dirección:`. Luego `Ejecutivo:`, `Email:`, `Teléfono:` y `Período:` / `Fecha Emisión:`.
- El RUT se imprime con puntos y guion: `<RUT>` con forma `NN.NNN.NNN-D`.
- "Resumen de sus inversiones": columnas `Activos | $ | US$ | APV ($)`.
  - Filas de activos: `Disponible en Caja`, `Depósitos a Plazo BICE (1)`, `Libreta de Ahorro`, `Acciones`, `Fondos Mutuos`, `Renta Fija (2)`, `Operaciones en Tránsito` y `Total Activos`.
  - `Otros Activos y Derivados`: `Forward (Resultado Neto)`, `Venta Corta`, `Patrimonio Custodia Pershing`.
  - `Pasivos`: `Simultáneas`, `Total Pasivos`.
  - `Patrimonio`.
- Formato: $ en enteros (`1.234.567`) y US$ con 2 decimales (`12.345,67`).
- La leyenda del gráfico (`Inversiones en $` y los % por clase) también es texto: hay que ignorarla.

**`Resumen Cartera en <M>`** (bloque izquierdo, x < 280):
- `Valor inicial al dd-mm-yyyy` (A), `Abonos/Retiros` (B), `Ganancia/Pérdida(1)` y `Valor Final al dd-mm-yyyy` (C).
- Las letras (A)…(C) son superíndices en otra línea, unos 3 pt más arriba. A veces quedan pegadas a la palabra (`30-04-2026(C)`, `Ganancia/Pérdida(1)`).
- Nota opcional: `(1): La Ganancia/Pérdida no considera activos por Depósitos a Plazo BICE y Libretas de Ahorro.` En US$ dice `…y Patrimonio Custodia Pershing.`

**`Resumen de Movimientos Caja en <M>`** (bloque derecho):
- Columnas `Monto <M> | Saldo <M>`.
- `Inicio` va en la columna Saldo. `Compras/Aportes` (D), `Ventas/Rescates` (E), `Dividendos y Otros` (F) y `Abonos/Retiros` (B) van en la columna Monto. `Final` va en Saldo.
- En US$ agrega la nota `El resumen de movimientos de caja no incluye Valores Extranjeros`.

**`Resumen de sus inversiones en <M>`:**
- Encabezado en 3 líneas: `Activos | Saldo al (G) dd-mm-yyyy | (**)Compras/ Aportes (H) | (**)Ventas/ Rescates (I) | (***)Cambio de Valor (2) | Saldo al (J) dd-mm-yyyy | Activo %`. La primera columna se rotula `Instrumento`.
- Hay filas de clase (`Disponible en Caja`, `Acciones`, `Fondos Mutuos`, `Depósitos a Plazo BICE`) seguidas de sus filas de instrumento:
  - Acciones: nemotécnico (acciones y también CFI, p. ej. `CFITINFR1B`, `ILC`).
  - Fondos Mutuos: nombre del fondo con su serie (p. ej. `BICE RENTA UF INSTITUCIONAL`, `FI BICE ALTERNATIVOS A`).
  - Depósitos a Plazo BICE: `DEPÓSITO A PLAZO INDEFINIDO RENOVABLE` / `DEPÓSITO A PLAZO FIJO`.
- `Disponible en Caja` solo trae G, J y %.
- El bloque cierra con `Total Activos` y `Patrimonio` (este último solo con G y J).

**`Dividendos del Período`:**
- Columnas: `Instrumento (****) | Fecha Límite | Fecha Pago | Cantidad Elegible | $ Divdo. unitario | Monto Dividendo`.
- En los fondos mutuos solo vienen Fecha Pago y Monto; las otras celdas quedan vacías, por eso hay que asignar las columnas por posición.
- El `$ Divdo. unitario` viene redondeado a entero, así que Cantidad × unitario no reproduce el monto.

**`Detalle Cartera Renta Variable en $`:**
- Columnas: `Instrumento | Cuenta Inversión | Cantidad Libre | Cantidad En Garantía | Saldo a Plazo | Precio Compra | Precio Último | Dividendos del Periodo | Valor de Mercado`.
- Cantidades enteras; precios con 2 decimales.
- Cierra con `Subtotal Cuenta Inversión <N>:` y `Subtotal Cartera Renta Variable:`.

**`Detalle Cartera Fondos Mutuos en $ | US$ | APV $`:**
- Columnas: `Instrumento | Cuenta Inversión | Cuenta Fondo | Valor Cuota | Saldo Cuotas Libres | Saldo Cuotas En Garantía | Saldo En $` (o `En US$` / `En APV $`).
- Valor cuota y cuotas con 4 decimales.
- En APV, la columna `Cuenta Inversión` trae el **régimen** (`DAPV-A`, `DAPV-B`) en vez de un número, y `Cuenta Fondo` trae el código de cuenta APV. Hubo un caso con número en ambas columnas y sin régimen.
- Subtotales: `Subtotal Cuenta Inversión <N>:` (o `Subtotal Cuenta Inversión APV:`) y `Subtotal Cartera Fondos Mutuos:`.
- **No trae precio promedio de compra.**

**`Detalle Cartera Depósitos a Plazo en $ | US$`:**
- Columnas: `Instrumento | Folio | Tipo | Moneda Origen | Fecha Captación | Fecha Vencimiento | Total Depósito A plazo | Total Vencimiento` (en US$ con `(*)`).
- `Tipo` = `RENOVABLE` o vacío; `Moneda Origen` = `$`, `UF` o `US$`.
- Subtotales: `Subtotal DEPÓSITO A PLAZO <TIPO>:` y `Subtotal Cartera Depósitos a Plazo:`. Ambos traen las dos columnas de total.
- Notas: `Los depósitos a plazo en UF son valorizados con el valor de la UF a la fecha de captación.` / `Los Depósitos a Plazo en Euro se muestran en moneda Dólar…`.

**`Detalle de movimientos de Caja en $ | US$`:**
- Un bloque por cuenta, con subtítulo `Cuenta Inversión: <N>`.
- Columnas: `Fecha | Folio | Tipo Movimiento | Instrumento | Abono | Cargo | Saldo`. **Abono va antes que Cargo.**
- Primera fila `SALDO INICIAL CAJA` (solo con saldo), última `SALDO FINAL CAJA`. Si no hubo movimientos aparece `SIN MOVIMIENTOS`.
- El folio viene con puntos de miles (`12.345.678`). Tipos vistos: `CARGO POR PAGO DE RESCATES $ OWP`, `ABONO ORIGINADO POR PAGO RESCATES $ OWP`, `ABONO POR COBRO DE INVERSION $ OWP`, `CARGO COMPROMISO DE INVERSION $ OWP`, `DIVIDENDO EN PESOS`. En los dividendos, `Instrumento` trae el nemotécnico.
- El saldo corrido puede ser negativo dentro del día.

**`Movimientos de Títulos en $`:**
- Un bloque por cuenta (`Cuenta Inversión: <N>`).
- Columnas: `Fecha | N°Ref. | Operación | Instrumento | P/B | Cantidad | Precio, TIR | Monto Neto`.
- Operaciones vistas: `INVERSION FM`, `RESCATE FM`, `INGRESO RV`, `RETIRO RV`.
- En fondos mutuos, el instrumento es `<FONDO> - CUENTA FONDO: <n>`. **Cuando no cabe se parte en una línea unos 7 pt arriba y otra unos 7 pt abajo de la fila de datos**, dentro de la columna x ≈ 170–350.
- Cuotas con 4 decimales; en RV, cantidad y precio con 3 decimales.
- P/B estuvo siempre vacío.

**Tablas que cruzan página:** en la parte A, la página siguiente repite el título del bloque y el encabezado. El subtotal puede caer en la página nueva (pasó en FM APV).

### Parte B (Security)

**Página 1, `Resumen Inversión`:**
- Columnas `Monto de Inversión ($) | %`.
- **Activos Directos:** `Acciones y CFI`, `Fondos Mutuos`, `Fondos de Inversión`, `Obligación por Simultáneas`, `Instrumentos de Deuda`, `Venta Corta`, `Instrumentos Extranjeros`, `Pactos`, `Forward`, `Patrimonio en Custodia Pershing`, `Total Activos Directos`.
- `Total Activos : <monto> (*)` va a la derecha, en x ≈ 530, en la misma línea que Total Activos Directos.
- **Activos Bajo Mandato:** `Portafolio Gestionado`, `Gestión Patrimonial` (negativo cuando hay comisión), `Total Activos Bajo Mandato`.
- **Ahorro Previsional:** `APV FFMM/DC`, `APV Flexible`, `APV Otros Instrumentos`, `Total Ahorro Previsional`.
- **Caja:** `Disponible Peso`, `Disponible Dólar`, `Disponible Euro`, `Dinero en Garantía`, `Cuentas por Pagar`, `Cuentas por Cobrar`, `Total Caja` (solo la caja no previsional), y luego `TOTAL PATRIMONIO`.
- A la derecha: `Rentabilidades | $ | UF | US$`, con filas `Año en Curso`, `Mes en Curso`, `Últimos 12 Meses`, `Últimos 30 Días`.

**Página 2:**
- `DETALLE DE INVERSIONES POR PRODUCTOS | SALDOS AL dd-mm-yyyy ($) | SALDOS AL dd-mm-yyyy ($)`: inicio y cierre de mes por producto, `Caja Total`, `Saldo Total`, `Patrimonio en Custodia Pershing`, `Saldo Total` y `TOTAL`.
- `DETALLE DE INVERSIONES POR CLASE DE ACTIVOS | INVERSIÓN NACIONAL ($) | INVERSIÓN INTERNACIONAL ($) | INVERSIÓN TOTAL ($)`: grupos `INSTRUMENTOS DE DEUDA`, `RENTA VARIABLE` y `OTROS ACTIVOS`, cada uno con `SubTotal`, y al final `SALDO TOTAL`. El texto del perfil comparte línea a la derecha.

**`FONDOS SECURITY - CLP`:**
- Columnas: `NOMBRE FONDO | MANDATO | NUMERO CUENTA | ES 57 BIS | NUMERO CUOTA | VALOR PROMEDIO COMPRA ($) | MONTO INVERTIDO ($) | VALOR CUOTA ACTUAL ($) | SALDO ACTUAL ($) | MAYOR O MENOR VALOR`.
- **En PREVISIONALES no existe la columna `ES 57 BIS`**: hay que detectar las columnas por encabezado.
- El nombre es corto, con serie (`MID TERM UF SERIE A`, `AGRESIVO EST SERIE I-APV`, `DOLAR MM SERIE A`).
- Cierra con `TOTAL`.

**`FONDOS SECURITY - USD`:** igual, con montos en `(USD)` y una columna extra `VALORIZACIÓN EN $`.

**`ACCIONES NACIONALES` / `CUOTAS`:**
- Columnas: `NOMBRE ACCION|CUOTA | MANDATO | NUMERO CUENTA | TOTAL | GARANTIAS / PRESTAMOS | SALDO A PLAZO | DISPONIBLES | PRECIO PROMEDIO COMPRA <MDA> | MONTO INVERTIDO ($) | PRECIO CIERRE <MDA> | [DEVOLUCION DE CAPITAL/ DIVIDENDO ($) solo en CUOTAS] | SALDO ACTUAL ($) | MAYOR O MENOR VALOR`.
- Cada precio va seguido de un token de moneda: `CLP`, `USD` o `EUR`.
- El nombre en CUOTAS es `<NEMO> - <NOMBRE TRUNCADO>` (unos 40 caracteres).
- Se repite una fila por cada cuenta APV.

**`RESUMEN DE SALDOS EN CAJA`:**
- Columnas: `CAJA | MANDATO | NUMERO CUENTA | SALDO EN CAJA SEGUN MONEDA | SALDO EN CAJA EN PESOS ($)`.
- Filas `En Peso`, `En Dolar`, `En Euro` (el saldo según moneda va con 2 decimales). Cierra con `TOTAL`.

**`INFORME DE TRANSACCIONES`:**
- Columnas: `FECHA OPERACIÓN | FECHA LIQUIDACIÓN | MANDATO | TIPO MOVTO | FORMA PAGO | NRO CUENTA | NUMERO OPERACIÓN | NÚMERO FACTURA | INSTRUMENTO | CANTIDAD/ CUOTAS | MDA | PRECIO/ VALOR CUOTA | MONTO | COMISIÓN | DERECHO | GASTOS | RETENCION/ IVA`.
- Fechas en formato `dd/mm/yyyy`.
- `TIPO MOVTO` viene truncado: `Inversion`, `Rescate`, `Dividendo`, `Compra`, `Venta`, `Canje De Cu`, `Disminucio`, `Emisión Lib`.
- `INSTRUMENTO` es el nemotécnico para CFI y el nombre truncado para FM (`FM SECURITY AGRESIVO ESTRATEGICO SE`).
- MONTO va con 2 decimales. FORMA PAGO estuvo siempre vacía; NÚMERO FACTURA solo aparece en Compra y Venta.

**`MOVIMIENTOS DE CAJA`:**
- Un bloque por cada combinación de cuenta y moneda, con título `CAJA: PESOS|DOLAR|EURO`.
- Columnas: `FECHA | MANDATO | NUMERO CUENTA | OPERACIÓN | DOCUMENTO | DESCRIPCIÓN | CARGO | ABONO | SALDO`. **Aquí Cargo va antes que Abono.**
- La primera fila es `Saldo Inicial`, fechada el último día del mes anterior. **No hay fila de saldo final.**
- `OPERACIÓN` es un código de 2 letras: `DA`, `DI`, `DC`, `FE`, `FX`, `MO`, `RG`.
- La `DESCRIPCIÓN` usa minúsculas y mayúsculas y lleva el nemotécnico dentro, p. ej. `Dividendo <NEMO> - Abono en Cuenta Mercantil`, `Disminucion de Capital <NEMO> - …`, `Cargo en Cuenta Corriente para Inversión en FM <FONDO>`, `Factura Ele. Compra Acciones`, `Factura Ele. Comisión APV`, `Operación Moneda Extranjera`, `Retiro`.

**Columna MANDATO:** en tenencias vale `N` o `S`; en movimientos, `N` o `A`. **No identifica APV con certeza**: un FM previsional apareció con `N`. Para clasificar como APV, usar el título `PREVISIONALES` / `NO PREVISIONALES`.

**Tablas que cruzan página:**
- Las de CFI siguen en la página siguiente sin repetir el encabezado: las filas vienen justo después de la cabecera fija.
- Las de movimientos de caja repiten el encabezado de columnas pero **no** el título `CAJA: <MONEDA>` ni el `Saldo Inicial`. El bloque continúa con la moneda anterior.
- Transacciones repite el encabezado.

---

## 4. Saldos y movimientos

| Tipo | Parte A (BICE) | Parte B (Security) |
|---|---|---|
| Caja (saldo) | `SALDO FINAL CAJA` de cada bloque "Detalle de movimientos de Caja", por cuenta y moneda. Si no hubo movimientos, solo existe el total `Disponible en Caja` en la página 1 y en "Resumen de sus inversiones", **sin cuenta** | `RESUMEN DE SALDOS EN CAJA`, por cuenta y moneda (saldo en moneda y en $) |
| Fondos mutuos | `Detalle Cartera Fondos Mutuos en $ / US$ / APV $` | `FONDOS SECURITY - CLP / USD` (NO PREV. y PREV.) |
| Acciones y CFI | `Detalle Cartera Renta Variable en $`. Los CFI aparecen aquí, en la clase "Acciones" | `ACCIONES NACIONALES` y `CUOTAS` (CFI y cuotas de FM de terceros, p. ej. `CFM-…`) |
| Depósitos a plazo | `Detalle Cartera Depósitos a Plazo en $ / US$` (**sin CSV destino en Example**) | — |
| Fondos de inversión BICE | En la muestra, `FI BICE ALTERNATIVOS A/R` aparece **dentro de Fondos Mutuos** | — |
| Renta fija, internacional, Pershing, derivados | Solo filas en 0 en la página 1 | Solo filas en 0 en "Resumen Inversión" y "Por productos" |
| Movimientos de caja | `Detalle de movimientos de Caja` (Fecha, Folio, Tipo Movimiento, Instrumento, Abono, Cargo, Saldo) | `MOVIMIENTOS DE CAJA` (Fecha, Mandato, Cuenta, Operación, Documento, Descripción, Cargo, Abono, Saldo) |
| Movimientos de títulos | `Movimientos de Títulos` (Fecha, N°Ref., Operación, Instrumento, P/B, Cantidad, Precio TIR, Monto Neto) | `INFORME DE TRANSACCIONES` (17 columnas, ver §3) |
| Dividendos | `Dividendos del Período` (informativo; el abono en caja aparece como `DIVIDENDO EN PESOS`. Los dividendos de FM se reinvierten como `INVERSION FM`) | Filas `Dividendo` en transacciones y `DI` en movimientos de caja |

---

## 5. Mapeo al formato de Example

**Columnas comunes:**
- **FechaProceso:** fecha de cierre del período (`30-04-2026` → `2026-04-30`). En el export es la fecha de proceso (un solo valor). Para movimientos hay que decidir si va la fecha de cada movimiento (recomendado) o el cierre del período.
- **RutCliente:** el `Rut:` de la página 1 (parte A) o el `Rut :` de cualquier página (parte B), sin puntos (`NNNNNNNN-D`). El dígito verificador `K` va en mayúscula.
- **Portafolio:** **no tiene fuente.** Ninguna de las dos partes menciona "PORTAFOLIO N°…" ni al asesor. En el export este campo es un nombre interno de BICE (`PORTAFOLIO N° k - AFITRADING ASESORIA FINANCIERA - <régimen>-S`). Hay que preguntar o dejarlo vacío.

### SALDOS_CAJA

| Columna | Parte A (BICE) | Parte B (Security) |
|---|---|---|
| Cuenta | `Cuenta Inversión: <N>` del bloque de caja. **Si no hubo movimientos no hay cuenta** | `NUMERO CUENTA` del resumen de saldos en caja (código Security; **no** coincide con el código de cuenta BICE del export) |
| ProductoBase | `CUENTA INVERSION`; en la sección APV $, por derivar (`APV FFMM`/`APV PRIME`) | Por derivar: no previsional → `CUENTA INVERSION`, previsional → `APV PRIME` (así quedaron las cuentas migradas en el export) |
| Producto | constante `CUENTAS CAJA` | ídem |
| MonedaValoracionPatrimonio | Sección `$` → CLP, `US$` → USD | `En Peso` → CLP, `En Dolar` → USD, `En Euro` → EUR (el export no trae ejemplos en EUR) |
| PatrimonioEnMonedaValoracion | `SALDO FINAL CAJA` | `SALDO EN CAJA SEGUN MONEDA` |
| patrimonioCLP | El mismo valor en $. **En US$ hace falta un tipo de cambio que la parte A no trae** | `SALDO EN CAJA EN PESOS ($)` |
| patrimonioUSD | Derivado (CLP / TC) | Derivado con el `USD:` de la cabecera |
| TipoAPV / DescripcionTipoRegimenTributario | Solo en APV: hay que pasar el régimen de la columna `Cuenta Inversión` a TipoAPV y Régimen (según el export, sufijo `-A` → `APORTE` y `-B` → `BONIFICACIÓN`) | **No tiene fuente** (el PDF no dice el régimen de cada cuenta APV) |
| EnTransito | `Operaciones en Tránsito` (página 1); siempre 0 en la muestra → `NO` | sin fuente → `NO` |
| TipoCambioUSD / TipoCambioEUR | **Sin fuente** | `USD:` / `€:` de la cabecera |

### SALDOS_FFMM

| Columna | Parte A | Parte B |
|---|---|---|
| Cuenta | `Cuenta Inversión` (o `Cuenta Fondo` en APV, donde Cuenta Inversión trae el régimen) | `NUMERO CUENTA` (código Security) |
| ProductoBase | `CUENTA INVERSION` o `APV FFMM` según la sección | Sección NO PREV / PREV |
| Producto | `FONDOS MUTUOS BICE`; los `FI BICE …` probablemente van como `FONDOS INVERSIÓN BICE` | `FONDOS MUTUOS BICE` (así quedaron los FM Security en el export) |
| Instrumento | `Instrumento`; coincide con el export en fondos BICE (p. ej. `BICE TESORERIA CLASICA`) | `FM SECURITY ` + nombre corto. Ojo: el corto dice `EST` y el largo `ESTRATEGICO` → conviene usar catálogo |
| NemotecnicoInstrumento | **Sin fuente** (catálogo, p. ej. `FM-TESORERIA-CLAS`) | La regla `FM-<NOMBRE>-SERIE <X>` acierta en 6 de 7 fondos de la muestra; falla `I. FUND S&P/CLX …`, que el export trunca. Usar catálogo |
| MonedaInstrumento | Según la sección ($ / US$ / APV $) | Según el bloque CLP / USD |
| Emisor | Sin fuente → constante `BICE INVERSIONES ADMINISTRADORA GENERAL DE FONDOS` | Ídem (en el export los FM Security tienen ese emisor) |
| Cantidad | `Saldo Cuotas Libres` + `En Garantía` | `NUMERO CUOTA` |
| PrecioCierreEnMonedaValoracion | `Valor Cuota` | `VALOR CUOTA ACTUAL` |
| PrecioPromedioCompra | **Sin fuente** | `VALOR PROMEDIO COMPRA` |
| PatrimonioEnMonedaValoracion / CLP / USD | `Saldo En $/US$/APV $`; para convertir falta TC | `SALDO ACTUAL` (CLP), `SALDO ACTUAL (USD)` y `VALORIZACIÓN EN $` |
| TipoAPV / Régimen | Columna Cuenta Inversión (régimen) | Sin fuente |
| EnTransito, TC | igual que SALDOS_CAJA | igual |

### CUSTODIA_ACCIONES

| Columna | Parte A | Parte B |
|---|---|---|
| Cuenta | `Cuenta Inversión` | `NUMERO CUENTA` |
| Producto | Derivado: nemotécnico `CFI*` → `CFI`, si no `ACCIONES`. `ETF` no se distingue → catálogo | Derivado: `CUOTAS` → `CFI` (o `ACCIONES`/`ETF` según el catálogo del export, que no es consistente); `ACCIONES NACIONALES` → `ACCIONES` |
| Instrumento | Sin nombre largo (solo nemotécnico) → catálogo | Nombre truncado → catálogo |
| NemotecnicoInstrumento | `Instrumento` | Texto antes de ` - ` |
| MonedaInstrumento | CLP (no aparece en el PDF) | Token después de `PRECIO CIERRE` (`CLP`/`USD`/`EUR`) |
| Emisor | **Sin fuente** → catálogo | **Sin fuente** → catálogo |
| Cantidad | `Cantidad Libre` + `En Garantía` + `Saldo a Plazo` | `TOTAL` |
| PrecioCierreEnMonedaValoracion | `Precio Último` | `PRECIO CIERRE`. En CFI en USD el precio está en USD pero el saldo en $; hay que decidir la moneda de valoración |
| PrecioPromedioCompra | `Precio Compra` | `PRECIO PROMEDIO COMPRA` |
| Patrimonio… | `Valor de Mercado` (en $) | `SALDO ACTUAL ($)`; en USD con el TC de la cabecera |

### MOVIMIENTOS_DE_CAJA

| Columna | Parte A | Parte B |
|---|---|---|
| Cuenta | `Cuenta Inversión: <N>` del bloque | `NUMERO CUENTA` |
| Producto / Instrumento | `CUENTAS CAJA` / `CAJA CLP` o `CAJA USD`. En dividendos, el export usa el producto del instrumento (`ACCIONES`/`CFI`) y el nemotécnico | Ídem; el nemotécnico se saca de la descripción con regex |
| nombreTipoMovimiento | `Tipo Movimiento`. Es el **mismo vocabulario que el export** (`CARGO POR PAGO DE RESCATES $ OWP`, `DIVIDENDO EN PESOS`, …) | `DESCRIPCIÓN` / código `OPERACIÓN`. **Otro vocabulario** → hace falta una tabla de equivalencias (p. ej. `FE` → `FACTURA COMPRA RV`) |
| Moneda | Según el título de la sección | Según `CAJA: PESOS/DOLAR/EURO` |
| abono / cargo | `Abono` / `Cargo` (en ese orden) | `ABONO` / `CARGO` (orden inverso) |
| TipoAPV / Régimen | ver SALDOS_CAJA | sin fuente |

### MOVIMIENTOS_FFMM y MOVIMIENTOS_BOLSA

| Columna | Parte A (`Movimientos de Títulos`) | Parte B (`INFORME DE TRANSACCIONES`) |
|---|---|---|
| Destino | `INVERSION FM`/`RESCATE FM` → FFMM; `INGRESO RV`/`RETIRO RV`/compras y ventas → BOLSA | `Inversion`/`Rescate` → FFMM; `Compra`/`Venta`/`Canje De Cu`/`Disminucio`/`Emisión Lib` → BOLSA. Hay que decidir qué hacer con las filas `Dividendo` (79 en la muestra) |
| Instrumento / Nemotécnico | FM: nombre antes de `- CUENTA FONDO:` (multilínea); RV: nemotécnico | Nemotécnico (CFI) o nombre truncado (FM) |
| NumeroRerferencia (solo FFMM) | `N°Ref.` sin puntos | `NUMERO OPERACIÓN` |
| NombreTipoMovimiento | `Operación` (mismo vocabulario que el export) | `TIPO MOVTO` truncado → tabla de equivalencias |
| Cantidad / PrecioTIR / MontoNeto | `Cantidad` / `Precio, TIR` / `Monto Neto` | `CANTIDAD/CUOTAS` / `PRECIO/VALOR CUOTA` / `MONTO` (ojo con la moneda, §7) |
| Moneda / MonedaInstrumento | `$` → CLP | `MDA` (poco confiable en CFI USD/EUR) |
| Emisor | sin fuente | sin fuente |

**MOVIMIENTOS_PERSHING:** no aplica. "Patrimonio Custodia Pershing" vale 0 en todos los archivos; los estados Pershing están en la subcarpeta excluida.

---

## 6. Cuadraturas probadas

Se probaron con un prototipo de pymupdf (palabras con coordenadas) sobre los **11 archivos únicos** (parte A) y los **9 únicos con parte Security** (parte B).

### Parte A (BICE)

| Cuadratura | Resultado | Tolerancia |
|---|---|---|
| Página 1: suma de activos = `Total Activos` (columnas $, US$ y APV) | 33/33 | exacta |
| Página 1: `Total Activos` + Otros − `Total Pasivos` = `Patrimonio` | 33/33 | exacta |
| Resumen inversiones: G + H − I + Cambio de Valor = J, por fila (sin DAP) | 52/52 | exacta |
| Suma de instrumentos = fila de clase (G, H, I, CV, J) | todas | exacta |
| Suma de clases = `Total Activos`; Σ % = 100 | todas | % ± 0,01 |
| `Total Activos` J = página 1 `Total Activos` de la moneda | 16/16 | exacta |
| Resumen Cartera A = Total G y C = Total J | 16/16 | exacta |
| **Resumen Cartera A + B + Ganancia/Pérdida = C** | 13/16 | Las 3 que fallan difieren exactamente en la variación de los Depósitos a Plazo, que la nota (1) excluye. Regla correcta: A + B + G/P + ΔDAP = C |
| Fila DAP: G + H − I + CV = J | 0/3 | Las renovaciones y capturas de DAP no figuran como compras y su CV vale 0. No usar esta regla para DAP |
| Resumen Mov. Caja: Inicio − D + E + F + B = Final | 16/16 | exacta |
| Mov. Caja: D = Total H, E = Total I, B (caja) = B (cartera) | 16/16 | exacta |
| FM: (cuotas libres + en garantía) × valor cuota = saldo | 36/36 | ≤ 0,49 $; ≤ 0,003 US$ |
| RV: (libre + garantía + plazo) × precio último = valor de mercado | 13/13 | ≤ 0,4 $ |
| Suma de filas = `Subtotal Cartera …` = J de la clase en Resumen (FM, RV, DAP) | 19/19 | exacta |
| Caja: saldo anterior + abono − cargo = saldo; último saldo = `SALDO FINAL CAJA` = `Disponible en Caja` | 26/26 y 7/7 | exacta |
| Títulos: cantidad × precio ≈ monto neto | 25/25 | ≤ 0,4 $ |
| Σ `Monto Dividendo` = F (`Dividendos y Otros`) | 3/3 | exacta |

### Parte B (Security)

| Cuadratura | Resultado | Tolerancia |
|---|---|---|
| Página 1: suma de cada grupo = su total; Directos + Mandato + Previsional = `Total Activos`; `Total Activos` + `Total Caja` = `TOTAL PATRIMONIO` | 9/9 en cada una | exacta |
| Por productos: suma = `Saldo Total` (ambas fechas); `TOTAL` = `TOTAL PATRIMONIO` | 18/18, 9/9 | ± 1 |
| Por clase: Nacional + Internacional = Total (207 filas); Σ SubTotal = `SALDO TOTAL` = `TOTAL PATRIMONIO` | todas | ± 1 |
| FM CLP: cuotas × valor cuota = saldo; cuotas × valor promedio compra = monto invertido; saldo − monto = mayor/menor | 14/14 cada una | ≤ 0,48 |
| FM USD: cuotas × valor cuota = saldo USD; saldo USD × `USD:` de la cabecera = `VALORIZACIÓN EN $` | 3/3 | ≤ 0,005 USD; ≤ 0,47 $ |
| Σ saldos FM = "Por productos" `Fondos Mutuos` | 8/8 | ± 2 |
| CFI/Acciones: `TOTAL` = garantías + plazo + disponibles | 163/163 | exacta |
| CFI/Acciones: `TOTAL` × precio cierre × TC de la cabecera (USD/EUR) = `SALDO ACTUAL ($)` | 163/163 | ≤ 0,5 |
| CFI/Acciones: saldo − monto invertido + devolución de capital/dividendo = mayor/menor | 163/163 | ± 1 |
| CFI en CLP: `TOTAL` × precio promedio de compra = monto invertido | 108/108 | ≤ 0,5 |
| Σ saldos CFI/Acciones = "Por productos" `Acciones y CFI` | 7/8 | El que falla difiere en 3 $ por acumular el redondeo de unas 60 filas. Usar ± 5 |
| Caja: saldo en moneda × TC = saldo $; suma = `TOTAL` | 22/22, 8/8 | ≤ 0,5 |
| Caja `TOTAL` = "Por productos" `Caja Total` | 6/8 | En uno la diferencia es exactamente `Cuentas por Cobrar` (página 1); en otro hay una diferencia pequeña sin explicar, probablemente por cobrar o pagar en APV |
| Movimientos de caja: saldo anterior − cargo + abono = saldo | 131/131 | exacta |
| Movimientos de caja: último saldo por (moneda, cuenta) = `RESUMEN DE SALDOS EN CAJA` | 21/21 | exacta |
| Transacciones: cantidad × precio ≈ monto | 105/126 | Las 21 que fallan son **todas `Dividendo` de CFI en USD**: el precio está en USD por cuota y el monto en CLP, aunque `MDA` dice `CLP` |

**Conclusión:** las sumas y productos permiten validar cada tabla de forma independiente. Tolerancias recomendadas:
- ± 1 $ por fila y ± 5 $ en totales de muchas filas.
- ± 0,01 en US$.
- Productos cuota × precio: ± 0,5 $.

---

## 7. Riesgos y particularidades

1. **Dos instituciones en un mismo PDF.** Hay que separar las partes por página (tamaño 792 × 612 o texto `VALORES SECURITY`). Felipe tiene que decidir si la parte Security se exporta, y cómo. Es otra institución, aunque sus posiciones hoy figuran en BICE (ver §10).
2. **Duplicado exacto** (`…713336299367` / `…718245976399`). Hay que deduplicar por contenido (texto o palabras), no por nombre ni por md5 del archivo, que difiere por el `/ID`.
3. **Texto anonimizado al final del orden de texto.** Son 5 spans Helvetica en la página 1 de la parte A y 4 spans Helvetica-Bold en cada página de la parte B. Algunos nombres mezclan texto original y texto reemplazado (sufijos `LTDA`/`SPA`, ciudad conservada). En la página `RENTABILIDAD CLIENTE` la dirección reemplazada se superpone al texto de metodología: hay que ignorar esa página. Usar siempre coordenadas.
4. **La parte A no trae tipo de cambio.** patrimonioCLP y patrimonioUSD de posiciones en US$ necesitan un TC externo (dólar observado del cierre) o el `USD:` de la parte B cuando existe.
5. **La parte A no da la cuenta de la caja cuando no hay movimientos.** El saldo solo aparece agregado en `Disponible en Caja`.
6. **APV en la parte A:** la columna `Cuenta Inversión` trae el régimen (`DAPV-A`/`DAPV-B`) y el número va en `Cuenta Fondo`. En la parte B no hay régimen.
7. **Orden de columnas distinto:** la parte A pone Abono y luego Cargo; la parte B, CARGO y luego ABONO. Si se interpreta por orden de texto se invierten los signos.
8. **Folios y N°Ref. con puntos de miles en la parte A** (`12.345.678`): parecen montos. Hay que asignarlos por columna.
9. **Descripciones multilínea:**
   - Parte A, Movimientos de Títulos: el instrumento se reparte entre una línea arriba y otra abajo de la fila, unos 7 pt de cada lado.
   - Parte A, Resumen Cartera: etiqueta y número desfasados unos 3 pt, con superíndices pegados.
   - Agrupar con una tolerancia fija de y ≤ 2,5 pt rompe estos casos. Hay que asociar por cercanía dentro de cada columna.
10. **Truncamientos en la parte B:**
    - nombres de CFI (unos 40 caracteres);
    - `TIPO MOVTO` (`Disminucio`, `Canje De Cu`, `Emisión Lib`);
    - instrumento FM en transacciones (sin serie).
    - Hay que mapearlos con nemotécnico o catálogo.
11. **`MDA` poco confiable en las transacciones de Security:**
    - Dividendo de CFI en USD: precio en USD y monto en CLP.
    - Compra de CFI en EUR: cantidad × precio = monto en EUR, aunque `MDA` dice `CLP` (en el movimiento de caja el cargo sale en CLP).
12. **El token `UF` puede ser parte de un nombre** (`FM SECURITY MID TERM UF`). No hay que tomarlo como moneda. El token de moneda real va entre dos números.
13. **Columnas que cambian según la sección:**
    - `ES 57 BIS` solo existe en FM no previsional.
    - `DEVOLUCION DE CAPITAL/ DIVIDENDO ($)` solo existe en `CUOTAS`.
    - En `Dividendos del Período` de fondos mutuos, la mitad de las celdas viene vacía.
    - Hay que detectar las columnas por encabezado.
14. **Filas de total y subtotal con forma de dato:** `Subtotal …`, `Total Activos`, `Patrimonio`, `TOTAL`, `SubTotal`, `SALDO TOTAL`, `SALDO INICIAL/FINAL CAJA`, `Saldo Inicial`. Hay que filtrarlas por etiqueta.
15. **Continuaciones de página distintas en cada parte:**
    - La parte A repite título y encabezado.
    - La parte B continúa las tablas de CFI sin encabezado.
    - Los movimientos de caja de la parte B no repiten `CAJA: <MONEDA>` ni el `Saldo Inicial`: hay que arrastrar la moneda y el saldo del bloque anterior.
16. **Ganancia/Pérdida no incluye los DAP.** Si se usa para validar, hay que sumar ΔDAP.
17. **Clasificación de producto:**
    - En la parte A, los CFI aparecen en la clase `Acciones`.
    - `FI BICE ALTERNATIVOS` aparece en `Fondos Mutuos`.
    - El export usa `CFI`/`ACCIONES`/`ETF`/`FONDOS INVERSIÓN BICE`.
    - Hace falta una regla o un catálogo.
18. **Sin destino en Example** para Depósitos a Plazo (parte A) ni para "Comisión Gestión Patrimonial" (parte B, negativa).
19. **Leyendas del gráfico de torta** en la página 1 de la parte A: son texto con porcentajes y no hay que tomarlas como datos.

---

## 8. Enfoque recomendado de extracción

**Herramienta:** pymupdf `page.get_text("words")`, agrupando en líneas por coordenada y. Razones:
- Recupera el texto anonimizado en su posición real, cosa que el orden de texto por defecto no hace.
- Los números están alineados a la derecha en columnas estables: el borde derecho `x1` de cada número cae dentro de ± 2 pt del borde derecho del encabezado.

**Por qué no pdfplumber `extract_tables`:**
- En la parte A, el sombreado de filas (cientos de `rects` y `lines` por página) fragmenta la tabla en trozos sin sentido.
- En la parte B, cada tabla sale como una sola celda con todo el texto.
- `pdftotext -layout` sirve para mirar y depurar, pero no para producción.

**Algoritmo:**
1. Clasificar cada página como parte A o B (tamaño de página o marcador de texto). Dentro de cada parte, reconocer secciones por el título exacto (§2 y §3).
2. En cada tabla, tomar los límites de columna del encabezado (borde derecho de cada palabra del encabezado) y asignar cada número por `x1`. El texto a la izquierda de la primera columna numérica es la descripción o el instrumento.
3. Casos especiales:
   - Resumen Cartera: emparejar número y etiqueta por cercanía en y (bloque izquierdo x < 280, bloque derecho x > 280).
   - Movimientos de Títulos: unir las líneas de la columna Instrumento a ± 8 pt de la fila con fecha.
   - Parte B: usar el token de moneda entre números como ancla de columnas.
4. Normalización:
   - Números: quitar `.` y cambiar `,` por `.`; el `%` aparte.
   - Fechas: `dd-mm-yyyy` o `dd/mm/yyyy` → ISO.
   - RUT: quitar puntos.
5. Validar con las cuadraturas de §6 antes de exportar; si una falla, marcar el archivo para revisión.
6. Deduplicar archivos por hash del texto normalizado.
7. Construir un catálogo nemotécnico/nombre → Instrumento, Nemotécnico, Emisor y Producto a partir de los CSV de Example (y de las cartolas BICE nuevas). Ninguna de las dos partes trae esos campos completos.

Ya hay un prototipo (fuera del repositorio) que aplica este enfoque y valida todas las cuadraturas de §6 sobre los 11 archivos únicos.

---

## 9. Extra: diferencias con la cartola BICE nueva

Se compararon 2 PDF de `BICE nuevas` (septiembre de 2026), sin estudiarlos a fondo.

| Aspecto | BICE vieja (parte A) | BICE nueva |
|---|---|---|
| Página | A4 **vertical** 595 × 842 | **Horizontal** 842 × 595 |
| Cabecera | `Cliente/Rut/Email/Teléfono/Dirección`, `Ejecutivo`, `Período: dd-mm-yyyy al dd-mm-yyyy`, `Fecha Emisión: dd-mm-yyyy` (cliente solo en la página 1) | "Información del cliente" (Nombre, Rut, Dirección, Comuna, Ciudad); "Información del reporte" (`Fecha de Emisión: 01 de Octubre de 2026`, Moneda del Reporte, **Tipo de Cambio Reporte `x (CLP/USD)`**, `Período entre el dd/mm/yyyy al dd/mm/yyyy`) |
| Organización | **Por moneda** ($, US$, APV $) con Resumen Cartera (A, B, C), Resumen de Movimientos Caja y tabla Saldo inicial / Compras / Ventas / Cambio de valor / Saldo final por instrumento | **Por clase de activo** (Caja, Renta Fija Nacional, RV Nacional/Internacional, Balanceados BICE, Activos Alternativos), separando "Previsional (APV)"; "Resumen por tipo de cuentas" con **`PORTAFOLIO N° …`** y "Número cuenta" |
| Detalle FM | Cuenta Inversión, Cuenta Fondo, Valor Cuota, Cuotas Libres / En Garantía, Saldo | Número cuenta, Número Cuotas, **Precio Prom. Compra**, Valor Cuota Actual, Valor de mercado, Rentabilidad, % de activo (+ Dividendos en FI) |
| Caja | Saldo por cuenta solo a través de los movimientos (inicial, final, corrido) | "Detalle de Caja" por portafolio (Pesos, Dólar, Euro) |
| Movimientos de caja | Fecha, Folio numérico con puntos, Tipo, Instrumento, **Abono, Cargo, Saldo**; bloques por cuenta y moneda | Fecha, Número cuenta, Folio con prefijo (`BCS_…`), Tipo, **Moneda**, Cargo, Abono (sin saldo) |
| Movimientos de títulos | Fecha, N°Ref., Operación, Instrumento (con `- CUENTA FONDO: n`, multilínea), P/B, Cantidad, Precio TIR, Monto Neto | Fecha, Número cuenta, Nº Referencia (`FD_…_1` o numérico), Tipo de operación, Instrumento, Moneda, Cantidad, Precio, Monto |
| Formato de celdas | Números sin símbolo de moneda | `$ 1.234.567`, `US$ 1.234,56`, `USD 1,2345` |
| Dividendos | Tabla "Dividendos del Período" | Columna "Dividendos" por posición |
| Instrumentos ex-Security | En una cartola Security aparte (parte B) | Integrados: `FM SECURITY …`, CFI Ameris/Toesca/etc. en portafolios AFITRADING |
| Paginación | `Página N de M` con flechas | `Página 0N` |

Uno de los clientes (el de `Document_639264679165525057`) también tiene una cartola BICE nueva de septiembre en `BICE nuevas`. Sirve para ver el mismo cliente en los dos formatos, aunque con 5 meses de diferencia.

---

## 10. Extra: cruce con Example Export y utilidad para validar

- **RUT:** de los 11 RUT distintos, 10 están en `RutCliente` (los 12 archivos menos `Document_639264687123145217`). Ese archivo es una cartola BICE pura, con solo fondos mutuos en $.
- **Qué contiene el export:** es BICE al 2026-09-22 y solo trae portafolios "AFITRADING". Por RUT tiene sobre todo:
  - FM `FM SECURITY …` (Producto `FONDOS MUTUOS BICE`);
  - CFI y acciones que antes estaban en Security;
  - cuentas `APV PRIME` con TipoAPV y régimen.
- **Hipótesis bien apoyada:** las cuentas Security de abril se migraron a BICE como portafolios AFITRADING. Lo que se midió:
  - 162 de 180 posiciones de la parte B (Security) tienen el mismo nemotécnico o nombre en el export para el mismo RUT, y **123 de 180 tienen además la misma cantidad**.
  - En la parte A (BICE), solo 4 de 49 posiciones aparecen por nombre y ninguna con la misma cantidad: las cuentas BICE propias (sin asesor) no están en el export.
  - En el cliente del duplicado, dos cuentas APV de Security aparecen **fusionadas** en una sola cuenta APV PRIME de BICE: la suma de cantidades coincide. La correspondencia de cuentas no es 1:1.
- **Sirve para validar:**
  - el formato de RUT;
  - un catálogo nemotécnico → `Instrumento`, `NemotecnicoInstrumento`, `Emisor`, `Producto`, `MonedaInstrumento`;
  - el vocabulario de `nombreTipoMovimiento` y `NombreTipoMovimiento`, que coincide con el de la parte A;
  - la regla régimen → TipoAPV y DescripcionTipoRegimenTributario;
  - como chequeo blando, las **cantidades de CFI de la parte B que no cambiaron** (unas 2/3 coinciden exactamente).
- **No sirve para validar:**
  - Saldos, precios, patrimonio, TC, ni ningún movimiento: el export tiene otra fecha y sus movimientos son todos del 2026-09-22.
  - `Cuenta` y `Portafolio`, que en el export son códigos BICE posteriores a la migración y no tienen equivalente en estos PDF.
  - Las posiciones de la parte A, que casi no aparecen en el export.

### Preguntas abiertas para Felipe

1. ¿Se exporta la parte Security? ¿Con qué `Cuenta`/`Portafolio`, si el PDF solo trae los códigos Security?
2. ¿De dónde sale el tipo de cambio para la parte A (dólar observado del 30-04 o el `USD:` de la parte B)?
3. En los movimientos, ¿`FechaProceso` debe ser la fecha del movimiento o el cierre del período?
4. ¿Dónde van los Depósitos a Plazo y la "Comisión Gestión Patrimonial", que no tienen CSV destino?
5. ¿Las filas `Dividendo` del informe de transacciones de Security van a MOVIMIENTOS_BOLSA, o se omiten porque ya aparecen como caja?

---

## 11. Extractor de la parte A (`skill/cartolas/extractores/bice_antigua.py`)

**Reconocimiento.** `paginas(doc)` toma las páginas verticales del principio del PDF que llevan el pie de BICE Inversiones, si la portada trae "Resumen de sus inversiones". Las páginas apaisadas que siguen son de la cartola Security y las lee `security.py`. Cada parte sale como una cartola aparte en el reporte.

**Lectura.** Palabras con coordenadas (`pdf.leer_palabras`), incluido el texto blanco de los títulos de bloque, agrupadas en líneas; los superíndices de 5 pt se descartan. Cada bloque se reconoce por su título exacto (§3) y cada celda se asigna a la columna cuyo encabezado termina más cerca de su borde derecho, porque los números van alineados a la derecha. Si aparece una tabla que el extractor no conoce (renta fija, libreta de ahorro, etc.), queda un aviso en el reporte.

**Qué se exporta:**

| Archivo | Fuente | Notas |
|---|---|---|
| Cuentas | `Cuenta Inversión` (0–9 → CUENTA INVERSION); en APV, `Cuenta Fondo` (80–85) | Producto base, tipo de APV y régimen salen de la tabla de cuentas (`catalogo.tipo_cuenta`). `Portafolio` queda vacío: la cartola no lo trae |
| SALDOS_CAJA | `SALDO FINAL CAJA` de cada bloque de movimientos de caja, por cuenta y moneda | Si una moneda tiene caja pero no movimientos, se asigna a la única cuenta de inversión de la cartola; si hay más de una, queda en el reporte sin exportar |
| SALDOS_FFMM | `Detalle Cartera Fondos Mutuos en $ / US$ / APV $` | Cantidad = cuotas libres + en garantía; precio = valor cuota; sin precio promedio de compra (la cartola no lo trae). Los `FI BICE …` van con producto FONDOS INVERSIÓN BICE |
| CUSTODIA_ACCIONES | `Detalle Cartera Renta Variable` | Cantidad = libre + en garantía + a plazo. Nombre largo, emisor y producto de la tabla maestra por nemotécnico |
| MOVIMIENTOS_DE_CAJA | `Detalle de movimientos de Caja` | Tipo tal como viene (es el vocabulario del export). En dividendos, el instrumento es el nemotécnico y el producto, el del instrumento |
| MOVIMIENTOS_FFMM / _BOLSA | `Movimientos de Títulos` | `… FM` a fondos mutuos con `N°Ref.` como referencia; `… RV` a bolsa. El instrumento partido en dos líneas se une |
| No se exporta | Depósitos a plazo, resúmenes, dividendos del período | Los depósitos quedan en el reporte como "sin archivo de destino" |

**Tipo de cambio.** La parte A no lo trae. El programa usa el `USD:` de la cartola Security del mismo PDF y, si el PDF no trae parte Security, el de otra cartola con el mismo cierre; en ambos casos lo anota en el reporte.

**Cuadraturas propias** (además de cantidad × precio en posiciones y movimientos, que hace `validar.py`):

- Portada: suma de activos = Total Activos, y Total Activos + otros − pasivos = Patrimonio, en $, US$ y APV.
- Resumen por moneda: saldo inicial + compras − ventas + cambio de valor = saldo final en cada fila (salvo depósitos a plazo); suma de instrumentos = fila de su clase; suma de clases = Total Activos; Total Activos = el de la portada.
- Resumen de cartera: valor inicial y final = los del resumen; inicial + abonos/retiros + ganancia + variación de depósitos a plazo = final.
- Resumen de movimientos de caja: inicio − compras + ventas + dividendos + abonos = final; compras y ventas = las del resumen; abonos = los del resumen de cartera; final = disponible en caja = suma de los saldos finales del detalle.
- Detalle de carteras: cada `Subtotal Cuenta Inversión` y `Subtotal Cartera` = suma de sus filas, y el subtotal de la cartera = la clase en el resumen.
- Movimientos de caja: saldo anterior + abono − cargo = saldo en cada fila, y el último = `SALDO FINAL CAJA`.
- Dividendos del período = "Dividendos y otros" del resumen de caja.

**Resultado en las 11 cartolas distintas** (12 PDF con un duplicado exacto, que el programa detecta por el texto y no procesa dos veces): todas las cuadraturas cierran (542 propias más las comunes). Se leen 60 posiciones (33 fondos mutuos, 3 FI BICE, 8 acciones, 5 CFI y 11 depósitos a plazo), 4 saldos de caja, 26 movimientos de caja y 25 de títulos, los mismos conteos que el prototipo de §6.

**Tabla maestra.** Las 13 acciones y CFI se encuentran por nemotécnico. Ninguno de los fondos mutuos BICE de estas cartolas está en el export de ejemplo, que es de portafolios AFI de septiembre, así que salen sin nemotécnico ni emisor y con un aviso en el reporte.
