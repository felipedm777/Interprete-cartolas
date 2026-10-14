# Formato de salida: saldos y movimientos

La skill debe producir los mismos archivos que el export de BICE que está en `Example Export` (portafolio <código>, fecha de proceso 2026-09-22). Este documento describe ese formato tal como viene en el ejemplo. La especificación en código está en `skill/cartolas/formato.py` y la prueba `tests/test_exportar.py` verifica que el exportador reproduce los 7 archivos del ejemplo byte a byte.

## Archivos

| Archivo | Filas en el ejemplo | Columnas | Contenido |
|---|---:|---:|---|
| `SALDOS_CAJA` | 555 | 15 | Saldo de caja por cuenta y moneda |
| `SALDOS_FFMM` | 706 | 22 | Posiciones en fondos mutuos y fondos de inversión administrados por BICE |
| `CUSTODIA_ACCIONES` | 4.055 | 22 | Posiciones en acciones, ETF y fondos de inversión (CFI) en custodia |
| `MOVIMIENTOS_DE_CAJA` | 75 | 13 | Cargos y abonos de caja |
| `MOVIMIENTOS_BOLSA` | 20 | 17 | Compras, ventas e ingresos de títulos de bolsa |
| `MOVIMIENTOS_FFMM` | 4 | 18 | Inversiones y rescates de fondos mutuos |
| `MOVIMIENTOS_PERSHING` | 0 | 17 | Movimientos en la custodia internacional Pershing (el ejemplo solo trae el encabezado) |

Nombre de archivo: `<ARCHIVO>_<portafolio>_<AAAAMMDD>_V2.csv`, por ejemplo `SALDOS_CAJA_12345_20260922_V2.csv`.

## Convenciones comunes

- Separador `;`, sin comillas, primera línea con encabezados.
- Fin de línea CRLF, también después de la última fila.
- Codificación Windows-1252 (`cp1252`), salvo `MOVIMIENTOS_PERSHING`, que viene en UTF-8. Ninguno trae BOM.
- `FechaProceso` en formato `AAAA-MM-DD`; es la misma fecha en todas las filas.
- Números con coma decimal, sin separador de miles y con una cantidad fija de decimales por columna (tabla abajo). Cuando el valor absoluto es menor que 1 se omite el cero: `,012345`, `,00`. Negativos con `-` adelante: `-1234,500000`.
- `RutCliente` con guion y sin puntos: `12345678-9`, `1234567-K`.
- Las columnas de texto vacías quedan sin contenido (`;;`).

## Decimales por columna numérica

| Columna | Decimales | Archivos |
|---|---:|---|
| `Cantidad` | 6 | `SALDOS_FFMM`, `CUSTODIA_ACCIONES` |
| `Cantidad` | 4 | `MOVIMIENTOS_BOLSA`, `MOVIMIENTOS_FFMM`, `MOVIMIENTOS_PERSHING`* |
| `PrecioCierreEnMonedaValoracion` | 6 | `SALDOS_FFMM`, `CUSTODIA_ACCIONES` |
| `PrecioPromedioCompra` | 4 | `SALDOS_FFMM`, `CUSTODIA_ACCIONES` |
| `PatrimonioEnMonedaValoracion`, `patrimonioUSD`, `patrimonioCLP` | 6 | saldos y custodia |
| `TipoCambioUSD`, `TipoCambioEUR` | 14 | saldos y custodia |
| `abono`, `cargo` | 2 | `MOVIMIENTOS_DE_CAJA` |
| `PrecioTIR` | 4 | movimientos de títulos |
| `MontoNeto` | 2 | movimientos de títulos |

\* El ejemplo de Pershing no tiene filas; se asumen los mismos decimales que `MOVIMIENTOS_BOLSA`.

## Columnas

### Identificación (todas las salidas)

| Columna | Valores observados | Notas |
|---|---|---|
| `FechaProceso` | `2026-09-22` | Fecha de corte del export |
| `RutCliente` | RUT con guion | En las cartolas Sura no aparece el RUT (ver inventario) |
| `Cuenta` | `0`–`9`, `80`–`85`, `90`–`96` | Ver tabla de cuentas |
| `Portafolio` | `PORTAFOLIO N° <n> - <ASESORA> - <sufijo>` | También `PORTAFOLIO 57 BIS <n> - ...`. El sufijo indica el tipo de cuenta |
| `ProductoBase` | `CUENTA INVERSION`, `APV PRIME`, `APV FFMM` | |
| `Producto` | `CUENTAS CAJA`, `FONDOS MUTUOS BICE`, `FONDOS INVERSIÓN BICE`, `CFI`, `ACCIONES`, `ETF`, `FORWARDS DIVISA` | Depende del archivo |

### Cuenta, APV y régimen tributario

En el ejemplo, la cuenta determina el producto base, el tipo de APV, el régimen y el sufijo del portafolio:

