# Herramientas

## anonimizar_cartolas.py

Hace copias de las cartolas con los datos de los clientes (nombre, RUT, dirección, comuna, email, teléfono y número de cuenta) cambiados por datos falsos, para poder trabajar con ellas sin exponer datos reales. Los originales no se modifican.

### Cómo usarlo (Windows)

1. Copia `anonimizar_cartolas.py` a la carpeta que contiene `Training Data` y `Example` (también sirve `Example Export`).
2. Abre una terminal en esa carpeta e instala las librerías una vez:

   ```
   py -m pip install pymupdf openpyxl
   ```

3. Corre el script:

   ```
   py anonimizar_cartolas.py
   ```

   La primera vez busca todos los RUT y crea `clientes.csv` con el nombre que aparece junto a cada uno. Ábrelo en Excel y revísalo: corrige los nombres, deja `si` en la columna `anonimizar` para los clientes y `no` para bancos, corredoras y emisores (el script ya propone `no` para los que parecen instituciones). Puedes agregar clientes que aparecen solo por nombre.

4. Corre el mismo comando otra vez. Ahora busca la dirección, comuna, email, teléfono y número de cuenta de cada cliente y crea `otros_datos.csv`. Revísalo: pon `no` en lo que no sea del cliente y agrega lo que falte. Si un nombre de archivo trae una abreviatura del cliente (iniciales, un nombre mal escrito), agrégala con tipo `alias`. La columna `falso` se llena sola.

5. Corre el mismo comando una tercera vez. Las copias quedan en `anonimizado`, con la misma estructura de carpetas.

Si después aparecen RUT nuevos (otra cartola), el script los agrega al final de `clientes.csv` y se detiene para que los revises.

Si algunos clientes tienen correo con el dominio de la asesora, agrega `--dominio-asesora <dominio>` (se puede repetir) en las tres corridas: en esos correos se cambia solo la parte antes de la @. Sin la opción también se cambia el dominio.

### Qué hace

- Reemplaza cada nombre, RUT y dato de `otros_datos.csv` por uno falso, siempre el mismo para el mismo cliente, en el texto de los PDF, en los Excel (`.xlsx`, `.xlsm`), en los `.csv`/`.txt` y en los nombres de archivo. Los RUT falsos tienen dígito verificador válido.
- Reconoce el nombre en distintos órdenes ("JUAN PEREZ GONZALEZ", "PEREZ GONZALEZ, JUAN", "Sr. Pérez"), con o sin tildes, y el RUT con o sin puntos.
- Los datos falsos mantienen el formato: una dirección falsa con número, un email armado con el nombre falso (el dominio público como gmail.com se mantiene), el mismo código de país y área en el teléfono, y una cuenta con los mismos separadores. Los correos, teléfonos y direcciones de las instituciones no se tocan.
- Abre los PDF protegidos con clave probando el RUT de los clientes (y las claves de `claves.txt`, una por línea, si existe). Las copias quedan sin clave.
- Borra los metadatos del PDF (autor, título) y del Excel.
- Verifica cada copia: si queda algún dato real (también dentro del archivo, fuera del texto visible, y en el nombre del archivo), si el PDF es escaneado, si se perdió texto o si la redacción borró palabras que no eran del cliente, ese archivo no se copia y queda anotado en el reporte. Por eso la carpeta `anonimizado` se puede compartir completa.

### Archivos con datos reales

`clientes.csv`, `otros_datos.csv`, `mapeo_anonimizacion.csv` (real → falso), `reporte_anonimizacion.txt` y `claves.txt` quedan junto a las carpetas originales y no deben compartirse ni subirse al repositorio. `anonimizado/RESUMEN.txt` no tiene datos reales.

### Pruebas

```
py -m pip install pytest
py -m pytest herramientas/tests
```

Las pruebas generan cartolas sintéticas; no usan datos reales.
