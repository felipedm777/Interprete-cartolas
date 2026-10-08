# Inventario de layout: Sura (cartola mensual de Corredores de Bolsa SURA)

Alcance: los 7 PDF de `Training Data/Sura/` cuyo nombre **no** contiene "pershing". El estado de cuenta `Sura pershing-...` es otro formato (Pershing LLC) y está documentado en `pershing.md`; aquí solo se explica cómo se relaciona con la cartola Sura.

Todos los números de ejemplo de este documento son sintéticos (1.234.567, 9,9999, etc.). No hay datos de clientes.

---

## 1. Archivos

Los nombres de archivo contienen nombres de clientes (ficticios), así que los identifico como S1–S7: el orden es el de Python `sorted()` sobre los nombres, excluyendo el de Pershing. El tamaño en bytes permite reconocerlos sin abrir el nombre.

| Id | Patrón de nombre | Bytes | Págs | Qué contiene (con datos) | ¿Movimientos? |
|---|---|---|---|---|---|
| S1 | `SURA-Agosto-<cliente>.pdf` | 224.384 | 5 | Financieras: Fondos de Inversión (CLP y USD), Caja CLP, Caja USD | Sí: compra de FI y caja (dividendo, abono, factura) |
| S2 | `SURA-Agosto-<cliente>.pdf` | 221.740 | 5 | Financieras: 1 Fondo Mutuo | No |
| S3 | `SURA-Agosto-<cliente>.pdf` | 224.066 | 6 | Previsionales: FM (BON_F, CVN_A) y Financieras: 5 FM | Sí: 4 aportes a FM |
| S4 | `SURA-Agosto-<cliente>.pdf` | 225.102 | 5 | Previsionales: FI, FM, 3 cajas CLP (una por régimen) y 2 cajas USD | Sí: aporte y venta de FM, rescate de FI, caja CLP y USD |
| S5 | `SURA-Agosto-<cliente>.pdf` | 61.772 | 5 | Previsionales (DCR): Acciones, FI, FM, Caja CLP, Caja USD | Sí: solo caja (dividendos, abono) |
| S6 | `Sura-Agosto-<iniciales>.pdf` | 222.449 | 5 | Financieras: 2 FM (uno en USD) | Sí: 2 "Aporte por Reparto" |
| S7 | `Sura-Agosto-<iniciales>.pdf` | 223.469 | 6 | Previsionales: 1 FM; Financieras: 1 FM y Caja CLP | No |

- **Rango de páginas**: entre 5 y 6. La última página es siempre de texto legal y glosario.
- **Período**: los 7 cubren `PERÍODO 01/08/2026 - 31/08/2026`. Los saldos comparativos son "del 31/07/2026" y "del 31/08/2026".
- **Fecha de emisión**: no está impresa. El texto legal habla de "fecha de su emisión", pero no la muestra, y los metadatos del PDF están vacíos (sin creator, producer ni fechas).
- **Moneda del reporte**: CLP. Hay bloques aparte en USD ("Instrumentos en Dólar", "Detalle de Inversiones ... USD", "Cuentas de Inversiones USD") que solo aparecen cuando hay caja en dólares. Los instrumentos denominados en USD (FI o FM) se informan dentro del bloque CLP, valorizados en pesos.
- **Página**: 612 × 792 pt (Carta vertical) y rotación 0 en todas las páginas.
- **Texto**: extraíble; no hay escaneos. Fuentes TrebuchetMS y TrebuchetMS-Bold (subconjuntos). Cada página trae una sola imagen, el logo arriba a la derecha (x≈397–550, y≈18–79). El texto anonimizado está en Helvetica de 8–9 pt (en un caso 7,6 pt, achicado para que quepa) y aparece al final del orden de texto de la página 1.
- **Dos variantes de plantilla** con coordenadas idénticas:
  - Variante A (S1–S4, S6, S7): el subtítulo en y≈44 es `Cartola Mensual` (repetido) y el período dice `PERÍODO`, con tilde.
  - Variante B (S5): el subtítulo es `Corredores de Bolsa SURA S.A.`, el período dice `PERIODO` sin tilde, el archivo pesa ~4 veces menos y el logo es levemente más ancho. Cambian además algunas mayúsculas en etiquetas, por ejemplo `SUBTOTAL Cuenta de Inversiones USD` frente a `... inversiones USD`.
- **Duplicados**: no hay. Los SHA-256 son distintos, y comparando el contenido sin el texto anonimizado la similitud máxima es 0,96 (S2 frente a S6). Esa similitud viene de que ambos usan la misma plantilla con páginas vacías ("No se registran movimientos"); los instrumentos y los montos son distintos.

---

## 2. Estructura del documento

Orden de páginas, que es fijo; cada bloque empieza en página nueva:

| # | Página / bloque | ¿Siempre? | Cómo se identifica |
|---|---|---|---|
| 1 | Encabezado del cliente, `Resumen de Saldos por Instrumento`, `Instrumentos en Dólar` (subbloque USD del resumen) y `Resumen de Movimientos` | Siempre en la pág. 1. El subbloque USD solo aparece si hay caja USD (S1, S4, S5) | Títulos en TrebuchetMS-Bold de 10 pt en x≈20 |
| 2 | `Detalle de Inversiones Previsionales` (+ `Detalle de Inversiones Previsionales USD`) | Solo si hay saldos previsionales (S3, S4, S5, S7) | Título en x≈20 bajo el encabezado de página |
| 3 | `Movimientos Inversiones Previsionales` con 4 bloques: `Aportes/Compras`, `Rescates/Ventas`, `Cuentas de Inversiones`, `Cuentas de Inversiones USD` | **Siempre**, aunque esté vacío ("No se registran movimientos para el período") | Igual |
| 4 | `Detalle de Inversiones Financieras` (+ `Detalle de Inversiones Financieras USD`) | Solo si hay saldos financieros (S1, S2, S3, S6, S7) | Igual |
| 5 | `Movimientos Inversiones Financieras` (los mismos 4 bloques) | **Siempre** | Igual |
| 6 | Texto legal y `Glosario:` | Siempre, en la última página | Línea `Glosario:` |

