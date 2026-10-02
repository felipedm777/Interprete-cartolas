"""Lleva una cartola extraída a las filas de los archivos de saldos y movimientos.

Reglas tomadas del export de ejemplo (docs/formato-salida.md):

- La cuenta BICE define producto base, tipo de APV y régimen (catalogo.tipo_cuenta);
  las cartolas de otras instituciones los traen en la Cuenta.
- El instrumento define nombre, nemotécnico, emisor, producto y archivo (tabla maestra);
  si no está en la tabla, el producto y el archivo salen de la tabla de la cartola.
- SALDOS_FFMM se valoriza en la moneda del instrumento. En CUSTODIA_ACCIONES los
  instrumentos en USD se valorizan en USD en la cuenta de inversión y en pesos en
  las cuentas APV.
- Con valoración en pesos, patrimonioUSD = pesos / tipo de cambio; con valoración
  en USD, patrimonioCLP = USD × tipo de cambio. Los instrumentos en otras monedas
  (euros) se valorizan en pesos; la caja en euros, en euros.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .catalogo import Catalogo, Instrumento, TipoCuenta, tipo_cuenta
from .formato import (
    CUSTODIA_ACCIONES,
    MOVIMIENTOS_BOLSA,
    MOVIMIENTOS_DE_CAJA,
    MOVIMIENTOS_FFMM,
    SALDOS_CAJA,
    SALDOS_FFMM,
)
from .modelo import Cartola, Cuenta, Posicion
from .validar import destino

# Archivo y producto según la tabla de la cartola, para instrumentos que no están
# en la tabla maestra. Las tablas que no aparecen aquí no tienen archivo de destino.
_POR_TABLA = {
    "Fondos Mutuos": (SALDOS_FFMM.tipo, "FONDOS MUTUOS BICE"),
    "Fondos Inversión Bice": (SALDOS_FFMM.tipo, "FONDOS INVERSIÓN BICE"),
    "Fondos De Inversión": (CUSTODIA_ACCIONES.tipo, "CFI"),
    "CFI": (CUSTODIA_ACCIONES.tipo, "CFI"),
    "Acciones": (CUSTODIA_ACCIONES.tipo, "ACCIONES"),
    "ETF": (CUSTODIA_ACCIONES.tipo, "ETF"),
    # Fondos mutuos de otras administradoras (p. ej. Larrainvial).
    "Fondos Mutuos Otras AGF": (SALDOS_FFMM.tipo, "FONDOS MUTUOS"),
}

# Movimientos de caja que el export asigna al instrumento DOLAR.
_MOVIMIENTOS_DOLAR = {"CARGO EN DOLARES", "OPERACION DOLAR"}


@dataclass
class Salida:
    filas: dict[str, list[dict]] = field(default_factory=dict)
    # Lo que la cartola trae pero no se exportó, con el motivo.
    omitidos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def agregar(self, tipo: str, fila: dict) -> None:
        self.filas.setdefault(tipo, []).append(fila)

    def extender(self, otra: "Salida") -> None:
        for tipo, filas in otra.filas.items():
            self.filas.setdefault(tipo, []).extend(filas)
        self.omitidos += otra.omitidos
        self.avisos += otra.avisos


def es_afi(cuenta: Cuenta) -> bool:
    return "AFITRADING" in cuenta.portafolio.upper()


def _tipo(cuenta: Cuenta) -> TipoCuenta | None:
    if cuenta.producto_base:
        return TipoCuenta(cuenta.producto_base, cuenta.tipo_apv, cuenta.regimen)
    return tipo_cuenta(cuenta.numero)


def generar(cartola: Cartola, catalogo: Catalogo, solo_afi: bool = False) -> Salida:
    """Filas de los 7 archivos para una cartola.

    La fecha de proceso de los saldos es el cierre de la cartola y la de cada
    movimiento, su propia fecha.
    """
    salida = Salida()
    tc = cartola.tipo_cambio_usd
    tc_eur = cartola.tipo_cambio_eur
    cierre = cartola.hasta

    def cuenta_exportable(numero: str, que: str) -> Cuenta | None:
        cuenta = cartola.cuentas.get(numero)
        if cuenta is None:
            salida.omitidos.append(f"{que}: la cuenta {numero} no está en el resumen de cuentas")
            return None
        if _tipo(cuenta) is None:
            salida.omitidos.append(f"{que}: cuenta {numero} ({cuenta.grupo}) sin equivalente en el export")
            return None
        if solo_afi and not es_afi(cuenta):
            salida.omitidos.append(f"{que}: {cuenta.portafolio} no es de AFI Trading")
            return None
        return cuenta

    for saldo in cartola.saldos_caja:
        cuenta = cuenta_exportable(saldo.cuenta, f"Caja {saldo.moneda} {saldo.monto}")
        if cuenta is None:
            continue
        fila = _cliente(cartola.rut, cuenta, "CUENTAS CAJA", cierre)
        if saldo.moneda == "USD":
            fila |= _patrimonio("USD", tc, usd=saldo.monto)
            if fila["patrimonioCLP"] is None:
                fila["patrimonioCLP"] = saldo.monto_clp
        elif saldo.moneda == "CLP":
            fila |= _patrimonio("CLP", tc, clp=saldo.monto)
        else:
            clp = saldo.monto_clp
            if clp is None and saldo.moneda == "EUR" and tc_eur:
                clp = saldo.monto * tc_eur
            fila |= _patrimonio("CLP", tc, clp=clp)
            fila["MonedaValoracionPatrimonio"] = saldo.moneda
            fila["PatrimonioEnMonedaValoracion"] = saldo.monto
        fila |= _cierre(tc, tc_eur)
        salida.agregar(SALDOS_CAJA.tipo, fila)

    for p in cartola.posiciones:
        que = f"{p.tabla} {p.instrumento}"
        instrumento = _instrumento(catalogo, p.instrumento, p.moneda, p.precio_actual, p.nemotecnico)
        if instrumento:
            archivo, producto = instrumento.archivo, instrumento.producto
        elif p.tabla in _POR_TABLA:
            archivo, producto = _POR_TABLA[p.tabla]
        else:
            salida.omitidos.append(f"{que} (cuenta {p.cuenta}): la tabla {p.tabla} no tiene archivo de destino")
            continue
        cuenta = cuenta_exportable(p.cuenta, que)
        if cuenta is None:
            continue
        if not instrumento:
            salida.avisos.append(f"{que}: no está en la tabla maestra, va sin emisor")
        fila = _cliente(cartola.rut, cuenta, producto, cierre)
        fila |= _datos_instrumento(p.instrumento, p.moneda, instrumento, p.nemotecnico)
        fila |= {
            "Cantidad": p.cantidad,
            "PrecioCierreEnMonedaValoracion": p.precio_actual,
            "PrecioPromedioCompra": p.precio_promedio,
        }
        fila |= _valor_posicion(p, archivo, cuenta, tc, tc_eur)
        fila |= _cierre(tc, tc_eur)
        salida.agregar(archivo, fila)

    for m in cartola.movimientos_caja:
        cuenta = cuenta_exportable(m.cuenta, f"Movimiento de caja {m.fecha} {m.tipo}")
        if cuenta is None:
            continue
        if m.tipo in _MOVIMIENTOS_DOLAR:
            producto, instrumento = "FORWARDS DIVISA", "DOLAR"
        elif m.instrumento:
            # Un dividendo o un cobro asociado a un instrumento va con su producto.
            datos = catalogo.buscar_nemotecnico(m.instrumento)
            producto = datos.producto if datos else "CUENTAS CAJA"
            instrumento = m.instrumento
        else:
            producto, instrumento = "CUENTAS CAJA", f"CAJA {m.moneda}"
        fila = _cliente(cartola.rut, cuenta, producto, m.fecha)
        fila |= {
            "Instrumento": instrumento,
            "nombreTipoMovimiento": m.tipo,
            "Moneda": m.moneda,
            "abono": m.abono,
            "cargo": m.cargo,
        }
        salida.agregar(MOVIMIENTOS_DE_CAJA.tipo, fila)

    for m in cartola.movimientos_titulos:
        que = f"Movimiento de títulos {m.fecha} {m.tipo} {m.instrumento}"
        archivo = destino(m)
        if not archivo:
            salida.omitidos.append(f"{que}: el tipo de movimiento no va a ningún archivo")
            continue
        cuenta = cuenta_exportable(m.cuenta, que)
        if cuenta is None:
            continue
        instrumento = _instrumento(catalogo, m.instrumento, m.moneda, m.precio, m.nemotecnico)
        fondo_mutuo = archivo == "FFMM"
        if instrumento:
            producto = instrumento.producto
        else:
            producto = "FONDOS MUTUOS BICE" if fondo_mutuo else ""
            salida.avisos.append(f"Movimiento {m.tipo} {m.instrumento}: no está en la tabla maestra, va sin emisor")
        fila = _cliente(cartola.rut, cuenta, producto, m.fecha)
        fila |= _datos_instrumento(m.instrumento, m.moneda, instrumento, m.nemotecnico)
        fila |= {
            "NombreTipoMovimiento": m.tipo,
            "Moneda": m.moneda,
            "Cantidad": m.cantidad,
            "PrecioTIR": m.precio,
            "MontoNeto": m.monto,
        }
        if fondo_mutuo:
            fila["NumeroRerferencia"] = m.referencia
            salida.agregar(MOVIMIENTOS_FFMM.tipo, fila)
        else:
            salida.agregar(MOVIMIENTOS_BOLSA.tipo, fila)
    return salida


def _instrumento(
    catalogo: Catalogo, nombre: str, moneda: str, precio: Decimal | None, nemotecnico: str = ""
) -> Instrumento | None:
    if nemotecnico and (i := catalogo.buscar_nemotecnico(nemotecnico, moneda)):
        return i
    return catalogo.buscar(nombre, moneda, precio)


def _cliente(rut: str, cuenta: Cuenta, producto: str, fecha: date) -> dict:
    tipo = _tipo(cuenta)
    return {
        "FechaProceso": fecha.isoformat(),
        "RutCliente": rut,
        "Cuenta": cuenta.numero,
        "Portafolio": cuenta.portafolio,
        "ProductoBase": tipo.producto_base,
        "Producto": producto,
        "TipoAPV": tipo.tipo_apv,
        "DescripcionTipoRegimenTributario": tipo.regimen,
    }


def _datos_instrumento(
    nombre: str, moneda: str, instrumento: Instrumento | None, nemotecnico: str = ""
) -> dict:
    # Con el nombre de la tabla maestra, que es el del export, aunque la cartola
    # lo escriba distinto (alias).
    return {
        "Instrumento": instrumento.nombre if instrumento else nombre,
        "NemotecnicoInstrumento": instrumento.nemotecnico if instrumento else nemotecnico,
        "MonedaInstrumento": instrumento.moneda if instrumento else moneda,
        "Emisor": instrumento.emisor if instrumento else "",
    }


def _patrimonio(
    moneda: str, tc: Decimal | None, clp: Decimal | None = None, usd: Decimal | None = None
) -> dict:
    if moneda == "USD":
        clp = usd * tc if tc and usd is not None else None
    else:
        usd = clp / tc if tc and clp is not None else None
    return {
        "MonedaValoracionPatrimonio": moneda,
        "PatrimonioEnMonedaValoracion": usd if moneda == "USD" else clp,
        "patrimonioUSD": usd,
        "patrimonioCLP": clp,
    }


def _valor_posicion(
    p: Posicion, archivo: str, cuenta: Cuenta, tc: Decimal | None, tc_eur: Decimal | None
) -> dict:
    moneda = p.moneda
    if archivo == CUSTODIA_ACCIONES.tipo and moneda == "USD":
        if _tipo(cuenta).producto_base != "CUENTA INVERSION":
            moneda = "CLP"
    if moneda not in ("CLP", "USD"):
        clp = p.valor_clp
        if clp is None and moneda == "EUR" and tc_eur and p.cantidad is not None and p.precio_actual is not None:
            clp = p.cantidad * p.precio_actual * tc_eur
        return _patrimonio("CLP", tc, clp=clp)
    if archivo == SALDOS_FFMM.tipo and p.cantidad is not None and p.precio_actual is not None:
        # Como en el export: patrimonio = cuotas × valor cuota, sin redondear.
        valor = p.cantidad * p.precio_actual
        return _patrimonio(moneda, tc, clp=valor, usd=valor)
    if moneda == "USD":
        # La cartola muestra los USD redondeados a entero; los centavos salen
        # del equivalente en pesos.
        if p.valor_clp is not None and tc:
            usd = (p.valor_clp / tc).quantize(Decimal("0.01"))
        else:
            usd = p.valor_usd
        return _patrimonio("USD", tc, usd=usd)
    return _patrimonio("CLP", tc, clp=p.valor_clp)


def _cierre(tc: Decimal | None, tc_eur: Decimal | None = None) -> dict:
    # Ninguna cartola marca saldos en tránsito.
    return {"EnTransito": "NO", "TipoCambioUSD": tc, "TipoCambioEUR": tc_eur}
