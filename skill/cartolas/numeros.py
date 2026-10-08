"""Lectura de montos impresos en las cartolas y escritura en el formato de salida."""

import re
from decimal import ROUND_HALF_UP, Decimal

_LIMPIAR = re.compile(r"US\$|USD|CLP|UF|\$|%|\s")


def leer_monto(texto: str, decimal: str = ",") -> Decimal:
    """Convierte un monto impreso a Decimal.

    ``decimal`` es el separador decimal de la cartola: "," en las chilenas
    (1.234.567,89) y "." en las que vienen en formato inglés (1,234,567.89).
    Acepta signo de moneda, porcentaje, signo menos al inicio o al final y
    negativos entre paréntesis.
    """
    t = _LIMPIAR.sub("", texto)
    negativo = False
    if t.startswith("(") and t.endswith(")"):
        negativo, t = True, t[1:-1]
    if t.startswith("-"):
        negativo, t = True, t[1:]
    elif t.endswith("-"):
        negativo, t = True, t[:-1]
    miles = "." if decimal == "," else ","
    t = t.replace(miles, "").replace(decimal, ".")
    if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", t):
        raise ValueError(f"monto no reconocido: {texto!r}")
    valor = Decimal(t)
    return -valor if negativo else valor


def escribir_numero(valor: Decimal | int | float | str | None, decimales: int) -> str:
    """Escribe un número como el export de ejemplo: 1234,500000 o ,012345.

    Coma decimal, sin separador de miles, decimales fijos y sin el cero antes
    de la coma cuando el valor absoluto es menor que 1. Vacío si no hay valor.
    """
    if valor is None or valor == "":
        return ""
    d = Decimal(str(valor)).quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)
    signo = "-" if d < 0 else ""
    entero, _, fraccion = f"{abs(d):f}".partition(".")
    if entero == "0" and decimales:
        entero = ""
    return f"{signo}{entero},{fraccion}" if decimales else f"{signo}{entero}"