Encabezado de todas las páginas: `Cartola Mensual` (19 pt, y≈23), el subtítulo (y≈44) y `PER[IÍ]ODO dd/mm/aaaa - dd/mm/aaaa` (y≈60). Pie de página: `600 600 7872`, `Página N de M`, `sura.cl` (y≈765).

Grupos de instrumentos (subtítulos en x≈25, en negrita) que se observaron:
- En el Detalle, en este orden: `Acciones` → `Fondos de Inversión` → `Fondos Mutuos` → `Cuenta de Inversiones`. En el bloque USD el grupo es `Cuentas Inversiones USD`.
- En el Resumen de Saldos, en otro orden: `Fondos Mutuos`, `Fondos de Inversión`, `Cuenta de inversiones` (con "i" minúscula), `Acciones`, `Total`. En el bloque USD: `Cuentas de Inversión USD`, `Total USD`.
- En Movimientos: `Fondos Mutuos`, `Fondos de Inversión` y también **`Fondo de Inversiones`**, una variante del mismo grupo (S1).

---

## 3. Detalle por sección

### 3.1 Encabezado del cliente (pág. 1)

| Etiqueta (x≈33) | y aprox. | Valor |
|---|---|---|
| `Cliente:` | 104–112 | Nombre del cliente, desde x≈68 hasta ~300. Puede venir en varios spans con fuentes distintas: en S1 la razón social "Inversiones <X> Spa" quedó en 3 trozos (2 en Trebuchet y 1 en Helvetica). Hay que concatenar todas las palabras de la franja ordenadas por x |
| `Asesor(a):` | 123–129 | `Bkr - <NOMBRE ASESOR>` (x≥80). Es el mismo asesor en los 7 archivos |
| `Mail:` | 145–150 | Un email (x≥57) que es **el mismo en los 7 archivos**: es del asesor, no del cliente |
| `Teléfono:` (x≈312) | 146 | `0` en los 7 archivos |

**No hay RUT ni número de cuenta en ninguna parte de la cartola Sura.** Las notas previas hablan de una cuenta "TD9-999999", pero esa cuenta **no aparece en estos 7 PDF**: es el número de cuenta del estado Pershing (ver §5.0).

### 3.2 Resumen de Saldos por Instrumento (pág. 1)

- Encabezados en dos niveles. Arriba: `Inversiones Previsionales` | `Inversiones Financieras` | `Inversión Total` (en el bloque USD: `Inversiones Totales`). Abajo, bajo cada grupo: `del 31/07/2026` | `del 31/08/2026`. La primera columna se titula `Instrumento`, o `Instrumentos en Dólar` en el bloque USD.
- **Trampa**: en el orden de texto los encabezados salen como "del 31/08" y luego "del 31/07", pero visualmente el 31/07 (mes anterior) está a la **izquierda** y el 31/08 (cierre) a la **derecha**. Los valores siguen el orden visual. Si se emparejan encabezados y valores por orden de texto, las fechas quedan invertidas. Hay que usar coordenadas.
- Bordes derechos de las 6 columnas de valores: ≈225, 294, 364, 433, 504 y 574.
- Formato: `$1.234.567`, entero en CLP con punto de miles; en el bloque USD, `US$1.234,56`.
- Filas: una por tipo de instrumento y luego `Total` (o `Total USD`).

### 3.3 Resumen de Movimientos (pág. 1)

- Columnas: `Movimientos` | `Inversiones Previsionales` | `Inversiones Financieras` | `Inversión Total`, con bordes derechos ≈295, 434 y 573.
- Filas: `Saldo Inicial 01/08/2026`, `Abonos`, `Cargos`, `Utilidad o Pérdida`, `Saldo Final 31/08/2026`.
- Negativos con el signo después del símbolo: `$-1.234.567`.
- La semántica de Abonos y Cargos no se deduce de forma fiable del detalle:
  - En S1, Abonos es igual al "Abono a Cuenta de Inversiones" de la caja.
  - En S3, Abonos es la suma de los "Aporte Fondos" a FM.
  - En S4, Cargos es igual al "Rescate Custodia" de un FI en USD (con ±1 de diferencia).
  - En S5 hay un "Abono a Cuenta de Inversiones" en caja y aun así Abonos = 0.
  - Conclusión: usar esta tabla solo para cuadrar (§6).

### 3.4 Detalle de Inversiones Previsionales / Financieras (CLP)

Encabezados exactos, de 3 líneas apiladas: `Instrumento` | `Serie` | `Régimen Tributario` | `Moneda de Origen` | `Cantidad / N° de Cuotas` | `Precio / Valor Cuota` | `Tipo Cambio Observado` | `Saldo en CLP`.

