# Inventario de cartolas

Resumen del estudio de las 59 cartolas anonimizadas de `Training Data` y de los 7 CSV de `Example Export` (octubre de 2026). El formato de salida está en [formato-salida.md](formato-salida.md) y el detalle de cada formato de cartola, en [instituciones/](instituciones/).

Ningún documento de esta carpeta contiene datos de clientes: los nombres, RUT, cuentas y montos de ejemplo son marcadores o números inventados.

## Formatos encontrados

Las 4 carpetas contienen 6 formatos distintos, porque las cartolas BICE antiguas traen pegada una cartola de Valores Security y hay estados Pershing tanto en BICE como en Sura.

| Formato | Dónde está | Archivos | Páginas | Período | Página | Detalle |
|---|---|---:|---|---|---|---|
| BICE nueva | `BICE nuevas/` | 20 (20 clientes) | 6–15 | sep-2026 | A4 apaisada | [bice-nueva.md](instituciones/bice-nueva.md) |
| BICE antigua | `BICE viejas/` | 12 (11 distintos: hay un duplicado exacto) | 4–7 | abr-2026 | A4 vertical | [bice-antigua-y-security.md](instituciones/bice-antigua-y-security.md) |
| Valores Security / AGF Security | Pegada después de la BICE antigua en 10 de esos 12 PDF | 10 | 4–14 | abr-2026 | Carta apaisada | [bice-antigua-y-security.md](instituciones/bice-antigua-y-security.md) |
| Larrainvial | `Larrainvial/` | 14 (2 clientes) | 5–11 | sep-2025 a ago-2026 | Carta, girada 90° | [larrainvial.md](instituciones/larrainvial.md) |
| Sura | `Sura/` | 7 | 5–6 | ago-2026 | Carta vertical | [sura.md](instituciones/sura.md) |
| Pershing | `BICE viejas/Corredora de bolsa/` (5) y `Sura/` (1) | 6 (2 cuentas) | 8–13 | ene–may 2026 y ago-2026 | Carta apaisada | [pershing.md](instituciones/pershing.md) |

Todas las páginas tienen texto extraíble, así que no hace falta OCR.

## Cómo extraer

El mismo enfoque sirve para los 6 formatos: leer palabras o spans con coordenadas con PyMuPDF, ubicar cada sección por su título, armar las columnas a partir de los encabezados de cada tabla y asignar cada valor a la fila cuya celda ancla (cuenta o fecha) esté más cerca en vertical. Las tablas automáticas de pdfplumber no sirven en ninguno: las tablas no tienen líneas o salen como una sola celda. `pdftotext -layout` colapsa los espacios dobles que forman parte de los nombres de instrumento.

Particularidades que el extractor tiene que manejar en más de un formato:

- **Texto anonimizado al final.** Nombre, RUT, dirección y cuenta quedaron en Helvetica y aparecen al final del orden de lectura de la página, así que solo se pueden leer por posición.
- **Celdas de 2 líneas.** Hay montos en `$` con su equivalente `US$` debajo y nombres de instrumento que ocupan 2 líneas por encima y por debajo de la fila de números.
- **Monedas mal rotuladas.** En BICE nueva, `CARGO EN DOLARES` dice CLP pero el monto es USD. En Larrainvial, las columnas `($)` de las secciones en dólares están en USD. En Security, los dividendos de fondos en USD traen el precio en USD y el monto en CLP.
- **Precisión.** BICE nueva redondea los USD a entero en caja, movimientos y valor de mercado; los centavos se recuperan dividiendo el equivalente en CLP por el tipo de cambio.
- **Formatos numéricos mezclados.** Chileno (`1.234,56`) en casi todo; inglés (`1,234.56`) en Pershing y en los nominales de bonos de BICE nueva; un `100.00` aislado en Larrainvial.
- **Larrainvial.** Las páginas vienen giradas 90° (hay que aplicar `page.rotation_matrix`) y tienen texto blanco invisible que hay que filtrar.
- **Nombres de archivo engañosos.** En Larrainvial, "…Septiembre" es de 2025 y "Prov" en el nombre no indica si la cartola es provisoria. En Pershing, el índice `MSTAT_<n>` no sigue el orden de los meses. El período siempre se lee del contenido.

## Cómo se puede verificar lo extraído

