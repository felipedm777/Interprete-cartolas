# BICE Inversiones: cartolas "nuevas" (formato septiembre 2026). Inventario de layout

Fuente: `Training Data/BICE nuevas/` (20 PDF `CARTOLA_10038_202609_<RUT>.pdf`), cruzado contra `Example Export/` (export BICE, portafolio 10038, `FechaProceso` 2026-09-22).

Convenciones de este documento:
- **#NN** = posición del archivo en orden alfabético de nombre (`ls | sort`, #01 a #20). No se listan los nombres de archivo porque contienen el RUT.
- Todos los montos y cantidades de ejemplo son **sintéticos** (1.234.567, 12,3456…). `<RUT>`, `<NOMBRE>` y `<CTA_PERSHING>` reemplazan datos de cliente.
- Las cifras de cuadratura son **conteos de casos**, no montos.

Resumen corto:
- Formato muy regular, nativo digital (Poppins), con una tabla por clase de activo y por tipo de producto. No hay líneas de tabla: pdfplumber no detecta tablas, así que hay que leer palabras con coordenadas.
- El PDF trae casi todo lo que piden SALDOS_FFMM, CUSTODIA_ACCIONES y SALDOS_CAJA. **No trae** `NemotecnicoInstrumento` (salvo CFI-xxx y acciones), `Emisor`, `TipoCambioEUR` ni `EnTransito`. Hay que derivarlos con una tabla maestra.
- Contra el CSV del 22-09: **cantidades y PPC coinciden exacto** en 168/170 y 163/170 posiciones. Precio y valor difieren por fecha (30-09 contra 22-09), salvo en los FI cuyo valor cuota no cambió. Todas las diferencias de caja y posiciones se explican por la fecha, por el perímetro del export (solo portafolios "AFITRADING", sin Pershing) o por convenciones del CSV.

---

## 1. Archivos