| Columna | x (pymupdf) | Formato |
|---|---|---|
| Instrumento | x0 30–165 | Texto. **Puede ocupar 2 líneas**: la segunda queda +8 pt más abajo y la línea de datos se corre +2 pt respecto de la primera línea del nombre |
| Serie | x0 164–185 | `-` en FI, Acciones y Caja; una letra en FM (`A`, `C`, `D`). **En FI la serie viene dentro del nombre** ("... Serie A", "... Fully Fund A", "... FOGAPE", "... Priv Eq B", "... I"), casi siempre en la segunda línea |
| Régimen Tributario | x0 200–240 | Código: `18Q`, `18T`, `BON_F`, `CVN_A`, `CVN_B`, `DCN`, `DCR` |
| Moneda de Origen | x0 255–300 | `CLP` / `USD` |
| Cantidad | borde der. ≈357 (Financieras) / ≈365 (Previsionales) | `1.234,5678` (4 decimales). En acciones también lleva 4 decimales |
| Precio / Valor Cuota | borde der. ≈431 / ≈436 | `$1.234,5678`. **Lleva `$` aunque el precio esté en USD**; la moneda la da "Moneda de Origen". En caja es `$1,0000` |
| Tipo Cambio Observado | borde der. ≈493 / ≈501 | `$999,99` solo en filas USD; `-` en CLP |
| Saldo en CLP | borde der. ≈575 | `$1.234.567` (entero) |

- Las columnas de la sección Previsionales están corridas unos 5–8 pt a la derecha respecto de Financieras, con los encabezados en la misma posición. Conviene asignar por rangos o por el centro más cercano, no por x exacto.
- Filas de cierre:
  - `SUBTOTAL <grupo>`, con el valor en el borde der. ≈575.
  - `TOTAL INVERSIONES PREVISIONALES` o `TOTAL INVERSIONES FINANCIERAS`.
- Valores ausentes. En S1 hay un FI recién comprado con Cantidad, pero con Precio `-`, TC `-` y **sin Saldo**, ni siquiera un `-`; el SUBTOTAL lo excluye. También un FM aparece dentro del grupo `Fondos de Inversión` (S5: "Fondo Mutuo LarrainVial Enfoque").

### 3.5 Detalle de Inversiones ... USD

- Mismo encabezado, salvo que la primera columna es `Instrumentos en Dólar` y la última `Saldo en USD`.
- Solo trae `Caja USD`, una fila por régimen:
  - Cantidad: monto en USD con 2 decimales (`1.234,56`).
  - Precio: `US$1`.
  - TC: `-`.
  - Saldo: `US$1.234,56`.
- Cierre: `SUBTOTAL Cuenta de inversiones USD` (o `... Inversiones USD`), y luego `TOTAL INVERSIONES PREVISIONALES USD` o `... FINANCIERAS USD`.

### 3.6 Movimientos: Aportes/Compras y Rescates/Ventas

Encabezados exactos: `Instrumento` | `Fecha` | `Concepto` | `Serie` | `Régimen Tributario` | `Moneda de Origen` | `Cantidad / N° de Cuotas` | `Precio / Valor Cuota` | `Tipo Cambio Operación` | `Monto en CLP`.

| Columna | x |
|---|---|
| Instrumento | x0 30–125, 1 o 2 líneas. Cuando son 2, la línea de datos queda ~3,5 pt **por debajo** de la primera línea del nombre y la segunda línea queda ~4,6 pt por debajo de los datos |
| Fecha | x0 127–164, `dd/mm/aaaa` |
| Concepto | x0 167–235. Puede ocupar 2 líneas (`Aporte FFMM de` / `Cta Inversión`) |
| Serie | x0 236–255 (`-` o letra) |
| Régimen | x0 255–300 (`18Q`, `R.GRAL`, `18T`, `CVN_B`...) |
| Moneda | x0 300–345 |
| Cantidad | borde der. ≈405 |
| Precio | borde der. ≈458–461 |
| TC Operación | borde der. ≈492–520 (`-` o `$999,99`) |
| Monto en CLP | borde der. ≈575. **Puede venir vacío**: en S6, un "Aporte por Reparto" por una fracción ínfima de cuota no trae monto |

- Grupos (x≈25): `Fondos Mutuos`, `Fondos de Inversión` / `Fondo de Inversiones`.
- Cierre: `TOTAL APORTES/COMPRAS` y `TOTAL RESCATES/VENTAS`. En la página de Financieras, la fila TOTAL RESCATES/VENTAS trae un token `$` suelto en x≈523 antes del valor, así que hay que tomar el token más a la derecha.
- Vacío: `No se registran movimientos para el período` + `TOTAL ... $0`.
- Conceptos observados:
  - Aportes/Compras: `Compra RV` (FI), `Aporte Fondos`, `Aporte FFMM de Cta Inversión`, `Aporte por Reparto` (FM).
  - Rescates/Ventas: `Venta por Acciones` (FM), `Rescate Custodia` (FI en USD).

### 3.7 Movimientos: Cuentas de Inversiones / Cuentas de Inversiones USD

- Encabezado impreso (en orden visual): `Operación` | `Fecha` | `Concepto` | `Régimen Tributario` | `Moneda` | `Cargo` | `Abono` | `Saldo`. **Los encabezados no calzan con los datos.** El orden real de los datos es:
  - [Concepto descriptivo, x0 30–135, p. ej. "Dividendo en Pesos"]
  - [Fecha, x0 141–177]
  - [Operación `Abono`/`Cargo`, x0 180–199]
  - [Régimen, x0 250–285]
  - [Moneda, x0 302–330]
  - [Cargo, borde der. ≈417]
  - [Abono, borde der. ≈488]
  - [Saldo, borde der. ≈577]
