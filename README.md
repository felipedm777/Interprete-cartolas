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