| Cuenta | ProductoBase | TipoAPV | DescripcionTipoRegimenTributario | Sufijo del portafolio |
|---|---|---|---|---|
| `0`–`9` | `CUENTA INVERSION` | vacío | vacío | `S` |
| `80` | `APV FFMM` | `DAPV` | `BONIFICACIÓN` | `DAPV-B-S` |
| `81` | `APV FFMM` | `CV` | `BONIFICACIÓN` | `CV-B-S` |
| `82` | `APV FFMM` | `DC` | `BONIFICACIÓN` | `DC-S` |
| `83` | `APV FFMM` | `DAPV` | `APORTE` | `DAPV-A-S` |
| `84` | `APV FFMM` | `CV` | `APORTE` | `CV-A-S` |
| `85` | `APV FFMM` | `DAPV` | `APORTE` | `BF DAPV-A-S` |
| `90` | `APV PRIME` | `DAPV` | `BONIFICACIÓN` | `DAPV-B-S` |
| `91` | `APV PRIME` | `CV` | `BONIFICACIÓN` | `CV-B-S` |
| `92` | `APV PRIME` | `DC` | `BONIFICACIÓN` | `DC-S` |
| `93` | `APV PRIME` | `DAPV` | `APORTE` | `DAPV-A-S` |
| `94` | `APV PRIME` | `CV` | `APORTE` | `CV-A-S` (7 filas con `CV-A`) |
| `95` | `APV PRIME` | `DAPVC` | `APORTE` | `BF DAPV-A-S` |
| `96` | `APV PRIME` | `DAPVC` | `APORTE` | `BF CV-A` |

Régimen A = `APORTE`, régimen B = `BONIFICACIÓN` (así lo nombra el export). Hay 20 filas de las cuentas `90` y `92` con sufijo `S`, que no siguen la regla.

### Saldos y custodia

| Columna | Notas |
|---|---|
| `Instrumento` | Nombre largo, por ejemplo `FM SECURITY MID TERM SERIE A` |
| `NemotecnicoInstrumento` | Código corto, por ejemplo `FM-MID TERM-SERIE A`, `CFIASXIB-E` |
| `MonedaInstrumento` | `CLP` o `USD` |
| `Emisor` | Administradora o emisor; 15 filas vacías en `CUSTODIA_ACCIONES` |
| `MonedaValoracionPatrimonio` | `CLP` o `USD` |
| `EnTransito` | `NO`; en `SALDOS_CAJA` también `SI` (caja pendiente de liquidar) |
| `TipoCambioUSD`, `TipoCambioEUR` | Un único tipo de cambio para todo el archivo |

Relaciones que se cumplen en todas las filas del ejemplo (útiles para validar):

- Si la moneda de valoración es `CLP`: `PatrimonioEnMonedaValoracion = patrimonioCLP` y `patrimonioUSD = patrimonioCLP / TipoCambioUSD`.
- Si es `USD`: `PatrimonioEnMonedaValoracion = patrimonioUSD` y `patrimonioCLP = patrimonioUSD × TipoCambioUSD`.
- En `SALDOS_FFMM`: `Cantidad × PrecioCierreEnMonedaValoracion = PatrimonioEnMonedaValoracion` (diferencia máxima 0,0001).
- En `CUSTODIA_ACCIONES` el precio de cierre suele venir en la moneda del instrumento, no en la de valoración pese al nombre de la columna: en 777 de las 785 filas de instrumentos en USD valorizados en CLP, `Cantidad × Precio × TipoCambioUSD ≈ Patrimonio`; las otras 8 traen el precio ya en CLP. Con la fórmula que corresponda, el error es menor a 0,1 % en todas las filas salvo 3 (máximo 0,46 %), así que esta cuadratura necesita tolerancia.

### Movimientos

| Columna | Valores observados |
|---|---|
| `nombreTipoMovimiento` (caja) | `ABONO CUENTA INVERSION $`, `CARGO EN DOLARES`, `OPERACION DOLAR`, `FACTURA COMPRA RV`, `DIVIDENDO EN DOLARES`, `ABONO ORIGINADO POR PAGO RESCATES $ OWP`, `ABONO ORIGINADO POR PAGO RESCATE US$ OWP`, `CARGO POR PAGO DE RESCATES $ OWP`, entre 12 tipos |
| `Instrumento` (caja) | `CAJA CLP`, `CAJA USD`, `DOLAR`, o el nemotécnico del instrumento que generó el movimiento |
| `abono` / `cargo` | Una de las dos en cero (`,00`) |
| `NombreTipoMovimiento` (bolsa) | `COMPRA RV`, `INGRESO RV` |
| `NombreTipoMovimiento` (FFMM) | `INVERSION FM`, `RESCATE FM` |
| `NumeroRerferencia` | Número de operación (se escribe así, con la errata, en el export) |
| `PrecioTIR` | Precio unitario (o tasa, en renta fija) |
| `MontoNeto` | Monto de la operación, siempre positivo; el signo lo da el tipo de movimiento |

## Qué falta definir

- El ejemplo es de BICE. Para Larrainvial, Sura y Pershing hay que decidir cómo llenar las columnas propias de BICE (`Cuenta`, `Portafolio`, `ProductoBase`, `Producto`, `NemotecnicoInstrumento`). El inventario por institución propone un mapeo.
- Las cartolas son mensuales y el ejemplo es de un día (2026-09-22): `FechaProceso` debería ser la fecha de cierre de la cartola.
- `MOVIMIENTOS_PERSHING` no tiene filas de ejemplo, así que su formato numérico es una suposición.
