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