- Filas: `Saldo Inicial`, luego las de movimiento, `Saldo Final` y `Saldo en Garantía` (siempre 0 en las muestras).
- Montos: `$1.234.567` o `US$1.234,56`. En la columna que no aplica aparece `$0` / `US$0,00`, no vacío.
- **La columna Saldo es un saldo corrido por régimen tributario, no el saldo total de la caja.** En S4 parte desde el saldo de la sub-caja CVN_B, no del total. En S1 parte desde 0, porque los movimientos usan `R.GRAL` y la tenencia `18Q`, y llega a quedar negativa (`$-1.234.567`). No sirve como saldo de caja. Lo que sí se cumple es saldo_i − saldo_{i−1} = abono − cargo.
- Conceptos observados:
  - CLP: `Dividendo en Pesos`, `Abono a Cuenta de Inversiones`, `Factura Compra RV`, `Retiro desde Cta Inversión`, `Abono a Cta Inv SURA x Rescate`.
  - USD: `Abono USDs desde Cuenta`.

### 3.8 Página legal / Glosario

Glosario de regímenes: `CVA_B`, `CVN_A`, `CVN_B` (cotización voluntaria antigua/nueva, régimen A/B), `BON_F` (Bonificación Fiscal), `DCA`, `DCN`, `DCR` (depósito convenido antiguo/nuevo/reconstrucción), `RTN` (régimen normal), `57B`, `57T` (57 bis y transitorio) y `18Q` (régimen general art. 108 LIR).

En los datos aparecen además `R.GRAL` (régimen general, solo en movimientos) y `18T`, que **no está en el glosario**: probablemente es el ex art. 18 ter / art. 107 LIR, aplicado a FM accionarios, pero hay que confirmarlo.

El texto legal dice además que las fechas de movimientos son la "fecha de valor cuota" y que los saldos en moneda extranjera se valorizan "al tipo de cambio del último día del mes".

### 3.9 Tablas que cruzan páginas

No se observó ninguna. Cada sección cabe en su página; la más larga es el Detalle Previsional de S4, con 14 filas. Igual hay que mantener el estado de sección entre páginas por si una cartola grande desborda.

---

## 4. Saldos y movimientos

**Productos encontrados** (solo los nombres de los instrumentos, que pueden publicarse):
- Fondos Mutuos (SURA AGF): SURA Renta Depósito Chile, SURA Renta Bonos Chile, SURA Renta Corporativa Largo Plazo, SURA Selección Acciones Chile, SURA Selección Acciones USA, SURA Selección Global, SURA Multiactivo Agresivo / Moderado / Prudente y SURA Cartera Patrimonial Conservadora, en series A, C y D.
- Fondo internacional distribuido: JP Morgan Emerging Markets Equity (serie D, USD).
- Fondos de Inversión:
  - Ameris: Alternativos I, Alternativos II, DP con Garantía FOGAPE, Deuda Directa C, Financ Acceso a Vivienda C, NM Guardian III.
  - Security Pantheon Sec Fully Fund A.
  - FYNSA Galgo II y Galgo III, serie C.
  - Singular: Leaseback II A y Residential MBS I.
  - Toesca Deuda Privada A y F.
  - Falcom Port Adv MVP Priv Eq B.
  - SURA Real Estate Global A (solo en un movimiento).
  - "Fondo Mutuo LarrainVial Enfoque", listado dentro del grupo FI.
  - Hay FI en CLP y en USD.
- Acciones nacionales: LTM y QUINENCO, ambas dentro de APV (régimen DCR).
- Caja CLP y Caja USD, con una fila por régimen.
- **No aparecen** seguros con ahorro, renta fija directa (bonos, depósitos), ETF ni custodia internacional. Lo internacional se reduce a FI y FM denominados en USD. La custodia en EE.UU. está en el estado Pershing aparte y **no** se suma en la cartola Sura.

| Sección del PDF | Aporta | Columnas útiles |
|---|---|---|
| Detalle ... grupo `Fondos Mutuos` | Saldos de FFMM | Instrumento, Serie, Régimen, Moneda, Cantidad, Precio, TC, Saldo CLP |
| Detalle ... grupos `Fondos de Inversión` y `Acciones` | Custodia (CFI y acciones) | ídem |
| Detalle ... `Cuenta de Inversiones` y `Cuentas Inversiones USD` | Saldos de caja CLP y USD, por régimen | Régimen, Moneda, Cantidad (= saldo), Saldo |
| Movimientos ... `Aportes/Compras` y `Rescates/Ventas`, grupo FM | Movimientos de FFMM | Fecha, Concepto, Instrumento, Serie, Régimen, Moneda, Cantidad, Precio, TC Op., Monto CLP |
| Movimientos ... `Aportes/Compras` y `Rescates/Ventas`, grupo FI/Acciones | Movimientos de bolsa | ídem |
| Movimientos ... `Cuentas de Inversiones` y `... USD` | Movimientos de caja | Concepto, Fecha, Operación, Régimen, Moneda, Cargo, Abono (Saldo corrido no) |
| Resumen de Saldos / Resumen de Movimientos | Solo validación | Totales por tipo y por segmento; SI, Abonos, Cargos, Utilidad, SF |

Movimientos del período: hay movimientos en S1, S3, S4, S5 y S6; S2 y S7 no tienen ninguno. Con el parser de prueba se contaron 45 filas de saldo, 10 movimientos de títulos y 15 de caja en total.

La previsional/financiera de cada fila sale de la sección (`... Previsionales` / `... Financieras`). El régimen tributario va por fila.

---

## 5. Mapeo al formato de Example

### 5.0 Identificación del cliente (RutCliente, Cuenta) y relación con Pershing

