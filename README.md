# Intérprete de Cartolas

Skill que lee cartolas (estados de cuenta en PDF) de distintas instituciones y exporta archivos de **saldos** y **movimientos** con el mismo formato que los ejemplos de la carpeta `Example`.

## Objetivo

- Extraer la mayor cantidad de información de cada cartola con la menor cantidad de errores.
- Desarrollar la skill con las cartolas de `Training Data`, separadas por institución.
- Verificar que los datos extraídos coinciden con los PDF.

## Datos y privacidad

Las cartolas contienen datos reales de clientes, así que:

- Los PDF de `Training Data`, los archivos de `Example` y sus copias anonimizadas no se suben a este repositorio.
- Antes de trabajar con ellas se reemplazan los nombres y RUT de los clientes en copias anonimizadas. El mapeo entre datos reales y ficticios queda solo en el computador local.

## Estructura

- `skill/`: la skill (`SKILL.md`) y el paquete Python `cartolas` que lee las cartolas y escribe los archivos de salida.
- `docs/formato-salida.md`: formato de los archivos de saldos y movimientos, tomado del export de ejemplo.
- `docs/inventario.md`: formatos de cartola encontrados, cómo extraerlos y validarlos, y preguntas abiertas. El detalle por institución está en `docs/instituciones/`.
- `tests/`: pruebas (`python3 -m pytest tests`). Las que usan cartolas reales corren solo donde existen sus copias anonimizadas.

## Uso

Lee los 6 formatos de `Training Data`: las cartolas BICE nuevas (septiembre de 2026 en adelante), las BICE antiguas, la cartola Valores Security que viene pegada a ellas, los informes Larrainvial, las cartolas mensuales Sura y los estados Pershing (de BICE y de Sura).

```
pip install -r requirements.txt
cd skill
python -m cartolas "<carpeta con las cartolas>" --salida "<carpeta de salida>"
```

Deja en la carpeta de salida un juego de 7 CSV por institución y un reporte con las cuadraturas que no cierran y lo que no se pudo exportar. La salida tiene datos de clientes: no va al repositorio.

Para comparar la salida con un export de BICE del mismo día, fila por fila:

```
python -m cartolas.comparar "<carpeta del export>" "<carpeta de salida>"
```

Compara solo los clientes que están en la salida y, en los movimientos, solo las fechas del export. La carpeta del export puede traer los archivos de varios días: se juntan, y de los movimientos se comparan los días dentro del período de las cartolas. Si el export no es del día de cierre de las cartolas, `--fecha-saldos AAAA-MM-DD` indica qué saldos de la salida comparar. Deja `COMPARACION_<código>.md` en la carpeta de salida.

## Instalar la skill en Claude Code

Conviene instalarla en el computador donde están las cartolas: Claude Code la corre ahí y los datos no salen de ese equipo. Necesita Python 3.10 o superior.

1. Bajar el repositorio: `git clone https://github.com/felipedm777/Interprete-cartolas.git`, o el ZIP desde GitHub (botón *Code* → *Download ZIP*).
2. Instalar la librería de PDF: `pip install pymupdf`.
3. Copiar la carpeta `skill` con el nombre `interprete-cartolas` a una de estas carpetas:
   - `.claude/skills/` dentro de la carpeta donde se trabaja con las cartolas, para usarla solo ahí.
   - `~/.claude/skills/` (en Windows, `C:\Users\<usuario>\.claude\skills\`), para usarla en cualquier carpeta.

   Tiene que quedar `.../skills/interprete-cartolas/SKILL.md` junto a `.../skills/interprete-cartolas/cartolas/`.
4. Abrir Claude Code en la carpeta de las cartolas y pedirle, por ejemplo, "exporta las cartolas de esta carpeta al formato del SFTP". Claude encuentra la skill por la descripción de su `SKILL.md`.

Para actualizarla, bajar de nuevo el repositorio (`git pull`) y volver a copiar la carpeta `skill`. La tabla maestra de instrumentos (`cartolas/datos/instrumentos.csv`) viene incluida; para agregarle instrumentos nuevos, ver "Mantener la tabla maestra" en `skill/SKILL.md`.