| Formato | Cuadraturas internas | Continuidad entre meses | Contra el export de ejemplo |
|---|---|---|---|
| BICE nueva | Cuadran en los 20 archivos: sumas contra totales, cuotas × valor cuota = valor de mercado (±0,5 CLP), % de activo, cantidad × precio = monto | No aplica (un solo mes) | Sí, parcial: de 185 posiciones, 170 están en el export, con la misma cantidad en 168 y el mismo precio promedio en 163. Precio y valor difieren porque el export es del 22-09 y la cartola del 30-09 |
| BICE antigua | Cuadran con ±1 $ (±0,01 US$). La Ganancia/Pérdida excluye los depósitos a plazo | No aplica | Solo como catálogo: el export es cinco meses posterior |
| Security | Cuadran con ±1 $ | No aplica | 123 de 180 posiciones tienen el mismo nemotécnico y cantidad en el export |
| Larrainvial | Cuadran en los 14 archivos. Única excepción: la factura de compra es 1,2–1,3 % mayor que precio × cantidad por los costos | Patrimonio final = inicial del mes siguiente en las 11 transiciones del cliente con 12 meses | No: los RUT están, pero con sus posiciones en BICE |
| Sura | 12 cuadraturas en los 7 archivos, con diferencias de redondeo de hasta 4 CLP | No aplica (un solo mes) | No: la cartola no trae RUT |
| Pershing | 15 cuadraturas en los 6 archivos, al centavo. Cantidad × costo unitario se desvía hasta ±0,10 | Valor final = inicial del mes siguiente en los 4 empalmes | No: el ejemplo no tiene filas Pershing |

El validador de la skill puede aplicar estas reglas a cada archivo y marcar los que no cuadren dentro de la tolerancia indicada en cada documento.

## Lo que las cartolas no traen

Estas columnas del formato de salida no salen de ningún PDF, o solo de algunos:

| Dato | Situación | Propuesta |
|---|---|---|
| `NemotecnicoInstrumento`, `Emisor` | Solo vienen cuando el nombre ya es el nemotécnico (`CFI-…`, acciones) y aun así hay excepciones (`NUEVAPOLAR` → `ABC`) | Tabla maestra de instrumentos, partiendo de los 240 nemotécnicos distintos del export de ejemplo |
| `RutCliente` | Sura y Pershing no lo traen | Tabla de clientes que mantenga Felipe: nombre o cuenta Pershing → RUT |
| `Cuenta`, `Portafolio`, `ProductoBase` | Son conceptos de BICE. Larrainvial siempre dice "Cuenta: 0"; Security, Sura y Pershing usan sus propios códigos | Misma tabla de clientes, más una regla por institución |
| `TipoAPV`, régimen | BICE nueva los codifica en el sufijo del portafolio; BICE antigua, en la columna de cuenta; Sura usa sus propios códigos (`CVN_A`, `BON_F`, `18Q`, `18T`…); Security no los trae | Regla por institución, a confirmar |
| `TipoCambioUSD` | No viene en BICE antigua; en Sura solo si hay instrumentos en USD | Usar el dólar observado del cierre o el de la cartola Security del mismo mes |
| `TipoCambioEUR`, `EnTransito` | No vienen en ningún formato | `EnTransito = NO` y `TipoCambioEUR` vacío, salvo que Felipe prefiera otra cosa |
| Instrumento de los dividendos y repartos | BICE nueva y Sura abonan el dividendo o el reparto en la caja sin decir de qué fondo viene; el export sí lo trae | Comparar el monto por cuota entre clientes del mismo día y contra los repartos que publican la Bolsa de Santiago y DataFondos: [eventos-capital.md](eventos-capital.md) |

## Preguntas para Felipe

Ordenadas por cuánto afectan al diseño de la skill:

1. **Alcance.** ¿Se exportan los portafolios que no son de la asesora, la parte Security de las cartolas BICE antiguas y los estados Pershing? Los depósitos a plazo, la intermediación financiera y los bonos no tienen archivo de destino en el ejemplo: ¿dónde van?
2. **Clientes y cuentas.** Para Sura, Pershing, Larrainvial y Security hace falta una tabla que diga, por cliente, su RUT, cuenta y portafolio. ¿Existe ya en algún sistema?
3. **Institución.** Un mismo RUT tendrá filas de BICE y de Larrainvial, a veces con el mismo instrumento. ¿Cómo se distingue la institución en la salida: por nombre de archivo, por `Portafolio` o con otra columna?
4. **Fechas.** ¿`FechaProceso` es el cierre de la cartola en los saldos? ¿Y en los movimientos, la fecha del movimiento o la del cierre?
5. **Convenciones.** ¿Se confirma régimen A = `APORTE` y régimen B = `BONIFICACIÓN`, como en el export? ¿El money market de Pershing es caja o fondo? ¿`MontoNeto` se toma de la factura (con costos) o es precio × cantidad?
6. **Más muestras.** Para validar montos al peso serviría un export de BICE al 30-09-2026, la misma fecha de las cartolas nuevas. También faltan estados Pershing con compras, ventas y dividendos de acciones, y la cartola Larrainvial de julio de 2026 del segundo cliente.

Cada documento de [instituciones/](instituciones/) termina con sus propias preguntas de detalle.

## Siguiente paso propuesto

Empezar por BICE nueva: es el formato con más archivos, el más regular y el único que se puede contrastar contra el export de ejemplo. Con ese extractor se arman también la tabla maestra de instrumentos y el validador de cuadraturas, que después sirven para los otros formatos.
