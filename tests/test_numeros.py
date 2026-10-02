from decimal import Decimal

import pytest

from cartolas.numeros import escribir_numero, leer_monto


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("$ 47.522.669", Decimal("47522669")),
        ("1.948,6070", Decimal("1948.6070")),
        ("23.944,1986", Decimal("23944.1986")),
        ("1,85%", Decimal("1.85")),
        ("-$ 1.234", Decimal("-1234")),
        ("(1.234,50)", Decimal("-1234.50")),
        ("1.234-", Decimal("-1234")),
        ("972,6", Decimal("972.6")),
        ("US$ 12,5", Decimal("12.5")),
        (",5", Decimal("0.5")),
    ],
)
def test_leer_monto_chileno(texto, esperado):
    assert leer_monto(texto) == esperado


def test_leer_monto_ingles():
    assert leer_monto("1,234,567.89", decimal=".") == Decimal("1234567.89")
    assert leer_monto("(12.50)", decimal=".") == Decimal("-12.50")


@pytest.mark.parametrize("texto", ["", "abc", "1.2.3,4,5", "$"])
def test_leer_monto_rechaza_basura(texto):
    with pytest.raises(ValueError):
        leer_monto(texto)


@pytest.mark.parametrize(
    "valor, decimales, esperado",
    [
        (Decimal("3056889"), 6, "3056889,000000"),
        (Decimal("0.042289"), 6, ",042289"),
        (Decimal("0"), 2, ",00"),
        (Decimal("-12345.6789"), 6, "-12345,678900"),
        (Decimal("-0.5"), 2, "-,50"),
        (Decimal("945.87"), 14, "945,87000000000000"),
        (Decimal("1.00005"), 4, "1,0001"),
        (Decimal("-0.0000001"), 6, ",000000"),
        (None, 6, ""),
        ("", 2, ""),
    ],
)
def test_escribir_numero(valor, decimales, esperado):
    assert escribir_numero(valor, decimales) == esperado