- La cartola Sura **solo trae el nombre del cliente** (`Cliente:`). No trae RUT, número de cuenta ni email o teléfono del cliente: el email y el teléfono del encabezado son del asesor y `0`.
- Busqué los 7 nombres en los 51 PDF de las otras instituciones y no aparecen en ninguno. Tampoco hay una ruta indirecta (por ejemplo, un cartola BICE del mismo cliente ficticio) para obtener el RUT.
- El nombre de archivo trae un nombre corto, solo el nombre de pila o iniciales. No sirve como clave.
- **RutCliente: sin fuente.** Hace falta una tabla maestra que mantenga Felipe (nombre normalizado → RUT, Cuenta, Portafolio y, si corresponde, cuenta Pershing). El match tiene que normalizar mayúsculas, tildes y espacios, y aceptar razones sociales ("Inversiones <X> Spa").
- **Cuenta: sin fuente.** BICE usa enteros por producto (0–9 para CUENTA INVERSION, 80+ para APV FFMM, 90+ para APV PRIME). Para Sura hay que fijar una convención, por ejemplo 0 para Financieras y otra para Previsionales, o tomarla de la tabla maestra.
- **Relación con `Sura pershing-...`**:
  - Es el estado de Pershing LLC del **mismo cliente que S5**: el nombre coincide, en mayúsculas y sin tildes.
  - Ahí sí aparece `Número de Cuenta: TD9-<CUENTA>`, que es la cuenta Pershing y llenaría `CuentaPershing` en MOVIMIENTOS_PERSHING. No es una cuenta Sura.
  - Tampoco trae RUT. Trae el código de asesor (las mismas iniciales del email del asesor de la cartola Sura).
  - La cartola Sura de S5 **no** incluye lo custodiado en Pershing (no hay ninguna fila "internacional" equivalente), así que no hay doble conteo. Hay que procesar ambos y ligarlos por nombre o por la tabla maestra.

### 5.1 Columnas comunes

| Columna destino | Fuente en el PDF Sura |
|---|---|
| FechaProceso | Fin del `PERÍODO` (31/08/2026 → `2026-08-31`). En movimientos queda por decidir si va la fecha del movimiento (columna Fecha) o la del cierre; el Example es un export diario y no lo aclara |
| RutCliente | **Sin fuente**: tabla maestra por nombre |
| Cuenta | **Sin fuente**: convención o tabla maestra |
| Portafolio | **Sin fuente** (`PORTAFOLIO N° k - AFITRADING ASESORIA FINANCIERA - <sufijo>`). El sufijo se puede derivar del régimen (S, CV-A-S, CV-B-S, DC-S...), pero el número k no |
| ProductoBase | Se deriva de la sección: Financieras → `CUENTA INVERSION`; Previsionales → APV. Falta decidir el nombre: BICE usa `APV FFMM` para FM y `APV PRIME` para caja y custodia |
| TipoAPV | Se deriva del Régimen (propuesta, a confirmar): `CVN_A`/`CVN_B`/`CVA_B` → `CV`; `DCA`/`DCN`/`DCR` → `DC`; `BON_F` → ¿`DAPVC`/`DAPV`? (en BICE "BF ..." aparece con DAPVC); `18Q`, `R.GRAL`, `18T`, `RTN`, `57B`, `57T` → vacío |
| DescripcionTipoRegimenTributario | En el Example se observa: sufijo -A- → `APORTE`, -B- → `BONIFICACIÓN`, DC → `BONIFICACIÓN`. Para Sura: `*_A` → `APORTE`, `*_B` → `BONIFICACIÓN`, `DC*` → `BONIFICACIÓN`, `BON_F` → a confirmar, régimen general → vacío |

### 5.2 SALDOS_FFMM (grupo `Fondos Mutuos`) y CUSTODIA_ACCIONES (grupos `Fondos de Inversión` y `Acciones`)

| Columna | Fuente / regla |
|---|---|
| Producto | FM → a definir (BICE usa `FONDOS MUTUOS BICE`); FI → `CFI`; Acciones → `ACCIONES` (igual que BICE en CUSTODIA_ACCIONES) |
| Instrumento | Nombre del instrumento (unir las 2 líneas) más la Serie (en FM, de la columna Serie; en FI, viene dentro del nombre). Conviene normalizar al estilo BICE (`FI AMERIS ALTERNATIVOS II SERIE A`) |
| NemotecnicoInstrumento | **Sin fuente.** En acciones el nombre es el nemo (LTM, QUINENCO). En FI se puede usar un catálogo: varios FI de Sura están en CUSTODIA_ACCIONES del Example con nemo y emisor (Ameris Alternativos I/II, FYNSA Galgo II/III, Toesca Deuda Privada A/F, Singular Residential MBS I, Ameris NM Guardian III, Security Pantheon...). Los FM SURA no están en el Example; harían falta CMF u otra fuente |
| MonedaInstrumento | `Moneda de Origen` |
| Emisor | **Sin fuente**; se deriva del nombre con un catálogo (SURA AGF, Ameris, Toesca, FYNSA, Singular, Security, Falcom, LarrainVial, JP Morgan) |
| Cantidad | `Cantidad / N° de Cuotas` |
| PrecioCierreEnMonedaValoracion | `Precio / Valor Cuota`, en la moneda de origen (igual que BICE con CFI en USD dentro de APV) |
| PrecioPromedioCompra | **Sin fuente** (Sura no informa costo) |
| MonedaValoracionPatrimonio | `CLP`, porque el saldo viene en CLP. Para instrumentos USD falta decidir si se informa en USD (Cantidad × Precio) como hace BICE en Cuenta Inversión |
| PatrimonioEnMonedaValoracion | `Saldo en CLP` (o el valor en USD si se elige USD) |
| patrimonioCLP | `Saldo en CLP` |
| patrimonioUSD | Se deriva: Saldo CLP / TC |
| EnTransito | No hay campo; `NO` por defecto. El texto legal define "Saldo en Tránsito", pero no aparece en ninguna cartola |
| TipoCambioUSD | `Tipo Cambio Observado` de cualquier fila USD de la cartola. Si no hay filas USD (S2, S3, S7) → **sin fuente**: dólar observado externo del último día del mes |
| TipoCambioEUR | **Sin fuente** |

