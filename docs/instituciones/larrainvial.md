# Inventario de layout: Larrainvial (informe patrimonial mensual)

Carpeta: `datos/anonimizado/Training Data/Larrainvial/` (14 PDF).
Los nombres de archivo contienen el nombre (ficticio) del cliente, así que aquí se citan por número
`#1…#14` (orden de `sorted(os.listdir())` en Python) y por patrón. Todos los montos y cantidades de
este documento son sintéticos.

## Resumen

- Son 14 informes mensuales de 2 clientes. El **Cliente A** tiene 12 meses seguidos, de **sep-2025 a ago-2026**, sin meses repetidos ni faltantes. El **Cliente B** tiene jun-2026 y ago-2026, y **le falta jul-2026**. No hay ningún informe de sep-2026: el archivo "…Septiembre.pdf" corresponde a **septiembre de 2025**.
- Las páginas tienen `/Rotate 90` (MediaBox 612×792 en vertical). Visualmente son apaisadas (792×612) y su texto es horizontal. En el espacio sin rotar, PyMuPDF devuelve todas las líneas con `dir=(0,-1)`, es decir, como texto vertical. Hay que aplicar `page.rotation_matrix` a las coordenadas (o usar pdfplumber ≥0.11 o `pdftotext -layout`, que ya rotan).
- Todo el texto es extraíble (no hay escaneos). No hay tablas con líneas: se debe leer por palabras con coordenadas.
- Hay dos tipos de documento: **INFORME PROVISORIO PATRIMONIAL** (12 archivos) y **CARTOLA PATRIMONIAL** (definitiva; #12 = dic-2025 y #14 = jul-2026). El "Prov" del nombre de archivo no sirve para distinguirlos (ver §1.3).
- Las cuadraturas internas dan 100 % en los 14 archivos, y la continuidad mes a mes del Cliente A también: **Patrimonio Fin (m) = Patrimonio Inicio (m+1) en las 11 transiciones, sin diferencia**.
- Los 2 RUT aparecen en `RutCliente` del export de BICE, pero con posiciones de BICE, no de Larrainvial (ver §5.6).

---

## 1. Archivos

| # | Patrón de nombre | Cliente | Período (encabezado) | Tipo (título p.1) | Emitido (nota legal) | Págs | KB |
|---|---|---|---|---|---|---|---|
| 1 | `<Nombre> Septiembre.pdf` | A | Septiembre **2025** | Provisorio | 6-oct-2025 | 6 | 97 |
| 2 | `<Nombre>.pdf` (sin mes) | A | Octubre 2025 | Provisorio | 4-nov-2025 | 6 | 97 |
| 13 | `LV <Nombre> NOV-25.pdf` | A | Noviembre 2025 | Provisorio | 2-dic-2025 | 6 | 97 |
| 12 | `LV <Nombre> DIC-25.pdf` | A | Diciembre 2025 | **Definitiva** | 8-ene-2026 | 6 | 55 |
| 3 | `Cartola <NOMBRE> enero 2026 (1).pdf` | A | Enero 2026 | Provisorio | 3-feb-2026 | 6 | 97 |
| 5 | `Cartola Prov <NOMBRE> febrero 2026.pdf` | A | Febrero 2026 | Provisorio | 3-mar-2026 | 6 | 98 |
| 7 | `Cartola Prov <NOMBRE> marzo 2026.pdf` | A | Marzo 2026 | Provisorio | 6-abr-2026 | 8 | 95 |
| 11 | `Cartola prov <NOMBRE> abril 2026.pdf` | A | Abril 2026 | Provisorio | 4-may-2026 | 5 | 91 |
| 8 | `Cartola Prov <NOMBRE> mayo 2026.pdf` | A | Mayo 2026 | Provisorio | 2-jun-2026 | 7 | 94 |
| 6 | `Cartola Prov <NOMBRE> junio 2026.pdf` | A | Junio 2026 | Provisorio | 2-jul-2026 | 5 | 91 |
| 14 | `<NOMBRE> LARRA JULIO.pdf` | A | Julio 2026 | **Definitiva** | 9-sep-2026 | 5 | 49 |
| 4 | `Cartola Prov <NOMBRE> agosto 2026.pdf` | A | Agosto 2026 | Provisorio | 2-sep-2026 | 5 | 91 |
| 10 | `Cartola Prov <NOMBRE B> junio 2026.pdf` | B | Junio 2026 | Provisorio | 2-jul-2026 | 11 | 106 |
| — | — | B | **Julio 2026: falta** | — | — | — | — |
| 9 | `Cartola Prov <NOMBRE B> agosto 2026.pdf` | B | Agosto 2026 | Provisorio | 2-sep-2026 | 8 | 98 |

### 1.1 Datos generales

- **Páginas:** entre 5 y 11 por archivo, 90 en total. La MediaBox es carta (612×792) con `/Rotate 90`, de modo que se ve apaisada (792×612). Todas las páginas de todos los archivos están rotadas.
- **Texto:** extraíble y nativo, en PDF 1.4 y sin metadatos (no hay Producer ni fechas). Las fuentes originales son `HelveticaNeueLTStd-LtCn/-Cn/-MdCn`. El texto reemplazado por el anonimizador está en `Helvetica`: el RUT en todas las páginas, y el nombre y la dirección en la p.1.
- **Imágenes:** logo, código de barras (solo en la p.1) y, **solo en los provisorios**, un timbre "INFORME PROVISORIO" en cada página. Por eso las definitivas pesan cerca de la mitad.
- **Moneda del reporte:** pesos chilenos. Todos los "Monto ($)" están en CLP. Las posiciones en USD se valorizan con el "Dolar" de los *Valores de referencia* del pie. Caja y movimientos en dólares se informan en USD (aunque el encabezado diga "($)").
- **Fecha de emisión:** solo aparece en la nota legal de la última página: `- El presente documento fue emitido con fecha D de Mes de AAAA.`. El encabezado trae `Periodo: <Mes> <AAAA>`. La p.1 trae además un número de 14 dígitos bajo el código de barras con forma `AAAAMM12NNNNNN`, donde AAAAMM es el período.
- **Cuenta:** en los 90 encabezados aparece `Cuenta: 0`. Es texto original, no anonimizado: Larrainvial no muestra un número de cuenta en este informe.

### 1.2 Duplicados y continuidad

- Los 14 SHA-256 son distintos y los 14 pares (cliente, período) también: no hay duplicados ni casi duplicados.
- Los meses consecutivos sin movimientos del Cliente A (sep-25 a feb-26, abr-26 y jun-26 a ago-26) se ven muy parecidos, porque tienen las mismas cantidades y el mismo número de páginas. Aun así, difieren en precios, dólar de referencia y totales. El sufijo "(1)" del #3 sugiere una segunda descarga, pero no hay otra copia de enero.
- **Cliente A:** 12 meses consecutivos de sep-2025 a ago-2026, sin repetidos ni huecos.
- **Cliente B:** jun-2026 y ago-2026. **Falta jul-2026**, lo que se confirma numéricamente (ver §6.2).
- Ningún archivo es de sep-2026. El export de BICE es del 22-09-2026, así que no hay un informe de Larrainvial a la fecha del ejemplo.
- El nombre del archivo no es confiable para el período: #1 dice "Septiembre" y es de 2025, y #2 no indica mes. Hay que leer siempre `Periodo:` del encabezado.

### 1.3 "Cartola Prov" frente a archivos sin "Prov"

El "Prov" lo puso quien descargó el archivo, y no es una regla:

- Los 8 archivos con "Prov"/"prov" (#4–#11) son efectivamente provisorios.
- De los 6 sin "Prov", 4 también son provisorios (#1, #2, #3, #13) y 2 son definitivos (#12 dic-25 y #14 jul-26).

Cómo distinguirlos por el contenido:

| Característica | Provisorio | Definitiva |
|---|---|---|
| Título (p.1 y p.2, y≈86) | `INFORME PROVISORIO PATRIMONIAL` | `CARTOLA PATRIMONIAL` |
| Timbre "INFORME PROVISORIO" (imagen, abajo a la derecha) | En todas las páginas | No aparece |
| Bloque **Rentabilidad** en la p.1 | Los 2 títulos "Rentabilidad" están en **texto blanco (invisible)** y no hay valores | Visible, con filas `Nominal` y `Real` × (mes, año anterior, año actual YTD) en formato `-1,23%` |
| Resto de secciones y columnas | Iguales | Iguales |
| Emisión | 2 a 6 días después del cierre de mes | dic-25: 8 días después. jul-26: emitida el 9-sep, después del provisorio de agosto |

No hay ningún mes con ambas versiones, así que no se pudo comparar un provisorio con su definitiva. Lo que sí se comprobó es que la cadena encaja exacto en los cruces provisorio→definitiva→provisorio: Fin nov(prov) = Inicio dic(def), Fin dic(def) = Inicio ene(prov), Fin jun(prov) = Inicio jul(def) y Fin jul(def) = Inicio ago(prov).

**Regla sugerida:** clasificar por el título. Si llegan ambas versiones de un mismo (RUT, período), quedarse con la `CARTOLA PATRIMONIAL`; si no, con la de emisión más reciente.

---

## 2. Estructura del documento

Cada sección o subsección empieza en una página nueva y solo aparece si tiene datos. Orden observado:

| Pág. | Título de página (y≈86–88) | Subtítulo (y≈108–112) | Presencia |
|---|---|---|---|
| 1 | `INFORME PROVISORIO PATRIMONIAL` / `CARTOLA PATRIMONIAL` | Bloques: `Evolucion de patrimonio` (2 tablas), `Rentabilidad` (2), `Patrimonio por clase de activo`, `Distribucion por clase de activo` (torta) | Siempre |
| 2 | Mismo título | `Patrimonio por monedas`, `Distribucion patrimonio por monedas` (torta), `Patrimonio por tipo de producto`, `Distribucion patrimonio por tipo de producto` (torta) | Siempre |
| 3… | `PATRIMONIO POR CLASE DE ACTIVO` | `CAJA` | Siempre (14/14) |
| … | `PATRIMONIO POR CLASE DE ACTIVO` | `RENTA FIJA` | 8/14 (cuando hay fondos de renta fija) |
| … | `PATRIMONIO POR CLASE DE ACTIVO` | `ALTERNATIVOS` | 14/14 |
| … | `MOVIMIENTOS` | (página **vacía**, solo con el título) | #7 y #8. Ignorar |
| … | `MOVIMIENTOS` | `MOVIMIENTOS DE CAJA EN PESOS` | #9, #10 |
| … | `MOVIMIENTOS` | `MOVIMIENTOS DE CAJA EN DOLAR` | #7, #8, #10 |
| … | `MOVIMIENTOS` | `MOVIMIENTOS DE TITULOS EN PESOS` | #9, #10 |
| … | `MOVIMIENTOS` | `MOVIMIENTOS DE TITULOS EN DOLAR` | #7, #10 |
| … | `GARANTIAS` | `INSTRUMENTOS EN GARANTIA` | Solo #10 |
| última | (sin título) | Notas legales, incluida la fecha de emisión | Siempre |

- **Clases que no aparecen en esta muestra:** `RENTA VARIABLE`, `INTERNACIONAL` u otras. Tampoco hay posiciones en EUR ni datos en "Fecha vencimiento" o "Duracion años". El extractor debe fallar en forma visible si encuentra un subtítulo desconocido.
- **Encabezado de la p.1 (arriba a la derecha):** etiquetas `R.U.T. Cliente:`, `Periodo:` y `Cuenta:` (x≈343), con sus valores en x≈413. Más a la derecha (x≈530) va el bloque del cliente: nombre (y≈21), dirección (y≈32) y `CIUDAD - CHILE` (y≈44). Debajo, el código de barras y su número (y≈71).
- **Encabezado de la p.2 en adelante:** las mismas tres etiquetas (x≈493, valores en x≈563) y el bloque `Gestor Patrimonial` con nombre, email y teléfono del ejecutivo (x≈660).
- **Pie de todas las páginas:** `- Valores de referencia Dolar $<n> | Euro $<n> | UF $<n>` (y≈574), `www.larrainvial.com` y `Pagina N de M`.

---

## 3. Detalle por sección

Formato numérico chileno:

- `.` para miles y `,` para decimales; negativos con `-` adelante (`-1.234.567`, `-1,23`).
- Cero como `0`. Celdas vacías en blanco, sin guion.
- Montos en CLP sin decimales. Montos en USD con 2 decimales. Cantidades y cotizaciones con 4 decimales. Porcentajes con 2 decimales.

**Anomalía:** en #14 (definitiva de julio), el total de la columna Distribución de `Patrimonio por clase de activo` aparece como `100.00`, con **punto**. En el resto de los casos se usa coma.

Fechas: `dd/mm/aaaa` en los movimientos, `<Mes> <AAAA>` en el período y `D de Mes de AAAA` en la emisión. Se omiten los acentos ("Los acentos han sido omitidos voluntariamente"), con excepciones: `Fondos de inversión`, `Saldo Caja Dólar`, `Duracion años` y la tabla de garantías (`Nemotécnico`, `Descripción`, `Cantidad en garantía`). Conviene normalizar con `unicodedata` antes de comparar etiquetas.

### 3.1 p.1: Evolucion de patrimonio
Son dos tablas lado a lado. La izquierda tiene el título `Evolucion de patrimonio | <Mes AAAA>` y la derecha `Evolucion de patrimonio | Año <AAAA-1> | Año <AAAA> (YTD)`. Debajo de cada columna va el subencabezado `Monto ($)`. Las filas, con los mismos rótulos en ambas tablas, son:

```
Patrimonio Inicio Periodo   1.234.567     | Patrimonio Inicio Periodo   1.234.567   1.234.567
Aportes                             0     | Aportes                       123.456     123.456
Retiros                      -123.456     | Retiros                             0    -123.456
Cambio Valor Cartera          -12.345     | Cambio Valor Cartera         -12.345      12.345
Patrimonio Fin del Periodo  1.234.567     | Patrimonio Fin del Periodo  1.234.567   1.234.567
```
Retiros siempre aparece con signo negativo y Cambio Valor Cartera puede ser negativo.

### 3.2 p.1: Rentabilidad (solo en la definitiva)
Encabezado `Rentabilidad | <Mes AAAA> | Año AAAA-1 | Año AAAA (YTD)`, con filas `Nominal` y `Real` en formato `-1,23%`. En el provisorio solo quedan los títulos en blanco, que no se ven.

### 3.3 p.1: Patrimonio por clase de activo
Columnas `Monto ($)` y `Distribucion (%)`. Las filas son las clases presentes (`Caja`, `Renta fija`, `Alternativos`) y el total `Patrimonio Fin del Periodo`.

### 3.4 p.2: Patrimonio por monedas / Patrimonio por tipo de producto
- **Por monedas:** columnas `Moneda | Monto | En pesos ($)`. Filas:
  - `Peso ($) y UF`: solo trae "En pesos".
  - `Dolar (USD)`: "Monto" en USD con 2 decimales, más "En pesos".
  - `Total`.
- **Por tipo de producto:** columnas `Activos | Monto ($) | Distribucion (%)`. Filas `Caja`, `Fondos mutuos`, `Fondos de inversión` (con tilde) y `Patrimonio Fin del Periodo`. Es una clasificación **distinta** de la "clase de activo": por ejemplo, un fondo de inversión de deuda va en `Renta fija` y también en `Fondos de inversión`.

### 3.5 CAJA
Encabezado: (rótulo sin título) `| Moneda de origen | Monto ($) | Distribucion (%)`. Filas:

- `Saldo Caja Peso`: "Moneda de origen" vacía.
- `Saldo Caja Dólar`: "Moneda de origen" en USD (`12,34`) y "Monto ($)" en CLP.
- `Total caja`.

El orden entre Peso y Dólar varía de un archivo a otro.

### 3.6 RENTA FIJA
Encabezado en 3 líneas:
`Nemotecnico | Descripcion | Moneda | Cantidad | Cotizacion compra | Cotizacion actual | Monto actual ($) | Fecha vencimiento | Duracion años | Rentabilidad (%) | Distribucion (%)`.
Cierra con la fila `Total renta fija` (Monto y Distribución). En esta muestra solo hay fondos (FM y FI), así que "Fecha vencimiento" y "Duracion años" vienen siempre vacías.

### 3.7 ALTERNATIVOS
Encabezado en 3 líneas:
`Nemotecnico | Descripcion | Moneda | Cantidad | Cotizacion compra | Cotizacion actual | Monto actual ($) | Rentabilidad (%) | Distribucion (%)`.
Cierra con la fila `Total alternativos`.

Notas comunes a RENTA FIJA y ALTERNATIVOS:

- **Cotizaciones:** van en la moneda del instrumento. `Monto actual ($)` siempre está en CLP.
- **Descripción:** ocupa una sola línea y **se trunca** si es larga (ej.: `FI Frontal Trust - Cordada Rendimiento con`). No hay descripciones de varias líneas.
- **Rentabilidad (%):** a veces viene vacía (25 de 53 filas). Se observó con variación 0 y con un fondo de variación muy negativa, mientras que otro fondo con una variación negativa pequeña sí la muestra. No hay que reconstruirla.
- **Posiciones de los archivos:** CFI-ALT2AE, CFI-FYNUAE, CFILVLEQ-E, CFI-TUSCBE, CFIBTGPLAA, CFIBTGCRPA, CFIBTGDEA, CFIFTCLP-E, CFILVD2L-E, CFIFALCFIA, CFILVCOR-A (FI), y USLVMONEY y FMLVAHORRO (FM).

### 3.8 MOVIMIENTOS DE CAJA EN PESOS / EN DOLAR
Encabezado: `Fecha | Referencia | Descripcion de movimiento | Nemo | Precio ($) | Cantidad | Cargo ($) | Abono ($) | Saldo en caja ($)`.

- La primera fila es `01/MM/AAAA  Saldo inicial  <saldo>` y la última `Saldo final  <saldo>` (sin fecha).
- Cada fila trae Cargo **o** Abono, y el saldo corrido.
- En la sección **EN DOLAR**, todas las columnas "($)" están en **USD**, con 2 decimales.
- Precio, Cantidad y Nemo solo vienen en compras o rescates de FM y en dividendos o disminuciones de capital (en estos últimos va solo el Nemo).
- Descripciones vistas: `Retiro fondo mutuo`, `Aporte fondo mutuo`, `Retiro fondo mutuo dolares`, `Venta de dolares formal` / `Venta dolares formal`, `Factura compra RV`, `Abono por disminucion de capital`, `Pago dividendo dolar cfi`, `Retiro de cta cte`.

### 3.9 MOVIMIENTOS DE TITULOS EN PESOS / EN DOLAR
Encabezado: `Fecha | Referencia | Descripcion de movimiento | Nemo | Precio ($) | Cantidad`.

- No trae monto, saldo ni total. En la sección EN DOLAR el precio va en USD.
- Descripciones vistas: `Compra RV`, `Ingreso RV`, `Retiro por disminucion de capital` (con Referencia `0`), `Aporte fondos mutuos` (en caja dice "fondo mutuo"), `Retiro fondo mutuo`.

### 3.10 GARANTIAS / INSTRUMENTOS EN GARANTIA
Encabezado: `Producto | Nemotécnico | Descripción | Cantidad en garantía | Total`.

- Ejemplo de fila: `Fondos de Inversion | CFI-TUSCBE | FI Toesca US Credit I, Serie B | 1.234,0000 | 1.234,0000`.
- Es **informativa**: esa misma cantidad ya está incluida en ALTERNATIVOS.

### 3.11 Tablas multipágina
No se observaron: la tabla más larga tiene 7 filas y cada subsección cabe en su página. No se sabe cómo continúa una tabla larga (si repite el encabezado o el subtítulo). El parser debe aceptar una página que empiece con el encabezado de tabla sin subtítulo, y validar contra la fila `Total …` o `Saldo final`.

---

## 4. Saldos y movimientos

| Aporta | Sección | Contenido |
|---|---|---|
| Saldo de caja | `CAJA` | Una línea por moneda (`Saldo Caja Peso` y `Saldo Caja Dólar`), con monto en moneda de origen y en CLP |
| Saldo de fondos de inversión | `RENTA FIJA` y `ALTERNATIVOS`, filas con nemo `CFI*` | Nemo, descripción, moneda, cantidad, cotización de compra y actual, monto en CLP |
| Saldo de fondos mutuos | `RENTA FIJA` y `ALTERNATIVOS`, filas sin prefijo `CFI` (FMLVAHORRO, USLVMONEY…) | Igual que la fila anterior |
| Totales de control | p.1 (clase de activo, evolución) y p.2 (monedas, tipo de producto) | Totales y flujos del mes y del año |
| Movimientos de caja | `MOVIMIENTOS DE CAJA EN PESOS/DOLAR` | Fecha, referencia, descripción, nemo, precio, cantidad, cargo, abono y saldo |
| Movimientos de títulos | `MOVIMIENTOS DE TITULOS EN PESOS/DOLAR` | Fecha, referencia, descripción, nemo, precio y cantidad |
| (Informativo) | `INSTRUMENTOS EN GARANTIA` | No suma: duplica una posición existente |

**Regla FI/FM verificada:** con "nemo empieza por `CFI`" = fondo de inversión y el resto = fondo mutuo, las sumas coinciden exacto con las filas `Fondos de inversión` y `Fondos mutuos` de la p.2 en 14 de 14 archivos.

No hay secciones de acciones, renta fija con vencimiento, internacional ni Pershing en esta muestra. La nota legal menciona a Pershing solo como fuente de precios.

---

## 5. Mapeo al formato de Example (export de BICE)

Abreviaturas: "Hdr" = encabezado de página, "Pie" = *Valores de referencia*, "Derivar" = se calcula a partir del PDF, "Sin fuente" = no está en el PDF.

### 5.1 SALDOS_CAJA (una fila por línea `Saldo Caja …`)
| Columna | Fuente |
|---|---|
| FechaProceso | Derivar: último día del `Periodo:` (ej. `Agosto 2026` → 2026-08-31). Confirmar con Felipe |
| RutCliente | Hdr `R.U.T. Cliente:`, sin puntos (`12345678-9`), DV en mayúscula |
| Cuenta | Hdr `Cuenta:` (siempre `0`) |
| Portafolio | **Sin fuente** (en BICE es "PORTAFOLIO N° k - AFITRADING…"). Requiere tabla RUT→portafolio o decisión |
| ProductoBase | Sin fuente → `CUENTA INVERSION` (no hay APV en estos informes) |
| Producto | Constante `CUENTAS CAJA` |
| MonedaValoracionPatrimonio | `CLP` para `Saldo Caja Peso`, `USD` para `Saldo Caja Dólar` |
| PatrimonioEnMonedaValoracion | Peso: `Monto ($)`. Dólar: `Moneda de origen` (USD) |
| patrimonioUSD | Derivar: USD de origen, o CLP / Dólar de referencia |
| patrimonioCLP | `Monto ($)` |
| TipoAPV, DescripcionTipoRegimenTributario | Vacíos (en BICE vienen vacíos para CUENTA INVERSION) |
| EnTransito | Sin fuente → `NO` |
| TipoCambioUSD / TipoCambioEUR | Pie: `Dolar $…` / `Euro $…` |

### 5.2 CUSTODIA_ACCIONES (fondos `CFI*`) y SALDOS_FFMM (FM), con las mismas 22 columnas
| Columna | Fuente |
|---|---|
| FechaProceso, RutCliente, Cuenta, Portafolio, ProductoBase | Igual que en 5.1 |
| Producto | CUSTODIA: `CFI` (igual que en BICE). FFMM: BICE usa `FONDOS MUTUOS BICE`, así que **hay que decidir** el valor para Larrainvial |
| Instrumento | `Descripcion` (truncada y en mayúsculas y minúsculas). Mejor usar un lookup por nemo: 7 de los 15 nemos de Larrainvial están en Example con su nombre oficial |
| NemotecnicoInstrumento | `Nemotecnico` |
| MonedaInstrumento | `Moneda` (CLP/USD) |
| Emisor | **Sin fuente**. Lookup por nemo (Example o CMF). Los fondos propios CFILV*, FMLV* y USLV* no están en Example |
| Cantidad | `Cantidad` |
| PrecioCierreEnMonedaValoracion | `Cotizacion actual` |
| PrecioPromedioCompra | `Cotizacion compra` |
| MonedaValoracionPatrimonio | `Moneda` |
| PatrimonioEnMonedaValoracion | CLP: `Monto actual ($)`. USD: derivar `Cantidad × Cotizacion actual` |
| patrimonioUSD | Derivar |
| patrimonioCLP | `Monto actual ($)` |
| TipoAPV, DescripcionTipoRegimenTributario | Vacíos |
| EnTransito | `NO` (las garantías no son "en tránsito") |
| TipoCambioUSD / EUR | Pie |

### 5.3 MOVIMIENTOS_DE_CAJA (excluir las filas `Saldo inicial` y `Saldo final`)
| Columna | Fuente |
|---|---|
| FechaProceso | `Fecha` del movimiento. En BICE es una sola fecha por export, así que **hay que confirmar** si se usa la fecha del movimiento o la de corte |
| RutCliente, Cuenta, Portafolio, ProductoBase | Igual que en 5.1 |
| Producto | Derivar: `CFI` si el Nemo es CFI (dividendo o disminución de capital, igual que BICE `DIVIDENDO EN DOLARES`). Si no, `CUENTAS CAJA` |
| Instrumento | Nemo si existe. Si no, `CAJA CLP` o `CAJA USD` según la sección (convención de BICE) |
| nombreTipoMovimiento | `Descripcion de movimiento` (posible mapeo al vocabulario de BICE, en mayúsculas) |
| Moneda | `CLP` en "EN PESOS", `USD` en "EN DOLAR" |
| abono / cargo | `Abono ($)` / `Cargo ($)`, en la moneda de la sección |
| TipoAPV, DescripcionTipoRegimenTributario | Vacíos |

### 5.4 MOVIMIENTOS_BOLSA (títulos con nemo `CFI*`: `Compra RV`, `Ingreso RV`, `Retiro por disminucion de capital`)
| Columna | Fuente |
|---|---|
| Instrumento, NemotecnicoInstrumento, MonedaInstrumento, Emisor | Nemo más lookup. La moneda sale de la sección (PESOS/DOLAR) |
| NombreTipoMovimiento | `Descripcion de movimiento`. `COMPRA RV` e `INGRESO RV` ya existen en el vocabulario de BICE |
| Moneda | Según la sección |
| Cantidad | `Cantidad` (positiva; el sentido lo da el tipo, igual que en BICE) |
| PrecioTIR | `Precio ($)` (en la moneda de la sección) |
| MontoNeto | **Sin columna en el PDF**. Hay dos opciones: derivar `Precio × Cantidad`, o tomar la `Factura compra RV` de caja por Referencia, que **incluye costos** (+1,2 % a +1,3 % observado). Hay que decidir cuál |

### 5.5 MOVIMIENTOS_FFMM (títulos FM: `Aporte fondos mutuos`, `Retiro fondo mutuo`)
Es igual que 5.4, con estas diferencias:

- `NumeroRerferencia` ← `Referencia`.
- `NombreTipoMovimiento`: mapear `Aporte…` → `INVERSION FM` y `Retiro…` → `RESCATE FM`.
- `MontoNeto` = `Precio × Cantidad`, que coincide exacto con el Cargo o Abono de caja de la misma Referencia.

MOVIMIENTOS_PERSHING no aplica a estos informes.

### 5.6 Cruce de RUT con `RutCliente` del export de BICE
- **Los 2 RUT** (ambos con DV módulo 11 válido) **aparecen** en `RutCliente`:
  - Cliente A: 13 filas en CUSTODIA_ACCIONES, 2 en SALDOS_CAJA y 1 en SALDOS_FFMM.
  - Cliente B: 5 + 1 + 1.
  - Ninguno de los dos tiene movimientos en el export.
- **Qué significa:** el anonimizador usa un mapeo consistente (el mismo RUT real da el mismo RUT ficticio), así que son **los mismos clientes de AFI Trading con cartera en ambos custodios**. El export de BICE contiene **solo lo custodiado en BICE**, en sus portafolios `PORTAFOLIO N° k - AFITRADING…`. Las posiciones de Larrainvial no están en el export: por ejemplo, el Cliente A tiene en BICE CFI-ALT2AE y CFI-FYNUAE con **cantidades distintas** a las de Larrainvial, y ninguno de los nemos propios de Larrainvial aparece.
- **Consecuencias:**
  1. El export sirve para validar que el RUT extraído existe y para heredar convenciones (Producto, Instrumento y Emisor por nemo; Cuenta `0`; ProductoBase `CUENTA INVERSION`).
  2. **No** sirve para validar montos ni cantidades: es otro custodio y otra fecha (22-09-2026 frente al último informe, ago-2026).
  3. Al consolidar, un mismo `RutCliente` tendrá filas de BICE y de Larrainvial, incluso con el mismo nemo. La clave debe incluir la institución (vía Portafolio, Producto u otra columna) para no deduplicar ni sumar por error. Esto hay que **preguntarlo a Felipe**.

---

## 6. Cuadraturas (probadas en los 14 archivos)

### 6.1 Internas (por archivo)
| Cuadratura | Resultado | Tolerancia |
|---|---|---|
| Inicio + Aportes + Retiros + Cambio Valor Cartera = Fin, en las 3 columnas (mes, año anterior, YTD) | 42/42 | ±1 CLP (redondeo) |
| Fin del mes = Fin YTD | 14/14 | Exacto |
| Σ clases de activo = Patrimonio Fin = Total de monedas = Total de tipo de producto | 14/14 | ±1 CLP |
| Σ Distribución (%) de clases = 100 | 14/14 | ±0,01 |
| `Dolar (USD)` Monto × Dólar de referencia = En pesos | 14/14 | ±5 CLP (USD con 2 decimales) |
| `Dolar (USD)` Monto = Σ(Cantidad × Cotización) de posiciones USD + caja USD | 14/14 | ±0,005 USD |
| `Peso ($) y UF` = Σ Monto de posiciones CLP + caja CLP | 14/14 | Exacto |
| Σ líneas de CAJA = `Total caja` = `Caja` de la p.1 | 14/14 | Exacto |
| `Saldo Caja Dólar` (origen) × Dólar de referencia = Monto ($) | 8/8 | ±5 CLP |
| **Cantidad × Cotización actual × (Dólar de referencia si es USD) = Monto actual ($)** | **53/53** | **≤0,5 CLP** (redondeo a entero) |
| Σ posiciones = `Total <clase>` = fila de la clase en la p.1 | 22/22 | ±1 CLP |
| Rentabilidad (%) = (Cot. actual / Cot. compra − 1) × 100, cuando viene | 28/28 | ±0,01 |
| Distribución (%) de la posición = Monto / Patrimonio total × 100 | 53/53 | ±0,01 |
| FI (`CFI*`) y FM suman `Fondos de inversión` y `Fondos mutuos` de la p.2 | 14/14 | ±1 CLP |
| Movimientos de caja: saldo anterior + Abono − Cargo = Saldo en caja (fila a fila) | 13/13 | Exacto (±0,01 en USD) |
| `Saldo final` = último saldo = `Saldo Caja <moneda>` (moneda de origen) de la sección CAJA | 5/5 | Exacto |
| Movimiento de caja de FM: Precio × Cantidad = Cargo o Abono | 6/6 | Relativa <2e-6 |
| Caja frente a títulos: `Abono por disminucion de capital` = Precio × Cantidad del título con **misma fecha y nemo** (la Referencia del título es `0`) | 1/1 | Exacto |
| Caja frente a títulos: `Factura compra RV` frente a Σ(Precio × Cantidad) de los títulos con la misma Referencia | No cuadra | La factura es 1,2–1,3 % mayor (comisión, derechos, IVA) |
| RUT con DV módulo 11 | 2/2 | — |

### 6.2 Entre meses (lo más valioso)
**Cliente A, 12 meses consecutivos:**

- **Patrimonio Fin del Periodo (m) = Patrimonio Inicio Periodo (m+1): 11 de 11 transiciones, diferencia 0 CLP.** Incluye los cruces provisorio→definitiva→provisorio.
- `Patrimonio Inicio` de la columna "Año 2026 (YTD)" = Fin de dic-2025: 8/8.
- Aportes, Retiros y Cambio YTD de 2026 = Σ mensual desde enero: 8/8 (±1 CLP). En 2025 no se puede verificar porque faltan los meses de enero a agosto.
- La columna "Año anterior" es idéntica en todos los meses del mismo año (2025: 4/4; 2026: 8/8).
- Saldo inicial de la caja en USD de los movimientos (m+1) = `Saldo Caja Dólar` (m): 2/2 (mar y may-2026). En los meses sin movimientos, la caja por moneda se mantiene igual.
- Cantidades por nemo: no cambian entre meses, salvo en mar-2026. Ahí el cambio (alza de un FI y rescate total de un FM) es exactamente el de los `MOVIMIENTOS DE TITULOS` de marzo.

**Cliente B:** de jun-2026 a ago-2026 **no cuadra**, porque Fin de junio ≠ Inicio de agosto. Además, los cambios de cartera (salida de FMLVAHORRO y CFI-TUSCBE, entrada de CFIFALCFIA y CFILVCOR-A) no se explican con los movimientos de agosto. Esto confirma que **falta julio**.

**Aportes y Retiros frente a movimientos** (mar-2026, Cliente A):

- `Aportes` = `Ingreso RV` (Cantidad × Precio en USD) × TC.
- `Retiros` = `Retiro de cta cte` (USD) × TC.
- Ambos implican **el mismo TC del día**, que no se imprime y es distinto del dólar de referencia de fin de mes. Con el dólar de referencia, la cuadratura solo da con una tolerancia de ~0,5 %.
- Dividendos (`Pago dividendo dolar cfi`), disminuciones de capital y compraventas internas **no** cuentan como Aportes ni Retiros: van a Cambio Valor Cartera.

---

## 7. Riesgos y particularidades

1. **Rotación:**
   - `page.get_text("words")` de PyMuPDF entrega coordenadas del espacio **sin rotar**, y `get_text()` entrega el orden del flujo de contenido.
   - `sort=True` sin derrotar ordena por columnas visuales, no por filas, y el resultado sale desordenado.
   - Hay que transformar con `page.rotation_matrix`, o usar `page.remove_rotation()` en memoria, o pdfplumber 0.11 / `pdftotext -layout`, que ya rotan.
2. **Texto anonimizado:**
   - Está en Helvetica, al final del flujo y con un tamaño distinto: el RUT es de 7,7 pt frente a 9 pt de la etiqueta y queda unos 2 pt más arriba. Agrupar las filas con una tolerancia de ±3 pt.
   - El nombre de la p.1 queda partido en fragmentos originales más uno reemplazado. Hay que unirlos por posición.
3. **Texto invisible (blanco):**
   - Los títulos "Rentabilidad" de la p.1 de todo provisorio.
   - En #14, restos del anonimizador (un fragmento de ciudad) a la izquierda de `Periodo:` en todas las páginas.
   - Si no se filtran (color `0xFFFFFF`), contaminan la línea `Periodo:`.
4. **"($)" engañoso:** en las secciones EN DOLAR, Precio, Cargo, Abono y Saldo están en USD.
5. **`100.00` con punto** en #14: el parser de números debe tolerarlo, o validar los porcentajes por suma.
6. **Descripciones truncadas:** usar el nemo como clave, nunca la descripción.
7. **Rentabilidad (%) a veces vacía:** no hay que tratarla como 0 ni reconstruirla.
8. **Página `MOVIMIENTOS` vacía** (#7 y #8). No implica que haya un error.
9. **Secciones opcionales:** el número de páginas varía entre 5 y 11, y el orden de las líneas de CAJA cambia. Siempre se deben detectar por título, nunca por número de página.
10. **Columnas casi fijas**, aunque ALTERNATIVOS se mueve unos 5 pt entre archivos. Conviene anclar por encabezado, usando el borde derecho para los números (que van alineados a la derecha).
11. **Referencias:** la Referencia del título puede ser `0` o distinta de la de caja (ventas de dólares, disminuciones de capital). Enlazar por Referencia y, si no hay coincidencia, por Fecha + Nemo.
12. **GARANTIAS** repite una posición ya informada. No hay que sumarla.
13. **Provisorio frente a definitiva:** el nombre de archivo no lo indica. En el futuro puede haber dos versiones del mismo mes, así que hay que deduplicar por (RUT, período).
14. **Período:** el nombre de archivo no es confiable (#1 es de 2025, #2 no trae mes). Leer el encabezado.
15. **Tipo de cambio:** el pie trae el dólar y el euro de fin de mes. Sirve para la valorización, pero no para reconciliar los Aportes y Retiros, que usan el TC del día.
16. **No vistos:** tablas multipágina, RENTA VARIABLE, INTERNACIONAL, EUR y bonos con vencimiento o duración. El extractor debe validar los totales y rechazar el archivo si algo no cuadra.
17. **Consolidación con BICE:** son los mismos RUT con carteras distintas (ver §5.6).

---

## 8. Enfoque recomendado de extracción

**Palabras con coordenadas de PyMuPDF, llevadas al espacio visual con `page.rotation_matrix`, filtrando el texto blanco, agrupadas en filas por la y del centro y con columnas ancladas a los encabezados.** Las razones:

- No hay líneas de tabla: `pdfplumber.extract_tables()` no encuentra tablas con la estrategia por defecto, y con la estrategia `"text"` corta palabras.
- Los valores anonimizados están fuera del orden de lectura, así que hace falta trabajar por posición.
- Los números van alineados a la derecha: se asignan a la columna cuyo borde derecho del encabezado esté más cerca. El texto se asigna por borde izquierdo.
- La detección de secciones usa el título de página (y≈86–88) y el subtítulo (y≈108–112). Para la fecha de emisión y los *Valores de referencia* basta una regex sobre `page.get_text()`.
- Todas las cuadraturas de §6 se pueden automatizar como pruebas de aceptación por archivo, más la continuidad entre meses cuando haya meses consecutivos.

Las alternativas válidas para inspeccionar son pdfplumber ≥0.11 (aplica `/Rotate` solo: `page.width` = 792, `chars[i]["upright"]` = True) y `pdftotext -layout`. Con este código mínimo, probado en los 14 archivos, se extrajo todo lo de §6:

```python
import pymupdf  # PyMuPDF 1.28

def palabras(page):
    """(x0, y0, x1, y1, texto) en coordenadas de la pagina TAL COMO SE VE (apaisada 792x612),
    sin el texto blanco/invisible."""
    M = page.rotation_matrix                      # espacio sin rotar -> espacio visual
    blancos = [pymupdf.Rect(s["bbox"]) for b in page.get_text("dict")["blocks"]
               for l in b.get("lines", []) for s in l["spans"] if s["color"] == 0xFFFFFF]
    out = []
    for x0, y0, x1, y1, txt, *_ in page.get_text("words"):
        r = pymupdf.Rect(x0, y0, x1, y1)
        if any(r in b for b in blancos):          # descarta texto invisible
            continue
        r = r * M                                  # aplica la rotacion de /Rotate 90
        out.append((r.x0, r.y0, r.x1, r.y1, txt))
    return out

def lineas(page, tol=3):
    """Agrupa palabras por fila visual (centro y) y las ordena por x."""
    filas = []
    for w in sorted(palabras(page), key=lambda t: ((t[1] + t[3]) / 2, t[0])):
        yc = (w[1] + w[3]) / 2
        if filas and abs(filas[-1][0] - yc) <= tol:
            filas[-1][1].append(w)
        else:
            filas.append([yc, [w]])
    return [(yc, sorted(ws)) for yc, ws in filas]

doc = pymupdf.open(ruta_pdf)
for yc, ws in lineas(doc[0]):
    print(f"{yc:6.1f}  " + " ".join(w[4] for w in ws))
# -> "R.U.T. Cliente: <RUT> <NOMBRE>", "Periodo: Agosto 2026 <DIRECCION>", ...
```

Equivalente en pdfplumber, que ya entrega coordenadas rotadas; solo hay que filtrar el blanco:

```python
import pdfplumber
with pdfplumber.open(ruta_pdf) as pdf:
    p = pdf.pages[0]                                   # p.width == 792, p.rotation == 90
    vis = p.filter(lambda o: not (o.get("object_type") == "char"
                   and tuple(o.get("non_stroking_color") or ()) in ((1,), (1, 1, 1))))
    palabras = vis.extract_words()                     # x0, x1, top, bottom ya en espacio visual
```

Pasos sugeridos del extractor:

1. Leer el encabezado: RUT, período y cuenta, tomando el valor a la derecha de la etiqueta en la misma fila. Leer el título para saber si es provisorio o definitiva. Leer el pie para el dólar, el euro y la UF.
2. En la p.1 y la p.2, leer las tablas resumen por rótulo de fila.
3. En cada página de detalle:
   - Tomar el subtítulo.
   - Reunir las filas de encabezado hasta la primera fila con números o fechas, y armar las columnas con las frases conocidas (los encabezados de 2–3 líneas se unen por solape en x).
   - Asignar las palabras de cada fila.
   - Cortar en `Total …` o en `Saldo final`.
4. Clasificar cada posición en FI (`CFI*`) o FM y mapearla según §5.
5. Correr las cuadraturas de §6.1 y, si existe el mes anterior del mismo RUT, las de §6.2.

---

## 9. Extractor (`skill/cartolas/extractores/larrainvial.py`)

**Reconocimiento.** Todas las páginas, si el PDF trae `www.larrainvial.com` y el título `INFORME PROVISORIO PATRIMONIAL` o `CARTOLA PATRIMONIAL`. Lo provisorio queda marcado en la cartola: si llegan las dos versiones de un mismo cliente y período, el programa usa la definitiva y deja la provisoria en el reporte.

**Qué se exporta** (juego de archivos `*_LARRAINVIAL_<fecha>_V2.csv`, con la fecha del último cierre):

- Cuenta `0`, CUENTA INVERSION, sin portafolio. Período del 1 al último día del mes de `Periodo:`; tipo de cambio USD y EUR del pie.
- SALDOS_CAJA: las líneas `Saldo Caja Peso|Dólar` distintas de cero.
- CUSTODIA_ACCIONES: los nemotécnicos `CFI*` de RENTA FIJA y ALTERNATIVOS. SALDOS_FFMM: el resto (fondos mutuos de Larrainvial), con producto `FONDOS MUTUOS` mientras no se decida otro. En USD, el patrimonio en dólares es cantidad × cotización.
- MOVIMIENTOS_DE_CAJA: la descripción se lleva al vocabulario del export cuando es inequívoca (`TIPOS_CAJA`: factura de compra RV, dividendo en dólares, venta de dólares, aporte y rescate de fondos mutuos); el resto va en mayúsculas.
- MOVIMIENTOS_FFMM / _BOLSA (`TIPOS_TITULOS`): aporte y rescate de fondos mutuos; compra RV, ingreso RV y disminución de capital. El informe no trae el monto: se calcula como precio × cantidad, igual que el MontoNeto de COMPRA RV en el export de BICE. Las facturas de caja de las compras son 1,2 % a 1,3 % mayores (comisión, derechos e IVA) y quedan como aviso.
- Las garantías no son posiciones nuevas: solo se controla que el instrumento esté en cartera.

**Cuadraturas:** las internas de §6.1, más el dígito verificador del RUT, las garantías y que precio × cantidad de los fondos mutuos coincida con la caja de la misma referencia. La de entre meses (§6.2) está en las pruebas.

**Resultado en los 14 informes** (12 provisorios y 2 definitivos): 398 cuadraturas, todas cierran, y el patrimonio final de cada mes es el inicial del siguiente en las 11 transiciones del cliente con meses seguidos. Se leen 53 posiciones (46 CFI y 7 fondos mutuos), 21 saldos de caja, 13 movimientos de caja y 13 de títulos. 30 de las 53 posiciones están en la tabla maestra por nemotécnico; los fondos propios de Larrainvial (`CFILV*`, `FMLV*`, `USLV*`) y `CFIFALCFIA` no, y salen sin emisor.