| Atributo | Valor |
|---|---|
| Cantidad | 20 PDF, todos de un solo cliente (persona natural o jurídica) |
| Páginas | 6 a 15 por archivo (217 en total). Las de 6 páginas (#11, #18) solo tienen Renta Fija Nacional |
| Período | "Período entre el 01/09/2026 al 30/09/2026" (todos) |
| Fecha de emisión | "01 de Octubre de 2026" (todos) |
| Moneda del reporte | CLP; "Tipo de Cambio Reporte: 972,6 (CLP/USD)" (todos) |
| Página | A4 apaisada, 842 × 595 pt, `rotation = 0` en todas las páginas |
| Texto | Extraíble. Fuentes `poppins` / `poppinsb` (Poppins regular/bold), `ZapfDingbats` (viñetas del glosario) y `Helvetica` (solo el texto reemplazado por la anonimización) |
| Escaneo | No. Ninguna página es imagen |
| Metadatos | Vacíos (sin producer/creator/fecha; probablemente los borró el anonimizador) |
| Duplicados | No hay. MD5 distintos. La similitud máxima entre archivos (Jaccard de líneas con números, sin portada ni glosario) es 0,27, y se explica por precios compartidos |
| RUT | El RUT del nombre de archivo es el de la portada en los 20 (portada `12.345.678-9` → archivo `12345678-9`) |

Texto anonimizado (Helvetica): solo aparece en la **portada** (página 0): Nombre, Rut, Dirección, Comuna, Ciudad (en algunos casos la ciudad quedó en Poppins) y el nombre del ejecutivo. En el orden de texto va **al final de la página**, así que se lee por coordenadas (ver §3.1). Las páginas de detalle no tienen texto reemplazado: el "Número cuenta" de BICE es un índice de subcuenta (0, 1, 2…, 80, 90), no un número identificador. La cuenta Pershing sí es un código alfanumérico propio del cliente (`<CTA_PERSHING>`, 3 letras + 6 dígitos).

## 2. Estructura del documento

Cada página tiene el título en bold 17 pt en (25, 20), "BICE INVERSIONES" arriba a la derecha y "Página NN" (2 dígitos) en y≈53. La portada no lleva número y "Resumen de tus inversiones" es la Página 01. El título de página es la primera línea de `page.get_text()` y sirve como identificador de sección.

Orden fijo de secciones (una página por sección, salvo que se indique otra cosa):

| # | Título de página | Aparece en | Notas |
|---|---|---|---|
| 0 | (portada) "CARTOLA" / "BICE INVERSIONES" | 20/20 | Información del cliente, del reporte y del ejecutivo |
| 1 | Resumen de tus inversiones | 20/20 | 3 variantes (ver §3.2) |
| 2 | Resumen por tipo de cuentas | 20/20 | Portafolios agrupados por tipo de cuenta |
| 3 | Resumen por Clase de Activos | 20/20 | Tabla a la izquierda y gráficos a la derecha |
| 4 | Detalle de Caja | 15/20 | Solo si hay saldo de caja distinto de 0 |
| 5 | Detalle de Renta Fija Nacional | 17/20 | |
| 6 | Detalle de Renta Fija Internacional | 5/20 | |
| 7 | Detalle de Renta Variable Nacional | 4/20 | |
| 8 | Detalle de Renta Variable Internacional | 10/20 | |
| 9 | Detalle de Balanceados BICE | 5/20 | |
| 10 | Detalle de Activos Alternativos | 17/20 | |
| 11 | Movimiento de Caja | 17/20 | Siempre 1 página en la muestra |
| 12 | Movimiento de Títulos | 18/20 | 1 a 3 páginas: el título y el encabezado se **repiten** en cada página |
| 13 | Glosario | 20/20 | Texto fijo y siempre la última página. No tiene datos |

Dentro de cada página de detalle:
- **Bloque** (bold 7,0 pt en x≈25): "Renta Fija Nacional" o "Renta Fija Nacional - Previsional (APV)". El sufijo " - Previsional (APV)" está en regular y es un span aparte en la misma línea. Bloques APV vistos: RFN (4 archivos), RVI (3), Alternativos (5) y Balanceados (4).
- **Tabla** (bold 6,2 pt en x≈25, en la misma banda que los encabezados de columna en bold 6,2): el nombre de la tabla ocupa la columna del instrumento.
- **"Total"** (bold 6,2 en x≈25): uno por **bloque**, después de su última tabla. Totaliza todas las tablas del bloque, no cada tabla.

Tablas vistas por sección (en paréntesis, número de archivos):

| Sección | Tablas |
|---|---|
| Renta Fija Nacional | Fondos De Inversión (10), Fondos Mutuos (17), Intermediación Financiera (1) |
| Renta Fija Internacional | Bonos Internacionales (1, Pershing), Fondos Mutuos (5), Notas (1, Pershing) |
| Renta Variable Nacional | Acciones (1), ETF (1), Fondos De Inversión (2), Fondos Mutuos (1) |
| Renta Variable Internacional | ETF (1), Fondos De Inversión (8), Fondos Mutuos (1) |
| Balanceados BICE | Fondos Mutuos (5) |
| Activos Alternativos | CFI (17), Acciones (5; ¡son cuotas de FI!), Fondos Inversión Bice (1) |

Tipos de cuenta (filas en negrita de "Resumen por tipo de cuentas" y "Detalle de Caja"): "Cuenta de Inversión" (18), "APV Prime" (5), "APV FFMM" (4) y "Mercado Internacional Pershing" (1, #04).

## 3. Detalle por sección

### 3.1 Portada
Hay dos columnas: etiquetas en x≈480 y valores en x≈634.
- "Información del cliente": `Nombre:`, `Rut:`, `Dirección:`, `Comuna:`, `Ciudad:`. La pila de etiquetas está alineada abajo (Ciudad en y≈320) y sube cuando el nombre o la dirección ocupan 2 líneas (#06, #13). Si el valor cabe en una línea, queda a la misma altura que su etiqueta. Si ocupa 2 líneas, la segunda cae a la altura de una fila sin etiqueta propia. Regla robusta: cada línea de valor (x≈634) pertenece a la etiqueta más cercana que esté a su altura o sobre ella. El Rut está en la misma y que su etiqueta, con formato `12.345.678-9`.
- "Información del reporte": `Fecha de Emisión:` ("01 de Octubre de 2026"), `Fecha del Reporte:` ("Período entre el dd/mm/aaaa al dd/mm/aaaa"), `Moneda del Reporte:` ("CLP"), `Tipo de Cambio Reporte:` ("972,6 (CLP/USD)"), `Reporte emitido por:`.
- "Información del ejecutivo": nombre (Helvetica), Mail, Teléfono. No se usa.

### 3.2 Resumen de tus inversiones (Página 01)
Fecha de corte "30 de septiembre de 2026". Patrimonio en bold 20 pt (`$1.234.567`, sin espacio tras `$`). Perfil de inversionista, "Nivel de exposición actual/máximo" y gráficos de dona ("Distribución por moneda" y "Distribución por clase de activo", con leyendas tipo `Pesos $1.234.567` y `RF. Nacional $1.234.567`, en 6,3 pt). Las etiquetas de 4,3 pt son rótulos internos del gráfico y hay que ignorarlas.
Hay tres variantes del panel derecho:
- **A** (15 archivos, personas naturales): "Activos" → `Inversiones Previsionales` / `Inversiones No Previsionales`.
- **B** (4 archivos, #14–#17, personas jurídicas): "Balance" → `Activos` / `Pasivos` / `Patrimonio`.
- **C** (#18): además trae `Patrimonio al cerrar agosto`, `Abonos de septiembre`, `Retiros de septiembre`, `Rentado en septiembre`, el gráfico "Variación de tu patrimonio en 12 meses" (eje en millones "$ 1.234 M"…, meses "Oct 25"…"Sep 26") y "Flujo patrimonial acumulado año 2026" (`Saldo Inicial`, `Aportes/Retiros`, `Saldo Final`, `Rentado`). Parece ser el único cliente con historia previa; el resto se migró desde Valores Security el 14-09 (ver §4).
Esta página no aporta filas a los CSV. Solo sirve para validar totales.

### 3.3 Resumen por tipo de cuentas (Página 02)
Encabezado: `Número cuenta` | `Activos` | `Pasivos` | `Patrimonio` | `Porcentaje de activo`.
Filas: grupo en bold (tipo de cuenta con subtotal) → portafolios en regular → `Total` en bold. Pershing muestra cada celda en 2 líneas (`$ 1.234.567` encima y `US$ 1.234` debajo). **Pasivos siempre vacío** en la muestra: un saldo de caja negativo se resta dentro de Activos (#14).
Etiquetas de portafolio vistas (el texto exacto es el `Portafolio` del CSV):
- `PORTAFOLIO N° k - AFITRADING ASESORIA FINANCIERA - S` (cuentas 0–9)
- `PORTAFOLIO N° 1 - AFITRADING ASESORIA FINANCIERA - DAPV-B-S` (cuentas 80 y 90)
- `PORTAFOLIO 57 BIS 0 - AFITRADING ASESORIA FINANCIERA - S`, `PORTAFOLIO - 1 - AFITRADING ASESORIA FINANCIERA`
- **Sin "AFITRADING"** (otros mandatos, que no salen en el export 10038): `PORTAFOLIO N° 1`, `PORTAFOLIO N° 2`, `PORTAFOLIO - 0`, `PORTAFOLIO N° 1 - DAPV-B` (cuenta 80)
- Pershing: `PORTAFOLIO N° 1 - <CTA_PERSHING>` con Número cuenta = `<CTA_PERSHING>`

### 3.4 Resumen por Clase de Activos (Página 03)
Tabla en x < 420. A la derecha hay gráficos cuyas etiquetas se mezclan en el orden de texto, así que hay que recortar por x.
Encabezado: `Pesos` | `Dólar` | `APV` | `Porcentaje de activo`. **La columna APV no existe en la variante B** (personas jurídicas).
Filas: clase en bold (Caja, Renta Fija Nacional, Renta Fija Internacional, Renta Variable Nacional, Renta Variable Internacional, Alternativos, Balanceados Bice), subtipos en regular (Fondos Mutuos, Fondos De Inversión, Acciones, ETF, Notas, Bonos Internacionales, Intermediación Financiera) y `Total`.
- `Pesos` y `APV` en CLP (`$ 1.234.567`). APV ya trae convertido a CLP lo que esté en USD.
- `Dólar` en USD **con 2 decimales** (`US$ 1.234,56`). Es la **única fuente con centavos para la caja en USD no previsional**. Para CFI el valor llega ya redondeado (`US$ 1.234,00`).
- Una posición de pocos pesos puede no aparecer: #13 tiene RFN de valor mínimo en el detalle, pero no hay fila RFN en esta tabla.

### 3.5 Detalle de Caja
Encabezado: `Caja` (bold 8,2, nombre de tabla) | `Número cuenta` | `Pesos` | `Dólar` | `Euro` | `Valor de Mercado` | `Porcentaje de activo`.
Filas: grupo (bold, con subtotales) → portafolio (regular) → `Total`.
- Celda Dólar en 2 líneas: `$ 1.234.567` (equivalente CLP a 972,6) encima y `US$ 1.234` (USD **redondeado a entero**, fuente 6,0) debajo, centrada en la fila.
- **Euro siempre vacío** en la muestra.
- Negativos: `$ -1.234.567` y `US$ -1.234` (#14, sobregiro USD). En la fila `Total` de #14 el Dólar aparece como `$ -1.234`, sin línea US$: es un error del PDF (USD con signo `$`).

### 3.6 Tablas de posiciones (todas las "Detalle de …" excepto Caja)
Encabezados exactos (las etiquetas de 2 líneas se leen de arriba hacia abajo):

| Tabla | Columnas |
|---|---|
| Fondos Mutuos | Número cuenta · Número Cuotas · Precio Prom. Compra · Valor Cuota Actual · Valor de mercado · Rentabilidad · Porcentaje de activo |
| Fondos De Inversión / CFI / ETF / Fondos Inversión Bice / Acciones (en Alternativos) | Número cuenta · Número Cuotas · Precio Prom. Compra · Valor Cuota Actual · Valor de mercado · Dividendos · Rentabilidad · Porcentaje de activo (en RFN, "Rentabilidad" va antes de "Dividendos") |
| Acciones (RV Nacional) | Número cuenta · Acc. Libres · Acc. en Gtía · Saldo a Plazo · Precio Prom. Compra · Precio Actual · Valor de mercado · Dividendos · Rentabilidad · Porcentaje de activo |
| Intermediación Financiera | Número cuenta · Fecha de compra · Fecha de vencimiento · Tasa de compra · Nominales · Valor de mercado · Porcentaje de activo |
| Bonos Internacionales | Número cuenta · Fecha de compra · Nominales · Valor de mercado · Porcentaje de activo |
| Notas | Número cuenta · Cantidad · Precio Prom. Compra · Precio Actual · Valor de mercado · Rentabilidad · Porcentaje de activo |

Particularidades de fila:
- **Nombre del instrumento** a la izquierda (x≈25), con 3–5 espacios iniciales. Se conservan **espacios dobles internos** (p. ej. `FI AMERIS  DOVER STREET XI  SERIE B`) idénticos al `Instrumento` del CSV. pymupdf los respeta; `pdftotext -layout` los colapsa.
- Filas de Fondos De Inversión en RFN: el nombre (6,0 pt) queda ~6 pt **sobre** la línea de números y debajo va una línea de categoría en 5,0 pt `FONDOS DE INVERSIÓN`.
- Nombres largos en 2 líneas (6,0 pt) **alrededor** de la línea de números, por ejemplo `FI ETF SINGULAR GLOBAL CORPORATES SERIE` / `SIN SERIE`. Se unen con un espacio y coinciden con el CSV.
- Bonos e Intermediación: líneas de detalle en 5,0 pt bajo el nombre: `Clas. Riesgo:`, `Tipo: …`, `Vencimiento: dd-mm-aaaa` (en el bono es `01-01-1900`, un valor de relleno), `Duration: 0,00 Años`, `Tasa de emisión: 1,23` (a veces sin `%`).
- Notas: la línea principal trae el nombre truncado (`XS2658535526 - PM ALPHA DAC BA`). Debajo, en 5,0 pt, va la descripción completa, que incluye texto con formato US (`0.000% 07/31/33`).
- Posición USD: `Precio Prom. Compra` y `Valor Cuota Actual` llevan prefijo `USD` (`USD 1.234,5678`). Valor de mercado en 2 líneas: `$ 1.234.567` encima y `US$ 1.234` (entero) debajo.
- Número cuenta: entero (0–9, 80–85, 90–96) o `<CTA_PERSHING>`.

Formatos numéricos:
- Miles con `.` y decimales con `,`. Cuotas con 4 decimales (`1.234,5678`); acciones enteras (`1.234`); precios con 4 decimales; valor de mercado CLP entero; US$ entero en detalle y 2 decimales en el resumen por clase; porcentajes con 2 decimales (`12,34%`), salvo `0%` en algunos Total.
- Signo de moneda con o sin espacio: `$ 1.234`, `$0`, `$7`.
- Negativos con signo tras la moneda (`$ -1.234`, `US$ -1.234,56`, `-12,34%`).
- **Excepciones**: en Bonos Internacionales, `Nominales` aparece como `25,000` (ejemplo sintético), con coma como separador de **miles** (formato US: el valor de mercado solo cuadra si se lee 25 mil). En Intermediación, `Nominales` parece estar en **UF** (un `FUBIC-…`, depósito BICE en UF, con nominal de 3 dígitos y valor de mercado de 8 dígitos). En Notas, `Precio Actual` está en % del nominal.
- Fechas en tablas `dd-mm-aaaa`; en portada `dd/mm/aaaa` y fecha en texto.

### 3.7 Movimiento de Caja
Encabezado: `Fecha` | `Número cuenta` | `Folio` | `Tipo de movimiento` | `Moneda` | `Cargo` | `Abono`. Una fila por línea, sin totales ni saldos inicial o final, ordenadas por fecha y luego por cuenta.
- Folio: `BCS_00000XXXXXXXX`.
- Montos: `$ 1.234.567` o `USD 1.234`. **Los USD van redondeados a entero.**
- Tipos vistos: ABONO SALDO $ VALORES SECURITY, ABONO SALDO USD VALORES SECURITY, REPARTO DE DINERO, DIVIDENDO EN PESOS, PAGO DE DIVIDENDOS, OPERACION DOLAR, CARGO EN DOLARES, FACTURA COMPRA RV, FACTURA COMPRA RV EN USD, FACTURA MONTO DE COBRO PESOS, CARGO COMPROMISO DE INVERSION $ OWP, ABONO POR COBRO DE INVERSION $ OWP, CARGO POR PAGO DE RESCATES $ OWP, ABONO ORIGINADO POR PAGO RESCATES $ OWP, ABONO ORIGINADO POR PAGO RESCATE US$ OWP, TRASPASO DE DINERO A/DESDE OTRA CUENTA (CLP y USD), ABONO ELECTRONICO A CUENTA CORRIENTE.
- **Error del PDF**: `CARGO EN DOLARES` (3 de 3 casos) viene con `Moneda = CLP` y monto `$ 1.234`, pero el monto es **USD**. Lo confirman la cuadratura de caja y el CSV, que lo registra con Moneda USD y Producto FORWARDS DIVISA.

### 3.8 Movimiento de Títulos
Encabezado: `Fecha` | `Número cuenta` | `Nº Referencia` | `Tipo de operación` | `Instrumento` | `Moneda` | `Cantidad` | `Precio` | `Monto`. Se repite en cada página (hasta 3 páginas). Sin totales.
- Nº Referencia: `FD_000000XXXXXXX_1` o `IT_000000XXXXXXX_1` en operaciones de custodia y un número de 8–9 dígitos en operaciones de FM.
- Tipos: INGRESO RV (313 filas, casi todas del 14-09: la migración desde Valores Security), COMPRA RV, INGRESO GARANTIAS RV, INVERSION FM, RESCATE FM.
- Cantidad con 4 decimales; Precio `$ 1.234,5678` o `USD 1,2345`; Monto `$ 1.234.567` o `USD 1.234` (USD entero).
- Instrumento largo en 2 líneas (encima y debajo de la fila), p. ej. `FI FRONTAL  CORDADA REND C/LIQ. MED. PL. SERIE` / `CLPP`.
- **Filas idénticas colapsadas**: en #05 y #17, la suma de movimientos queda corta en exactamente un lote que ya aparece listado (mismo Nº Referencia, cantidad y precio). Al agregar ese lote, el PPC del detalle cuadra al 4º decimal. El PDF parece aplicar un DISTINCT, así que **no sirve para reconstruir cantidades fila a fila**.

## 4. Saldos y movimientos

| Aporta | Sección PDF | Destino natural |
|---|---|---|
| Saldo de caja por portafolio y moneda | Detalle de Caja (+ USD con centavos en Resumen por Clase → Caja → Dólar) | SALDOS_CAJA |
| Fondos mutuos (FM SECURITY …, BICE …) | tablas "Fondos Mutuos" de RFN, RFI, RVN, RVI y Balanceados | SALDOS_FFMM (Producto FONDOS MUTUOS BICE) |
| FI administrados por BICE (F.I. SECURITY PANTHEON…, FONDO DE INVERSION RENTA DINAMICA…) | "Fondos Inversión Bice" (Alternativos) **o** "Fondos De Inversión" (RFN) | SALDOS_FFMM (FONDOS INVERSIÓN BICE) |
| Fondos de inversión en custodia (CFI) | "CFI", "Fondos De Inversión" (RFN, RVN, RVI) | CUSTODIA_ACCIONES (CFI) |
| Acciones | "Acciones" (RVN) | CUSTODIA_ACCIONES (ACCIONES) |
| FI clasificados como acción | "Acciones" en Alternativos (FI SECURITY PANTHEON FULLY FUND…, FI SECURITY D PRV AUT IV…) | CUSTODIA_ACCIONES (ACCIONES; el CSV los trata igual) |
| ETF | "ETF" (RVN, RVI) y a veces "Fondos De Inversión" (FI ETF SINGULAR GLOBAL CORPORATES) | CUSTODIA_ACCIONES (ETF) |
| Depósitos a plazo | Intermediación Financiera | **sin archivo destino en el Example** |
| Pershing (bonos, notas, caja USD) | Bonos Internacionales, Notas, Caja → "Mercado Internacional Pershing" | **sin SALDOS Pershing en el Example** (solo existe MOVIMIENTOS_PERSHING, vacío) |
| Movimientos de caja | Movimiento de Caja | MOVIMIENTOS_DE_CAJA |
| Compras y traspasos de custodia | Movimiento de Títulos (INGRESO RV, COMPRA RV, INGRESO GARANTIAS RV) | MOVIMIENTOS_BOLSA |
| Aportes y rescates de FM | Movimiento de Títulos (INVERSION FM, RESCATE FM) | MOVIMIENTOS_FFMM |

Contexto del período: casi todos los clientes fueron **migrados desde Valores Security el 14-09-2026**: "ABONO SALDO $/USD VALORES SECURITY" en caja e "INGRESO RV" masivo en títulos, con el costo histórico como precio. Por eso la cartola casi no tiene saldo inicial y, para cuentas migradas, la suma de movimientos reproduce el saldo final.

## 5. Mapeo al formato del Example

### 5.0 Relación de cuentas y portafolios (verificado contra el CSV)
- `Cuenta` (CSV) = **Número cuenta** (PDF). `Portafolio` (CSV) = **etiqueta exacta del portafolio** (Resumen por tipo de cuentas o Detalle de Caja), carácter por carácter. Se verificó en 47 de 47 combinaciones RUT–cuenta presentes en ambos.
- `ProductoBase` = grupo del PDF: "Cuenta de Inversión" → `CUENTA INVERSION`, "APV Prime" → `APV PRIME`, "APV FFMM" → `APV FFMM`. Coincide con el rango de cuenta del CSV: 0–9 = CUENTA INVERSION, 80–85 = APV FFMM, 90–96 = APV PRIME. "Mercado Internacional Pershing" no tiene equivalente.
- **Perímetro del export 10038**: solo portafolios cuyo nombre contiene "AFITRADING ASESORIA FINANCIERA". Los portafolios sin ese texto (6 de cuenta de inversión y 1 APV FFMM en 5 archivos) y Pershing **no están** en el CSV. Un portafolio AFI con $0 (#03, cuenta 2) tampoco tiene filas.
- `TipoAPV` / `DescripcionTipoRegimenTributario`: no vienen como campo. Se derivan del sufijo del portafolio con la regla que muestra el CSV:

| Sufijo del portafolio | Cuenta | TipoAPV | DescripcionTipoRegimenTributario |
|---|---|---|---|
| `- S` (cuentas de inversión) | 0–9 | vacío | vacío |
| `DAPV-B-S`, `DAPV-B-APV FLEXIBLE - S` | 80 / 90 | DAPV | BONIFICACIÓN |
| `CV-B-S` | 81 / 91 | CV | BONIFICACIÓN |
| `DC-S`, `DC-APV FLEXIBLE - S` | 82 / 92 | DC | BONIFICACIÓN |
| `DAPV-A-S` | 83 / 93 | DAPV | APORTE |
| `CV-A-S`, `CV-A` | 84 / 94 | CV | APORTE |
| `BF DAPV-A-S` | 85 (APV FFMM) | DAPV | APORTE |
| `BF DAPV-A-S` | 95 (APV PRIME) | DAPVC | APORTE |
| `BF CV-A` | 96 | DAPVC | APORTE |

  Ojo: en el CSV, régimen "-A" se rotula APORTE y "-B" BONIFICACIÓN. Conviene que Felipe confirme que esa es la convención deseada, porque parece invertida respecto del régimen legal. En los 20 PDF solo aparece DAPV-B.

### 5.1 SALDOS_CAJA
| Columna | Fuente PDF |
|---|---|
| FechaProceso | Fin del período de la portada ("al 30/09/2026" → 2026-09-30) |
| RutCliente | Rut de la portada sin puntos (= nombre de archivo) |
| Cuenta / Portafolio / ProductoBase | Fila de portafolio en Detalle de Caja + su grupo (§5.0) |
| Producto | constante `CUENTAS CAJA` |
| MonedaValoracionPatrimonio | `CLP` para la columna Pesos y `USD` para la columna Dólar (una fila por moneda). **Excepción APV PRIME**: el CSV junta CLP + USD×TC en **una sola fila CLP** con decimales; 194 de 316 filas APV PRIME del CSV tienen decimales |
| PatrimonioEnMonedaValoracion | Pesos (entero). USD: el detalle trae enteros. Los centavos salen de `equivalente CLP / 972,6` redondeado a 2 decimales (error ≤ 0,0005 USD) o de Resumen por Clase → Caja → Dólar cuando hay una sola cuenta USD no previsional |
| patrimonioUSD / patrimonioCLP | Se calculan con TipoCambioUSD |
| TipoAPV / DescripcionTipoRegimenTributario | Sufijo del portafolio (§5.0) |
| EnTransito | **Sin fuente.** El glosario dice que Caja incluye "movimientos en tránsito", pero no los separa. Usar `NO` por defecto y preguntar |
| TipoCambioUSD | Portada: 972,6 |
| TipoCambioEUR | **Sin fuente** (la columna Euro está siempre vacía). Dejar vacío o preguntar |

### 5.2 SALDOS_FFMM y CUSTODIA_ACCIONES
| Columna | Fuente PDF |
|---|---|
| FechaProceso, RutCliente, Cuenta, Portafolio, ProductoBase, TipoAPV, Régimen, TipoCambioUSD/EUR | Igual que en caja |
| Producto | Se deriva de la tabla y del instrumento: Fondos Mutuos → FONDOS MUTUOS BICE; Fondos Inversión Bice y FI BICE (RENTA DINAMICA) → FONDOS INVERSIÓN BICE; Acciones → ACCIONES (aunque sea un FI); ETF → ETF; CFI / Fondos De Inversión → CFI, salvo excepciones (FI ETF SINGULAR GLOBAL CORPORATES → ETF). **Recomendado: tabla maestra por Instrumento** |
| Archivo destino | SALDOS_FFMM si es FM BICE o FI BICE; si no, CUSTODIA_ACCIONES |
| Instrumento | Nombre del PDF (con espacios dobles; los nombres de 2 líneas se unen con un espacio). Coincide byte a byte en 169 de 170 posiciones cruzadas |
| NemotecnicoInstrumento | **No viene en el PDF**, salvo cuando el nombre ya es el nemotécnico (17 casos `CFI-XXXXXX`, y acciones como `SONDA` o `COPEC`). Excepción: acción `NUEVAPOLAR` → nemo `ABC`. FM: patrón `FM-<abreviatura>-SERIE X` con abreviaturas no deducibles (DOLAR MM, AGRESIVO EST, DEUDA INTERNAC., I. FUND S&P CLX…). → tabla maestra |
| MonedaInstrumento | Prefijo del precio: `USD` → USD; `$` → CLP |
| Emisor | **No viene.** FM y FI BICE → `BICE INVERSIONES ADMINISTRADORA GENERAL DE FONDOS`; el resto, tabla maestra (76 emisores en el CSV) |
| Cantidad | Número Cuotas / Acc. Libres / Cantidad (Notas). ¿Sumar Acc. en Gtía y Saldo a Plazo? En la muestra siempre son 0: preguntar |
| PrecioCierreEnMonedaValoracion | Valor Cuota Actual / Precio Actual, **en la moneda del instrumento** (también en APV, donde la valoración es CLP) |
| PrecioPromedioCompra | Precio Prom. Compra |
| MonedaValoracionPatrimonio | CUENTA INVERSION y APV FFMM → moneda del instrumento; **APV PRIME → siempre CLP** (785 de 785 filas USD del CSV) |
| PatrimonioEnMonedaValoracion | Valor de mercado (línea `$` o `US$` según la moneda de valoración). FFMM en el CSV = cuotas × valor cuota sin redondear (máx. 1e-4), así que conviene recalcular. CFI USD en cuenta de inversión = USD entero, igual que el PDF |
| patrimonioUSD / patrimonioCLP | Se calculan con TC |
| EnTransito | Sin fuente (`NO`) |
| Rentabilidad, Dividendos, % de activo | Sin columna destino (sirven para validar) |

### 5.3 Movimientos
- **MOVIMIENTOS_DE_CAJA** ← Movimiento de Caja.
  - FechaProceso ← Fecha. El CSV usa el día de proceso; en la cartola mensual se usa la fecha del movimiento.
  - Cuenta, Portafolio, ProductoBase y APV ← cuenta (§5.0).
  - nombreTipoMovimiento ← Tipo de movimiento (mismo vocabulario que el CSV).
  - Moneda ← Moneda, **forzando USD en CARGO EN DOLARES**.
  - abono / cargo ← Abono / Cargo (formato destino `1234,00`).
  - Producto e Instrumento se derivan. En el CSV: CUENTAS CAJA + `CAJA CLP` / `CAJA USD`; OPERACION DOLAR y CARGO EN DOLARES → `FORWARDS DIVISA` + `DOLAR`; DIVIDENDO EN PESOS / DÓLARES → Producto e Instrumento del **papel que pagó**, que el PDF **no informa**.
  - Folio no tiene columna destino.
  - Los USD del PDF son enteros y el CSV tiene centavos.
- **MOVIMIENTOS_BOLSA** ← Movimiento de Títulos con INGRESO RV, COMPRA RV e INGRESO GARANTIAS RV.
  - Columnas directas: Instrumento; MonedaInstrumento = Moneda; NombreTipoMovimiento = Tipo de operación; Cantidad; PrecioTIR = Precio; MontoNeto = Monto.
  - Nemotécnico y Emisor ← tabla maestra.
  - Nº Referencia no tiene columna en BOLSA.
  - En el CSV, el único INGRESO RV trae PrecioTIR `0,0010`, mientras el PDF muestra el costo. Hay que confirmar qué precio se espera.
- **MOVIMIENTOS_FFMM** ← INVERSION FM y RESCATE FM.
  - `NumeroRerferencia` ← Nº Referencia (8–9 dígitos, mismo formato que el CSV).
  - Producto FONDOS MUTUOS BICE.
- **MOVIMIENTOS_PERSHING**: sin movimientos Pershing en la muestra.

### 5.4 Cruce con Example Export (CSV al 22-09, cartola al 30-09)

Sobre los 20 archivos se cruzó por `RutCliente` + `Cuenta` + `Instrumento`, y por cantidad cuando el nombre no calzó:
- **185 posiciones** en los PDF. **170** tienen fila en el CSV: 169 por nombre exacto y 1 solo por cantidad.
  - Las **15 sin fila** se explican todas: 9 están en portafolios sin "AFITRADING", 2 son de Pershing y 4 son FM **comprados el 24–25-09** (FM SECURITY DEFENSIVO SERIE A ×2 y FM SECURITY MID TERM UF SERIE I-APV ×2, estos últimos dentro de APV PRIME, cuenta 90; no hay ejemplo de cómo exporta BICE un FM en APV PRIME).
  - **3 filas del CSV sin posición** en el PDF: 2 FM rescatados el 24-09 y 1 ETF con otro nombre (ver cliente #14).
- **Cantidad**: igual en 168/170. Una diferencia es una compra del 24-09. La otra (#03, FM COMPASS TOESCA CHILE EQUITIES SERIE B) son +2 cuotas a costo ≈ 0 **sin movimiento** en el PDF, probablemente cuotas liberadas o reinversión.
- **PPC**: igual en 163/170. 4 difieren en el 4º decimal (redondeo distinto). 2 se deben a compras del 21 y 24-09: el PDF ya incluye el promedio ponderado y el CSV no. Queda 1 (COMPASS).
- **Precio**: igual en 36/170. Son siempre FI cuyo valor cuota no cambió entre el 22 y el 30-09. Difiere en todos los FFMM (valor diario), acciones y FI con nuevo valor. → **diferencia explicada por fecha**.
- **Valor de mercado**: igual solo donde el precio es igual y la valoración no pasa por TC. En posiciones USD valoradas en CLP (APV PRIME), aun con igual precio, el CLP del PDF / CSV = 972,6 / 945,87 = 1,02826 exacto. → **diferencia de TC por fecha**.
- **Caja** (26 combinaciones cuenta × moneda): `CSV(22-09) + Σ movimientos posteriores al 22-09 = PDF(30-09)` cuadra **exacto** en 17. El resto se explica así: (a) CARGO EN DOLARES rotulado CLP (3 clientes); (b) CSV que consolida la caja USD en una fila CLP dentro de APV PRIME (3 clientes); (c) Pershing y portafolio sin AFI, que no están en el CSV (2 combinaciones). De las 9 combinaciones que no cuadran directo, 7 sí lo hacen al corregir (a) y (b). Las 2 de (c) no tienen contraparte en el CSV. La comparación USD usa ±1 porque el PDF redondea a entero (p. ej. US$ 12 en el PDF contra 12,34 en el CSV).
- **Movimientos**: el CSV no tiene **ninguna** fila para estos 20 RUT y ningún movimiento de los PDF tiene fecha 22-09 (hay días 02–17, 21, 24–30). Esto es consistente con que los MOVIMIENTOS_* del Example son de un solo día de proceso.

Detalle de 5 clientes:

| Cliente | Perfil | Qué coincide exacto | Qué difiere y por qué |
|---|---|---|---|
| #04 | 5 portafolios de inversión (2 sin AFI) + APV Prime + Pershing; acciones, CFI CLP/USD, FFMM, FI BICE | 21/21 posiciones AFI: cantidad y PPC. 3 FI (TOESCA INFRAESTRUCTURA B, TOESCA RENTA RESIDENCIAL A, FYNSA PANTHEON GLOBAL CO-INV) con igual valor cuota → valor idéntico (el USD en US$; el CLP solo cambia por TC). Caja APV (cuenta 90) idéntica. `NUEVAPOLAR` ↔ nemo `ABC` | Valor cuota y precio de acciones distintos (fecha). Caja de la cuenta 2: no está en el CSV porque nace con REPARTO DE DINERO + DIVIDENDO EN PESOS del 30-09 (cuadra exacto). BICE ACCIONES CHILE ACTIVO LIQUIDEZ en cuentas 0/1 (sin AFI) y todo Pershing (bono, nota, caja USD): ausentes del CSV por perímetro |
| #05 | Cuenta "PORTAFOLIO 57 BIS 0" + APV Prime con muchos CFI USD | 19/19: cantidad y PPC. CFI USD: el CSV valora en CLP con precio en USD, igual que el PDF muestra `$` y `US$` | Valor CLP ×1,02826 donde el precio no cambió (TC). FM MID TERM UF I-APV (cuenta 90): ausente del CSV por compra del 25-09. Caja APV: el CSV trae 1 fila CLP con decimales (CLP + USD×945,87); el PDF separa Pesos y Dólar. Cuadra con los movimientos del 25-09 si CARGO EN DOLARES se toma como USD |
| #08 | Caja CLP+USD; FFMM, CFI; Intermediación en portafolio sin AFI | 15/15: cantidad y PPC. 2 FI con precio y valor idénticos. Caja CLP: CSV + movimientos del 25 y 30-09 = PDF exacto | Caja USD: el CSV tiene centavos y el PDF la muestra entera en el movimiento del 14-09; se liquida el 25-09 con un CARGO EN DOLARES rotulado CLP. FUBIC (Intermediación, cuenta 0 sin AFI) ausente del CSV |
| #13 | Solo USD: caja USD, FM USD, CFI USD, más un FM CLP de valor mínimo | Caja USD **al centavo** entre Resumen por Clase (US$ con 2 decimales) y SALDOS_CAJA. 3/3 posiciones: cantidad y PPC | Precio y valor por fecha. Detalle de Caja muestra la caja USD redondeada a entero. La posición mínima en CLP no aparece en Resumen por Clase |
| #14 | Persona jurídica; compras y rescates después del 22-09; caja USD negativa | CLP y USD de caja: CSV + movimientos posteriores = PDF exacto (incluido el saldo USD negativo). FI LINK HOLLYPORT IX, SERIE B del PDF (tabla ETF de RV Nacional) = CSV `ETF SINGULAR GLOBAL EQUITIES` (nemo CFI-LCPHBE): igual cuenta, cantidad, PPC, precio y US$ | **Nombre de instrumento distinto** (el nemo apunta a Hollyport, así que el error parece estar en el CSV). DOVER STREET XI: igual cantidad, PPC distinto (compra del 21-09 ya en la cantidad del CSV, pero no en su costo). NM PARTNERS VII: compra del 24-09 → PDF = CSV + compra. 2 FFMM de la cuenta 1 rescatados el 24-09: siguen en el CSV y faltan en el PDF |

**Nombres de instrumento PDF ↔ CSV**: `Instrumento` (CSV) = nombre de la fila del PDF, incluidos espacios dobles, comas y sufijos de serie. `NemotecnicoInstrumento` solo es deducible del nombre cuando ya es nemotécnico (`CFI-…`, acciones), y aun ahí hay excepciones (NUEVAPOLAR → ABC). En los demás casos (CFI con nombre largo, FM, FI BICE) hace falta una tabla de equivalencias. El catálogo del CSV cubre 76 de los 89 nombres distintos de los PDF (posiciones y movimientos). Faltan 13: los fondos "BICE …" de portafolios sin AFI o ya rescatados (8), los bonos y notas Pershing (2), el FUBIC, FM SECURITY MID TERM UF SERIE I-APV y FI LINK HOLLYPORT IX, SERIE B.

## 6. Cuadraturas (probadas en los 20 archivos)

| Regla | Resultado | Tolerancia |
|---|---|---|
| Resumen por tipo de cuentas: Σ portafolios = subtotal del grupo | 27/28 (1 a 2 CLP, con 8 portafolios) | ±0,5 CLP por fila |
| Σ grupos = Total = Patrimonio de Página 01 | 20/20 | ±1 |
| Previsionales + No previsionales = Patrimonio (variante A) | 16/16 | ±1 |
| Variante B: Activos − Pasivos = Patrimonio; variante C: Patrimonio al cierre anterior + Abonos − Retiros + Rentado = Patrimonio, y Saldo Inicial + Aportes/Retiros + Rentado = Saldo Final | Cuadra en los archivos revisados (#14 y #18) | exacto |
| Detalle de Caja: Pesos + Dólar(CLP) + Euro = Valor de Mercado | 37/37 filas | ±1 |
| Caja: US$ entero = round(CLP equivalente / 972,6) | 18/18 | ±0,5 USD |
| Σ Valor de mercado de las filas = "Total" del bloque | 64/64 bloques | ±0,5 por fila |
| Cuotas × valor cuota = Valor de mercado (CLP) | 143/143 | ±0,5 CLP |
| Cuotas × valor cuota = Valor de mercado US$ | 38/39 (1 a 0,59 USD por precio redondeado a 4 decimales) | ±(0,5 + cuotas × 0,00005) |
| CLP de posiciones USD | CFI/ETF en cuenta de inversión: CLP = US$ entero × 972,6 (18/18). FFMM, FI BICE y APV: CLP = cuotas × precio × 972,6 (16/21; los otros 5 difieren por el precio mostrado con 4 decimales) | ±1 CLP; ±0,01 % con precio redondeado |
| Notas: cantidad × precio / 100 = US$ | 1/1 | ±0,5 |
| Rentabilidad = (VM + Dividendos) / (cantidad × PPC) − 1 (Dividendos solo en tablas que los tienen; en FM = valor cuota / PPC − 1) | 172/182 | ±0,01 pp. Falla en fondos USD de APV (rentabilidad en CLP histórico, no reproducible) y en posiciones mínimas (VM redondeado) |
| % de activo = VM / Patrimonio total | 184/184 | ±0,01 pp |
| Resumen por Clase (Pesos + Dólar × 972,6 + APV) = Σ Totales del detalle de esa clase | 53/57 (RFI con diferencia ≤ 5 CLP: el resumen usa USD con centavos) | ±5 CLP |
| Movimiento de Títulos: cantidad × precio = monto | 337/337 | ±1 (USD entero) |
| Caja: Σ movimientos del período = saldo final (cuentas migradas el 14-09) | 18/26 combinaciones; el resto tiene saldo previo, Pershing o CARGO EN DOLARES mal rotulado | exacto con CLP; USD ±1 |
| Títulos: Σ cantidades netas de movimientos = cantidad final | 136/146 pares cuenta–instrumento. Los fallos son FM con saldo anterior al período (7), filas idénticas colapsadas (2) y COMPASS (1) | exacto |

En #04, #08 y #13 (los tres revisados también a mano) todas las reglas aplicables cuadran, salvo las excepciones ya descritas en la tabla: RFI ±5 CLP en el resumen por clase, la rentabilidad de posiciones mínimas o de fondos USD en APV, y el precio redondeado a 4 decimales.

## 7. Riesgos y particularidades

1. **Texto anonimizado al final del orden de lectura** (solo en la portada). Hay que leerlo por coordenadas. La pila de etiquetas se desplaza cuando el nombre o la dirección ocupan 2 líneas.
2. **Celdas en 2 líneas**: `$` encima y `US$` debajo en Valor de mercado y Caja, y nombres de instrumento que envuelven encima o debajo de la línea de números. Asignar por "fila ancla" (la celda Número cuenta o Fecha) y cercanía vertical, no por línea de texto.
3. **"Total" es por bloque**, no por tabla. Los bloques APV ("- Previsional (APV)") tienen su propio Total.
4. **Columnas que cambian de posición** entre páginas y archivos (cada tabla se autoajusta). Hay que detectar los encabezados en cada tabla. El orden también cambia: en RFN, "Rentabilidad" va antes de "Dividendos".
5. **Moneda mal rotulada**: CARGO EN DOLARES aparece con Moneda CLP y `$`, pero es USD. Total de caja con `$ -1.234`, que en realidad es USD.
6. **Pérdida de precisión en USD**: caja, movimientos y valor de mercado en US$ enteros. Los centavos solo se recuperan desde el equivalente CLP / 972,6 o desde Resumen por Clase.
7. **Formatos atípicos**: `Nominales` de bonos con coma como separador de miles; nominales en UF en Intermediación; precio de Notas en % del nominal; fecha de vencimiento `01-01-1900` como relleno; `Tasa de emisión` a veces sin `%`.
8. **Movimiento de Títulos colapsa filas idénticas.** No sirve para reconstruir cantidades y faltan eventos (cuotas liberadas). Para saldos hay que usar siempre las tablas de detalle.
9. **Perímetro**: la cartola trae portafolios que no son de AFI y Pershing. Hay que decidir si se exportan, y a qué archivo.
10. **Clasificación PDF ≠ Producto CSV**: FI listados como "Acciones", ETF listados como "Fondos De Inversión", FI BICE mezclados con CFI. Hace falta una tabla maestra por instrumento.
11. **Nombre distinto entre PDF y CSV** para la misma posición (HOLLYPORT ↔ ETF SINGULAR GLOBAL EQUITIES). Si se valida contra el CSV, cruzar también por cuenta + cantidad + PPC.
12. **Variantes de Página 01** (A, B y C) y tabla de Resumen por Clase sin columna APV para personas jurídicas.
13. **Secciones que podrían ocupar varias páginas**: en la muestra solo Movimiento de Títulos pasa de una página. Activos Alternativos llega hasta y≈533 de 595 (#19), así que un cliente con más fondos probablemente tendrá páginas de continuación con el mismo título. El parser debe concatenar páginas con el mismo título.
14. **Fecha de los CSV**: el Example es del 22-09 y la cartola del 30-09. TipoCambioUSD 945,87 contra 972,6, y no hay TipoCambioEUR en el PDF.
15. **Gráficos** en Página 01 y 03: sus etiquetas (4,3–6,3 pt) se mezclan con el texto. Recortar por x o ignorarlas.

## 8. Enfoque recomendado de extracción

**pymupdf `page.get_text("dict")`** (spans con bbox, fuente, tamaño y bold), con reglas geométricas. No conviene pdfplumber `extract_tables` (no hay líneas de tabla: devuelve 0 tablas) ni regex sobre `pdftotext -layout` (colapsa los espacios dobles de los nombres y desordena las celdas de 2 líneas). Así está implementado el extractor (`skill/cartolas/extractores/bice_nueva.py`, ver §9), que extrae las 185 posiciones, 78 movimientos de caja y 337 de títulos de los 20 archivos sin errores de alineación. Pasos:

1. **Página → sección**: primera línea del texto (título bold 17 pt). Concatenar páginas consecutivas con el mismo título.
2. **Portada**: etiquetas en x≈480 y valores en x≈634, asignados a la etiqueta más cercana por arriba. Período y TC con regex (`al (\d\d/\d\d/\d{4})`, `([\d.,]+) \(CLP/USD\)`).
3. **Encabezados de tabla**: span bold 6,2 en x<60 (≠ "Total") con ≥3 spans bold 6,2 a ±10 pt en y. Las columnas se forman agrupando esos spans por solape en x; la etiqueta se arma de arriba hacia abajo. Bloque = último span bold 7,0 en x<60 sobre la tabla (agregar el span regular "Previsional (APV)" de la misma línea).
4. **Filas**: ancla = span regular en la primera columna (Número cuenta o Fecha). Cada otro span de la región se asigna al ancla más cercana en y (penalizando los que están >9 pt sobre el ancla). Columna = mayor solape en x con el encabezado. A la izquierda de la primera columna: tamaño ≥ 6,0 = nombre (se unen las líneas con espacio) y 5,0 = categoría o detalle (bono, nota, intermediación).
5. **Caja y Resúmenes**: anclar por etiqueta izquierda (x<60), con los encabezados de la banda superior. En Resumen por Clase hay que recortar x < 420.
6. **Números**: `^(US\$|USD|\$)?\s?-?[\d.]+(,\d+)?%?$` → quitar `.` y cambiar `,` por `.`. Moneda por prefijo. Excepciones: Nominales de bonos (coma de miles) y CARGO EN DOLARES (forzar USD).
7. **Enriquecimiento**: cuenta → Portafolio/ProductoBase/TipoAPV/Régimen (§5.0). Instrumento → archivo destino, Producto, Nemotécnico y Emisor mediante una tabla maestra semilla construida desde los CSV del Example (183 instrumentos en custodia y 53 en FFMM), con revisión manual de los nuevos.
8. **Validación automática**: aplicar las reglas de §6 por archivo y marcar el archivo si alguna falla fuera de tolerancia.

Preguntas abiertas para Felipe:
- ¿Se exportan los portafolios sin "AFITRADING" y Pershing? ¿A qué archivo van Pershing e Intermediación Financiera?
- ¿FechaProceso = fin de período?
- ¿Qué valor usar en `EnTransito` y en `TipoCambioEUR`?
- ¿Cómo debe salir un FM dentro de APV PRIME?
- ¿Se suman Acc. en Gtía y Saldo a Plazo a Cantidad?
- ¿Qué PrecioTIR se espera en INGRESO RV?
- ¿Se confirma la convención A = APORTE / B = BONIFICACIÓN?

## 9. Extractor implementado

```
cd skill
python -m cartolas "<carpeta con las cartolas>" --salida "<carpeta de salida>" [--solo-afi]
```

Escribe los 7 CSV con el nombre `<ARCHIVO>_<código>_<cierre>_V2.csv` (el código se toma del nombre de los PDF, `CARTOLA_<código>_...`) y un `REPORTE_<código>_<cierre>.md` con las cuadraturas que no cierran, los avisos y lo que no se exportó. El reporte trae RUT y nombres de archivo, así que no va al repositorio.

### Resultado sobre las 20 cartolas anonimizadas

| Verificación | Resultado |
|---|---|
| Cuadraturas internas (sumas por cuenta, grupo, sección y total; caja; cantidad × precio en posiciones y movimientos) | 260 controles, todos cierran. Tolerancia: medio peso por sumando |
| Montos impresos en las páginas de detalle y movimientos que no quedaron en ninguna fila | Ninguno (solo la etiqueta "Previsional (APV)" de los bloques) |
| Posiciones exportadas que también están en el export de ejemplo | 170 de 182 |
| De esas 170, mismo portafolio, producto base, producto, nemotécnico, moneda, emisor, moneda de valoración, tipo de APV y régimen | 170 |
| Misma cantidad | 168. Las 2 restantes cambiaron entre el 22-09 y el 30-09 (una por una compra del 24-09 que aparece en los movimientos); en ambas el valor exportado es el impreso en la cartola |
| Mismo precio promedio de compra | 163. En las 7 restantes el valor exportado es el impreso en la cartola; 4 difieren en 0,0001 o 0,0002 |

De las 12 posiciones sin par en el ejemplo, 8 son de portafolios que no son de AFI Trading (el ejemplo no los trae) y 4 se compraron el 24 y 25-09, después del export, según los movimientos. 10 de ellas son fondos que no están en la tabla maestra, así que salen sin nemotécnico ni emisor y con un aviso en el reporte.

### Resultado contra el export diario al 30-09 (480 cartolas del SFTP)

Cartolas de septiembre de todos los clientes, corridas juntas con `--solo-afi --tipo-cambio-eur 1102,72109` y comparadas con `python -m cartolas.comparar` contra los saldos del 30-09 y los movimientos diarios del 11-09 al 30-09. Las 480 cartolas cierran todas sus cuadraturas.

| Archivo | Filas del export con par | Diferencias que quedan | Sin par |
|---|---|---|---|
| SALDOS_CAJA | 744 de 747 | Ninguna | 3 del export: caja en dólares bajo US$ 0,50, que la cartola no imprime |
| SALDOS_FFMM | 766 de 766 | 6 de redondeo (un fondo APV que el export redondea a pesos) | Ninguna |
| CUSTODIA_ACCIONES | 4052 de 4052 | 11 de redondeo, de medio peso o menos | Ninguna |
| MOVIMIENTOS_DE_CAJA | 1726 de 1770 | Centavos de dólar (la cartola imprime enteros); 3 dividendos sin instrumento deducible | 44 del export: abonos y cargos de dividendos de AGF que la cartola no imprime. 36 de la salida: abonos de saldos traídos desde Security el 14-09, que el export no trae |
| MOVIMIENTOS_BOLSA | 9441 de 9795 | Emisor en 123 (el export de movimientos nombra distinto algunos emisores que el de saldos); centavos de dólar | 354 del export: lotes idénticos que la cartola junta en una fila y tres fondos que el export del 14-09 nombra distinto. 238 de la salida: cuentas sin movimientos del 14-09 en el export |
| MOVIMIENTOS_FFMM | 157 de 158 | 3 de centavos de dólar | 1 del export, 2 de la salida |

Lo que no tiene par o difiere viene de lo que la cartola no imprime o de inconsistencias del propio export; no quedan errores de lectura conocidos.

### Decisiones mientras Felipe responde las preguntas

- **Portafolios.** Se exportan todos; `--solo-afi` deja solo los que dicen AFITRADING, como el ejemplo.
- **Cuenta Pershing dentro de la cartola.** No se exporta (su caja, bonos y notas): no tiene número de cuenta BICE y el ejemplo no trae saldos Pershing. Queda en el reporte.
- **Sin archivo de destino.** Intermediación Financiera, Bonos, Bonos Internacionales y Notas quedan en el reporte (el export lleva los bonos a `CUSTODIA_RENTA_FIJA`, que la skill no escribe). Sus movimientos `INGRESO RF` sí van a `MOVIMIENTOS_BOLSA`, como en el export, igual que `VENTA CF`.
- **FechaProceso.** Saldos: fecha de cierre de la cartola. Movimientos: fecha del movimiento.
- **Valorización.** Como en el ejemplo: `SALDOS_FFMM` con cuotas × valor cuota truncado a 4 decimales; `CUSTODIA_ACCIONES` con el valor de mercado impreso, en USD en la cuenta de inversión y en pesos en las cuentas APV. Los USD de caja recuperan los centavos desde el equivalente en pesos.
- **Movimientos de caja.** `CARGO EN DOLARES` y `OPERACION DOLAR` van con instrumento `DOLAR` y producto `FORWARDS DIVISA`; el resto, con `CAJA CLP` o `CAJA USD`. Los dividendos y repartos no dicen de qué instrumento son; el export usa el nemotécnico, así que se deduce juntando las cartolas: un instrumento paga el mismo monto por cuota a todos sus aportantes el mismo día (`dividendos.py`). Si no hay cómo saberlo, van como caja.
- **Montos en USD de los movimientos.** La cartola los imprime sin decimales y no trae el equivalente en pesos, así que salen enteros.
- **`TipoCambioEUR`**: la cartola no lo trae; se toma de otra cartola con el mismo cierre o de `--tipo-cambio-eur`, y si no, queda vacío.
- **Caja en tránsito.** La tabla "Cuentas por Cobrar" de la página de caja y "Cuentas por Pagar" de los pasivos van a `SALDOS_CAJA` con `EnTransito` = `SI` (la segunda con monto negativo), como en el export.
- **Caja en dólares bajo US$ 0,50.** La cartola no la muestra y el export sí; la cuenta queda sumando unos pesos menos que su patrimonio y el reporte lo avisa.
- **Nombre del instrumento.** Se exporta el de la tabla maestra (el del export). `datos/alias.csv` resuelve los que la cartola nombra distinto, como el caso HOLLYPORT de §7.