Caso especial: un FI con Cantidad pero sin Precio ni Saldo (S1). Hay que decidir si se exporta con patrimonio vacío o 0, o si se omite.

### 5.3 SALDOS_CAJA

| Columna | Fuente |
|---|---|
| Producto | `CUENTAS CAJA` |
| MonedaValoracionPatrimonio | `CLP` (grupo `Cuenta de Inversiones`) o `USD` (`Cuentas Inversiones USD`) |
| PatrimonioEnMonedaValoracion | `Saldo en CLP` / `Saldo en USD` de la fila `Caja` / `Caja USD`. Hay una fila por régimen (S4 tiene 3 cajas CLP y 2 USD), que se corresponden con filas o portafolios distintos |
| patrimonioCLP / patrimonioUSD | Para CLP: saldo y saldo/TC. Para USD: saldo×TC y saldo. El TC no siempre está en el PDF |
| EnTransito | `NO`. `Saldo en Garantía` (pág. de movimientos) existe, pero es otra cosa y vale 0 en todas las muestras |
| TipoCambioUSD / EUR | Igual que en §5.2 |

### 5.4 MOVIMIENTOS_DE_CAJA (bloques `Cuentas de Inversiones` y `... USD`, sin las filas Saldo Inicial/Final/Garantía)

| Columna | Fuente |
|---|---|
| Producto / Instrumento | `CUENTAS CAJA` / `CAJA CLP` o `CAJA USD` (como BICE) |
| nombreTipoMovimiento | Concepto descriptivo (1.ª columna) en mayúsculas. Algunos calzan literalmente con BICE (`DIVIDENDO EN PESOS`, `FACTURA COMPRA RV`); los demás necesitan una tabla de equivalencias |
| Moneda | Columna Moneda |
| abono / cargo | Columnas Abono / Cargo (sin `$`; `$0` → 0) |
| TipoAPV / Descripcion... | Del Régimen de la fila |

### 5.5 MOVIMIENTOS_FFMM (grupo FM) y MOVIMIENTOS_BOLSA (grupos FI/Acciones)

| Columna | Fuente |
|---|---|
| Instrumento / Nemotecnico / Emisor | Igual que en saldos (nemo y emisor sin fuente directa) |
| MonedaInstrumento | `Moneda de Origen` |
| NumeroRerferencia (solo FFMM) | **Sin fuente** |
| NombreTipoMovimiento | Concepto. Para BOLSA, `Compra RV` → `COMPRA RV` (literal BICE); `Rescate Custodia` → a definir. Para FFMM, Aportes/Compras → `INVERSION FM` y Rescates/Ventas → `RESCATE FM` (`Venta por Acciones` → RESCATE FM, a confirmar) |
| Moneda | `CLP` (el monto viene en CLP) |
| Cantidad | `Cantidad / N° de Cuotas` |
| PrecioTIR | `Precio / Valor Cuota` |
| MontoNeto | `Monto en CLP` (= cantidad × precio [× TC]; en BICE MontoNeto también es igual a cantidad × precio). La comisión aparece solo en la caja: `Factura Compra RV` = Monto × (1 + 0,5 % × 1,19) en el único caso observado |
| TC operación | Está en el PDF (`Tipo Cambio Operación`), pero no hay columna destino |

### 5.6 MOVIMIENTOS_PERSHING

No sale de la cartola Sura; ver el estado `Sura pershing-...` en `pershing.md`. La única conexión es `CuentaPershing` = `TD9-<CUENTA>` de ese estado.

---

## 6. Cuadraturas (probadas en los 7 archivos con un parser de prueba por coordenadas)

| # | Regla | Casos | Resultado |
|---|---|---|---|
| 1 | Por fila de Detalle: Cantidad × Precio (× TC si USD) = Saldo en CLP | 44 de 45 filas | Cuadra con dif. máx. 0,48 CLP (redondeo al peso). 1 fila sin precio ni saldo (FI recién comprado, S1) |
| 2 | Σ filas del grupo = `SUBTOTAL <grupo>` | 19 | Exacto |
| 3 | Σ SUBTOTAL = `TOTAL INVERSIONES ...` (CLP y USD) | 12 | Exacto |
| 4 | SUBTOTAL del Detalle = fila del Resumen de Saldos en la columna "del 31/08" del segmento (Previsional o Financiero) | 19 | Exacto (sirve además para comprobar que las columnas 31/07 y 31/08 quedaron bien asignadas) |
| 5 | Resumen de Saldos: Previsionales + Financieras = Total; Σ filas = Total | 54 + 60 | Exacto |
| 6 | Resumen de Movimientos: SI + Abonos − Cargos + Utilidad = SF (por columna) | 21 | Cuadra; dif. máx. 1 CLP (S1) |
| 7 | Resumen de Movimientos SI / SF = `Total` del Resumen de Saldos 31/07 / 31/08 | 21 | Exacto |
| 8 | Caja: Saldo Inicial + Σ Abono − Σ Cargo = Saldo Final (CLP y USD, por segmento) | 28 bloques | Cuadra; dif. máx. 4 CLP (S4, caja previsional con 3 regímenes); USD exacto |
| 9 | Saldo Final de caja = `SUBTOTAL Cuenta de Inversiones` del Detalle; SI y SF = fila "Cuenta de inversiones" del Resumen 31/07 y 31/08 | 28 | Exacto |
| 10 | Σ Monto en CLP = `TOTAL APORTES/COMPRAS` / `TOTAL RESCATES/VENTAS` | 28 | Exacto (el monto vacío cuenta como 0) |
| 11 | Por movimiento: Cantidad × Precio (× TC Operación) = Monto | 10 | Dif. máx. 3 CLP (fila con TC de operación); el resto ≤ 0,5 |
| 12 | Saldo corrido de caja: saldo_i − saldo_{i−1} = abono_i − cargo_i (dentro del mismo régimen) | S1, S4, S5 | Cuadra; el saldo de partida no es el Saldo Inicial impreso |

