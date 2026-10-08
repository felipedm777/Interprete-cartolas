# Herramientas

## anonimizar_cartolas.py

Hace copias de las cartolas con los nombres y RUT de los clientes cambiados por datos falsos, para poder trabajar con ellas sin exponer datos reales. Los originales no se modifican.

### Cómo usarlo (Windows)

1. Copia `anonimizar_cartolas.py` a la carpeta que contiene `Training Data` y `Example`.
2. Abre una terminal en esa carpeta e instala las librerías una vez:

   ```
   py -m pip install pymupdf openpyxl
   ```

3. Corre el script:

   ```
   py anonimizar_cartolas.py
   ```

   La primera vez busca todos los RUT y crea `clientes.csv` con el nombre que aparece junto a cada uno. Ábrelo en Excel y revísalo: corrige los nombres, deja `si` en la columna `anonimizar` para los clientes y `no` para bancos, corredoras y emisores (el script ya propone `no` para los que parecen instituciones). Puedes agregar clientes que aparecen solo por nombre.

4. Corre el mismo comando otra vez. Las copias quedan en `anonimizado`, con la misma estructura de carpetas.

### Qué hace

- Reemplaza cada nombre y RUT de cliente por uno falso, siempre el mismo para el mismo cliente, en el texto de los PDF, en los Excel (`.xlsx`, `.xlsm`), en los `.csv`/`.txt` y en los nombres de archivo. Los RUT falsos tienen dígito verificador válido.
- Reconoce el nombre en distintos órdenes ("JUAN PEREZ GONZALEZ", "PEREZ GONZALEZ, JUAN", "Sr. Pérez"), con o sin tildes, y el RUT con o sin puntos.
- Abre los PDF protegidos con clave probando el RUT de los clientes (y las claves de `claves.txt`, una por línea, si existe). Las copias quedan sin clave.
- Borra los metadatos del PDF (autor, título) y del Excel.
- Verifica cada copia: si queda algún nombre o RUT real, si el PDF es escaneado o si se perdió texto, ese archivo no se copia y queda anotado en el reporte. Por eso la carpeta `anonimizado` se puede compartir completa.

### Archivos con datos reales

`clientes.csv`, `mapeo_anonimizacion.csv` (real → falso), `reporte_anonimizacion.txt` y `claves.txt` quedan junto a las carpetas originales y no deben compartirse ni subirse al repositorio. `anonimizado/RESUMEN.txt` no tiene datos reales.

### Pruebas

```
py -m pip install pytest
py -m pytest herramientas/tests
```

Las pruebas generan cartolas sintéticas; no usan datos reales.