Tolerancias sugeridas: ±1 CLP por fila y en las identidades del resumen; ±5 CLP en la caja; ±0,01 USD; en filas con TC, ±5 CLP o un error relativo de 1e-5.

---

## 7. Riesgos y particularidades

1. **Sin RUT ni cuenta**: todo depende de una tabla maestra por nombre. El nombre puede venir en varios spans o fuentes, con la letra achicada (7,6 pt) o como razón social. En un archivo el nombre del cliente se parece al del asesor, así que no hay que usar el campo Asesor para identificar.
2. **El orden de texto no es el orden visual**: las fechas del Resumen se invierten, en filas CLP del Detalle el `-` del TC sale después del saldo y el texto anonimizado va al final. No usar regex sobre `get_text()` plano.
3. **Encabezados desalineados** en Cuentas de Inversiones (Operación/Concepto): hay que asignar por la posición de los datos, no por el texto del encabezado.
4. **Nombres y conceptos en 2 líneas** con la línea de datos desplazada (+2 pt en Detalle; −3,5 / +4,6 pt en Movimientos). La regla que funcionó: cada línea de nombre se asigna al último ancla (línea con datos) cuya y ≤ y_línea + 4,5.
5. **La serie del FI va dentro del nombre** (texto libre: "Serie A", "FOGAPE", "Fully Fund A", "Priv Eq B", "I"); en FM va en su columna.
6. **Valores ausentes**: `-` frente a vacío. Hay un saldo sin valor (FI recién comprado) y un monto vacío en una reinversión mínima.
7. Precios con `$` aunque la moneda sea USD; negativos `$-1.234`; caja USD con 2 decimales y el resto con 4.
8. **Variantes de etiquetas**: `Fondo de Inversiones` / `Fondos de Inversión`; `Cuenta de inversiones` / `Cuenta de Inversiones`; `Cuentas Inversiones USD` / `Cuentas de Inversión USD`; `PERÍODO` / `PERIODO`; dos subtítulos de plantilla. Hay que comparar normalizando.
9. **El orden de los grupos difiere** entre el Resumen (FM, FI, Caja, Acciones) y el Detalle (Acciones, FI, FM, Caja). Hay que emparejar por nombre.
10. **Códigos de régimen**: tenencias financieras en `18Q`, movimientos en `R.GRAL`; `18T` sin definición. El mapeo a TipoAPV y a la "Descripción" de BICE es una propuesta a validar.
11. **Saldo corrido por régimen**: puede partir de 0 o quedar negativo. No usarlo como saldo.
12. **Abonos y Cargos del Resumen de Movimientos** no tienen una regla reproducible (S1 frente a S5); solo valen para la identidad SI → SF.
13. Un FM aparece dentro del grupo FI (S5). Clasificar por grupo y marcarlo para revisión.
14. **Tipo de cambio**: solo aparece si hay un instrumento USD en CLP. La caja USD nunca trae TC. EUR nunca aparece.
15. **Sin fecha de emisión**: solo está el período. Las fechas de movimiento son fechas de valor cuota.
16. La fila `TOTAL RESCATES/VENTAS` trae un `$` suelto; tomar siempre el último token numérico de la línea.
17. **Pershing** está aparte: la cartola Sura no lo incluye. Hay que asegurarse de procesar ambos y de no inventar una cuenta TD9 para los clientes que no la tienen.
18. Desborde de página: no se observó, pero el parser debe arrastrar sección y grupo a la página siguiente si una página empieza sin título.

---

## 8. Enfoque recomendado de extracción

**pymupdf `page.get_text("words")` con coordenadas**, en una máquina de estados por página:

1. Período: regex `PER[IÍ]ODO (\d\d/\d\d/\d{4}) - (\d\d/\d\d/\d{4})` sobre la línea en y≈60.
2. Cliente: las palabras con y centro en 100–115 y x en 66–310 de la pág. 1, ordenadas por x. Ese nombre se busca en la tabla maestra para obtener RUT, cuenta y portafolio.
3. Agrupar palabras en líneas por y centro (tolerancia ~1,2 pt, porque nombre y datos están separados por 2–3,5 pt y hay que mantenerlos en líneas distintas). Detectar títulos de sección (`Resumen de Saldos...`, `Detalle de Inversiones (Previsionales|Financieras)( USD)?`, `Movimientos Inversiones ...`, `Aportes/Compras`, `Rescates/Ventas`, `Cuentas de Inversiones( USD)?`, `Glosario:`). Detectar grupos (x0≈25 sin datos), filas `SUBTOTAL`/`TOTAL`, y saltar los encabezados de tabla (líneas que contienen `Régimen`, `Tributario`, `Instrumento`, `Operación`).
4. Anclas de fila: en Detalle, una línea con palabras en x>200; en Movimientos, una línea que contiene una fecha `dd/mm/aaaa`. Asignar columnas por rango de x: el x0 para el texto y el borde derecho x1 para los números, que van alineados a la derecha. Las líneas sin datos se pegan al ancla con la regla del punto 4 de §7.
5. Resumen de Saldos: 6 valores por fila ordenados por x → (prev 31/07, prev 31/08, fin 31/07, fin 31/08, total 31/07, total 31/08). Resumen de Movimientos: 3 valores por fila.
6. Números: quitar `US$`/`$`, quitar `.` de miles, `,` → `.`, respetar el `-` después del símbolo; `-` solo = vacío.
7. Validar con las cuadraturas de §6 antes de escribir los CSV. Si algo falla, marcar el archivo para revisión en vez de exportar.

**Por qué**: el PDF tiene texto nativo con posiciones estables entre las dos variantes, mientras que el orden de texto no es fiable (puntos 2 y 3 de §7). pdfplumber `find_tables()` no sirve: los únicos rectángulos son los fondos de los encabezados, así que devuelve celdas de encabezado fusionadas y una sola columna de datos. La estrategia "text" de pdfplumber tampoco separa bien las filas de 2 líneas. Un prototipo de este enfoque (unas 150 líneas) extrajo todas las filas de los 7 archivos y pasó las 12 cuadraturas dentro de las tolerancias indicadas.

---

## 9. Extractor (`skill/cartolas/extractores/sura.py`)

**Reconocimiento.** Todas las páginas, si la primera trae `Cartola Mensual`, `sura.cl` y `PERÍODO`/`PERIODO` y no es la plantilla Pershing. El estado `Sura pershing-...` lo lee el extractor Pershing.

**Columnas.** Por coordenadas, con bordes fijos entre los datos (no entre los encabezados): así se evitan las fechas invertidas del Resumen (§3.2) y los encabezados corridos de Cuentas de Inversiones (§3.7). Los nombres en dos líneas se pegan a la línea de datos más cercana hacia arriba con 4,5 pt de margen (§7.4).

**Decisiones por defecto** (tablas al comienzo del módulo, fáciles de cambiar):

- RUT vacío, como decidió Felipe; él lo llena después. Portafolio vacío.
- Cuentas (`CUENTA_FINANCIERA`, `REGIMENES_APV`): Inversiones Financieras van todas a la cuenta `0` (CUENTA INVERSION), sea cual sea su régimen (18Q, 18T, R.GRAL). Inversiones Previsionales van a una cuenta por régimen, con el código del régimen como número y producto base APV PRIME: `CVN_A` → CV / APORTE, `CVN_B` y `CVA_B` → CV / BONIFICACIÓN, `DCA`/`DCN`/`DCR` → DC / BONIFICACIÓN, `BON_F` → DAPVC / APORTE (como las cuentas "BF" de BICE).
- Posiciones: fondos mutuos a SALDOS_FFMM con producto `FONDOS MUTUOS`; fondos de inversión a CUSTODIA_ACCIONES como `CFI`, incluido el fondo mutuo LarrainVial Enfoque que Sura lista entre los FI (BICE también lo exporta como CFI); acciones a CUSTODIA_ACCIONES con el nombre como nemotécnico. Sura no informa costo, así que `PrecioPromedioCompra` queda vacío. El FI recién comprado sin precio ni saldo sale con patrimonio vacío y un aviso.
- Movimientos de caja (`TIPOS_CAJA`): `Dividendo en Pesos` → DIVIDENDO EN PESOS, `Factura Compra RV` → FACTURA COMPRA RV, `Abono a Cuenta de Inversiones` → ABONO CUENTA INVERSION $, `Abono a Cta Inv SURA x Rescate` → ABONO ORIGINADO POR PAGO RESCATES $ OWP. `Retiro desde Cta Inversión` y `Abono USDs desde Cuenta` quedan en mayúsculas porque su equivalente no es inequívoco.
- Movimientos de títulos: fondos mutuos como INVERSION FM (Aportes/Compras) o RESCATE FM (Rescates/Ventas, incluida `Venta por Acciones`); FI y acciones como COMPRA RV o el concepto en mayúsculas (`RESCATE CUSTODIA`, con aviso). En CLP el monto es el `Monto en CLP`; en USD, cantidad × precio en dólares, con el monto en pesos y el tipo de cambio de operación en un aviso. Sin `Monto en CLP` (Aporte por Reparto), cantidad × precio.
- Tipo de cambio: el `Tipo Cambio Observado` de una fila USD; las cartolas sin filas USD toman el de otra cartola con el mismo cierre.

**Tabla maestra.** Cinco FI de Sura se agregaron a `datos/alias.csv` porque calzan en fondo, serie y moneda y su valor cuota al 31-08 está a menos de 1 % del precio de referencia del export (Ameris Alternativos II A, Singular Leaseback II A, Singular Residential MBS I, Toesca Deuda Privada A y F). No se agregaron los que no cumplen: FYNSA Galgo II y III, Security Pantheon Fully Fund A, Ameris DP con Garantía FOGAPE y LarrainVial Enfoque (sin serie en el nombre), y Ameris Alternativos I y NM Guardian III (moneda distinta). Los fondos mutuos SURA no están en el export de ejemplo y salen sin nemotécnico ni emisor.

**Resultado en las 7 cartolas:** 126 cuadraturas (las 12 de §6 más TOTAL INVERSIONES contra el Resumen y la operación Abono/Cargo contra la columna del monto), todas cierran. Se leen 35 posiciones (17 fondos mutuos, 16 CFI, 2 acciones), 10 saldos de caja, 15 movimientos de caja y 10 de títulos. 7 posiciones están en la tabla maestra (2 acciones por nemotécnico y 5 FI por alias).
