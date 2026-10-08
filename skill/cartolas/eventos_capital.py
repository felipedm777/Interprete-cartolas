"""Eventos de capital de los fondos, tomados de DataFondos.

Las cartolas abonan dividendos, repartos de capital y disminuciones de capital
en la caja del cliente, pero no siempre dicen de qué fondo vienen ni de qué
evento se trata: la cartola BICE nueva imprime "DIVIDENDO EN PESOS" o "REPARTO
DE DINERO" sin el instrumento, y la Security pone el nemotécnico pero no el
monto por cuota con el que se puede comprobar el abono.

DataFondos publica, por fondo y serie, cada reparto con su fecha límite, su
fecha de pago y el monto por cuota. Con esa tabla, un abono se explica cuando
el monto por cuota de un evento multiplicado por las cuotas que el cliente
tiene en ese fondo da el monto abonado: eso identifica el fondo y distingue un
dividendo de un reparto o una disminución de capital. Lo que la tabla no
explica queda marcado como dudoso en el reporte, nunca completado a mano.

La tabla se consulta en DataFondos (`dividendos` por fondo, o
`resumen_dividendos` para saber qué fondos tiene) y se guarda en
`datos/eventos_capital.csv`. Para agregarle lo que devuelve la herramienta,
guardar cada respuesta en un archivo JSON y correr:

    python -m cartolas.eventos_capital <respuesta.json>...

La tabla solo tiene datos públicos de fondos: nunca datos de clientes.
"""

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from .catalogo import Catalogo
from .modelo import Cartola, Control, MovimientoCaja, MovimientoTitulo
from .numeros import leer_monto

RUTA_TABLA = Path(__file__).parent / "datos" / "eventos_capital.csv"

_COLUMNAS = (
    "RutFondo",
    "NemotecnicoInstrumento",
    "Clase",
    "Moneda",
    "MontoPorCuota",
    "FechaLimite",
    "FechaPago",
    "Anulado",
    "Evento",
)

# Clases de evento, normalizadas desde el texto que publica DataFondos.
DIVIDENDO = "DIVIDENDO"
REPARTO = "REPARTO DE CAPITAL"
DISMINUCION = "DISMINUCION DE CAPITAL"
EMISION = "EMISION LIBERADA"
OTRO = "OTRO"

# Tipo de movimiento de caja -> (clase de evento que lo paga, moneda).
# Son los tipos de los seis formatos que leen los extractores; la moneda vacía
# significa que la trae el movimiento.
TIPOS_CAJA = {
    "DIVIDENDO EN PESOS": (DIVIDENDO, "CLP"),
    "DIVIDENDO EN DOLARES": (DIVIDENDO, "USD"),
    "PAGO DE DIVIDENDOS": (DIVIDENDO, ""),
    "REPARTO DE DINERO": (REPARTO, "CLP"),
    "REPARTO DE DINERO EN USD": (REPARTO, "USD"),
    "DISMINUCION DE CAPITAL - ABONO EN CUENTA MERCANTIL": (DISMINUCION, ""),
    "ABONO POR DISMINUCION DE CAPITAL": (DISMINUCION, ""),
}

# Movimientos de títulos que la cartola imprime por el mismo evento, con el
# monto por cuota en la columna de precio (Security y Larrainvial): sirven para
# comprobar el evento sin depender de las cuotas del cierre.
TIPOS_TITULOS = {
    "DIVIDENDO": DIVIDENDO,
    "DISMINUCION DE CAPITAL": DISMINUCION,
    "REPARTO DE CAPITAL": REPARTO,
    "EMISION LIBERADA": EMISION,
}

# Un reparto de capital y una disminución de capital son el mismo hecho con dos
# nombres: la Bolsa informa unos como "REPARTO CAP." y otros como "DISMINUCION",
# y las cartolas tampoco coinciden. Al buscar el evento de un abono se aceptan
# las dos clases.
_EQUIVALENTES = {REPARTO: (REPARTO, DISMINUCION), DISMINUCION: (DISMINUCION, REPARTO)}

# La cartola fecha el abono cuando el dinero entra o se devenga en la caja, que
# puede ser días antes o después de la fecha de pago que informa el fondo.
_DIAS_ANTES = 6
_DIAS_DESPUES = 12
# BICE imprime los montos en pesos sin decimales y los de dólares redondeados a
# entero, y las cuotas con derecho a reparto son las de la fecha límite, que
# pueden no ser las del cierre: el monto esperado se acepta con esta holgura
# relativa, con un piso por el redondeo.
_HOLGURA = Decimal("0.005")
_PISO = {"CLP": Decimal(1), "USD": Decimal("0.5")}


@dataclass(frozen=True)
class Evento:
    rut_fondo: str
    nemotecnico: str
    clase: str
    moneda: str
    monto_por_cuota: Decimal | None
    fecha_limite: date | None
    fecha_pago: date | None
    # Excluido a mano del cálculo del valor cuota en DataFondos (la Bolsa lo
    # informó como reparto pero el valor cuota no bajó): no paga dinero.
    anulado: bool = False
    # Texto tal como lo publica DataFondos, para poder rastrear el dato.
    texto: str = ""


@dataclass
class Conciliacion:
    """Qué se pudo explicar con la tabla de eventos."""

    # Abonos que la tabla explica: el instrumento y la clase del evento cuadran
    # con el monto.
    confirmados: int = 0
    # Abonos que no traían instrumento y la tabla identificó.
    asignados: int = 0
    # Abonos que la tabla no explica, con el motivo.
    dudosos: list[str] = field(default_factory=list)
    # Discrepancias entre lo que trae la cartola y lo que publica DataFondos.
    revisar: list[str] = field(default_factory=list)
    # Fondos y fechas que faltan en la tabla, para ampliarla desde DataFondos.
    pendientes: set[tuple[str, str]] = field(default_factory=set)

    def extender(self, otra: "Conciliacion") -> None:
        self.confirmados += otra.confirmados
        self.asignados += otra.asignados
        self.dudosos += otra.dudosos
        self.revisar += otra.revisar
        self.pendientes |= otra.pendientes


def clase_de(texto: str) -> str:
    """Clase de evento según el texto de DataFondos."""
    t = texto.upper()
    if "DIVIDENDO" in t:
        return DIVIDENDO
    if "REPARTO" in t:
        return REPARTO
    if "DISMINUC" in t:
        return DISMINUCION
    if "EMIS" in t:
        return EMISION
    return OTRO


def monto_de(texto: str, pago_por_accion: str | float | None = None) -> Decimal | None:
    """Monto por cuota del evento.

    DataFondos lo trae redondeado a tres decimales en ``pago_por_accion`` y
    completo dentro del texto del evento ("DIVIDENDO PROV. $ 264,8097994"):
    se prefiere el del texto, que es el que cuadra con el abono.
    """
    m = re.search(r"(?:US\$|\$)\s*([\d.]+,\d+|[\d.]+)\s*$", texto.strip())
    if m:
        try:
            return leer_monto(m.group(1))
        except ValueError:
            pass
    if pago_por_accion in (None, ""):
        return None
    return Decimal(str(pago_por_accion))


def moneda_de(texto: str) -> str:
    """Moneda del evento: DataFondos usa "$" y "US$"."""
    t = texto.upper()
    if "US$" in t or "USD" in t:
        return "USD"
    if "$" in t:
        return "CLP"
    return ""


def _fecha(texto: str) -> date | None:
    return date.fromisoformat(texto) if texto else None


class Tabla:
    """Eventos de capital por nemotécnico."""

    def __init__(self, eventos: list[Evento]):
        self.eventos = eventos
        self._por_nemo: dict[str, list[Evento]] = {}
        for e in eventos:
            self._por_nemo.setdefault(e.nemotecnico.upper(), []).append(e)

    def __len__(self) -> int:
        return len(self.eventos)

    @classmethod
    def cargar(cls, ruta: Path = RUTA_TABLA) -> "Tabla":
        if not ruta.exists():
            return cls([])
        with open(ruta, encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f, delimiter=";"))
        faltan = [c for c in _COLUMNAS if filas and c not in filas[0]]
        if faltan:
            raise ValueError(f"{ruta}: faltan las columnas {', '.join(faltan)}")
        return cls(
            [
                Evento(
                    rut_fondo=r["RutFondo"],
                    nemotecnico=r["NemotecnicoInstrumento"],
                    clase=r["Clase"] or clase_de(r["Evento"]),
                    moneda=r["Moneda"] or moneda_de(r["Evento"]),
                    monto_por_cuota=leer_monto(r["MontoPorCuota"]) if r["MontoPorCuota"] else None,
                    fecha_limite=_fecha(r["FechaLimite"]),
                    fecha_pago=_fecha(r["FechaPago"]),
                    anulado=r["Anulado"].strip().upper() in ("1", "SI", "SÍ", "TRUE"),
                    texto=r["Evento"],
                )
                for r in filas
            ]
        )

    def periodo(self) -> tuple[date, date] | None:
        """Primera y última fecha de pago de la tabla."""
        fechas = [e.fecha_pago for e in self.eventos if e.fecha_pago]
        return (min(fechas), max(fechas)) if fechas else None

    def buscar(self, nemotecnico: str, clase: str, fecha: date, moneda: str = "") -> list[Evento]:
        """Eventos de ese fondo que pueden pagar un abono de esa clase en esa fecha."""
        clases = _EQUIVALENTES.get(clase, (clase,))
        return [
            e
            for e in self._por_nemo.get(nemotecnico.upper(), [])
            if e.clase in clases
            and not e.anulado
            and e.monto_por_cuota
            and e.fecha_pago
            and -timedelta(days=_DIAS_ANTES) <= fecha - e.fecha_pago <= timedelta(days=_DIAS_DESPUES)
            and (not moneda or not e.moneda or e.moneda == moneda)
        ]

    def cubre(self, nemotecnico: str) -> bool:
        return nemotecnico.upper() in self._por_nemo


def _parece_fondo(nemotecnico: str) -> bool:
    """Si el nemotécnico es de un fondo, los únicos que publica DataFondos.

    Los nemotécnicos de los fondos de inversión y mutuos chilenos empiezan con
    CFI o CFM; las acciones no, y sus dividendos no están en DataFondos.
    """
    return nemotecnico.upper().startswith(("CFI", "CFM"))


def _monto(m: MovimientoCaja) -> Decimal:
    return m.abono - m.cargo


def _cuadra(esperado: Decimal, monto: Decimal, moneda: str) -> bool:
    holgura = max(abs(esperado) * _HOLGURA, _PISO.get(moneda, Decimal(1)))
    return abs(esperado - monto) <= holgura


def _mismo_por_cuota(impreso: Decimal, publicado: Decimal) -> bool:
    """Si el monto por cuota impreso en la cartola es el que publica DataFondos,
    comparado con los decimales que imprime la cartola."""
    decimales = min(-impreso.as_tuple().exponent, 8)
    if decimales <= 0:
        return False
    unidad = Decimal(1).scaleb(-decimales)
    return abs(impreso - publicado.quantize(unidad)) <= unidad / 2


def conciliar(cartolas: list[Cartola], catalogo: Catalogo, tabla: Tabla) -> Conciliacion:
    """Identifica y comprueba con la tabla los abonos por eventos de capital.

    Completa el instrumento de los abonos que no lo traen cuando un solo fondo
    de la cuenta explica el monto, y deja en la conciliación los que no se
    pudieron explicar. No cambia un instrumento que la cartola ya trae: si no
    coincide con lo que publica DataFondos, lo anota para revisar.
    """
    total = Conciliacion()
    for cartola in cartolas:
        parte = _conciliar_cartola(cartola, catalogo, tabla)
        total.extender(parte)
        if parte.asignados:
            cartola.avisos.append(
                f"{parte.asignados} abonos por eventos de capital identificados con DataFondos"
            )
        if parte.confirmados:
            cartola.controles.append(
                Control(
                    "Eventos de capital contra DataFondos",
                    True,
                    f"{parte.confirmados} abonos cuadran con el reparto publicado",
                )
            )
        for texto in parte.revisar:
            cartola.controles.append(Control("Evento de capital contra DataFondos", False, texto))
        for texto in parte.dudosos:
            cartola.avisos.append(f"Dudoso (DataFondos no lo explica): {texto}")
    return total


def _conciliar_cartola(cartola: Cartola, catalogo: Catalogo, tabla: Tabla) -> Conciliacion:
    resultado = Conciliacion()
    if not len(tabla):
        return resultado
    cuotas = _cuotas_por_cuenta(cartola, catalogo)
    titulos = _titulos_por_cuenta(cartola, catalogo)
    for m in cartola.movimientos_caja:
        if m.tipo not in TIPOS_CAJA:
            continue
        clase, moneda_tipo = TIPOS_CAJA[m.tipo]
        moneda = moneda_tipo or m.moneda
        monto = _monto(m)
        if not monto:
            continue
        posiciones = cuotas.get(m.cuenta, {})
        # (nemotécnico, evento) que explican el abono: por el monto por cuota que
        # la cartola imprime en el movimiento de títulos del mismo evento, o por
        # las cuotas que la cuenta tiene en el fondo.
        explican = [
            (nemo, e)
            for nemo, cantidad in posiciones.items()
            for e in tabla.buscar(nemo, clase, m.fecha, moneda)
            if _cuadra(e.monto_por_cuota * cantidad, monto, moneda)
            or _explica_titulo(titulos.get((m.cuenta, nemo), []), e, monto, moneda)
        ]
        donde = f"{m.tipo} {moneda} del {m.fecha:%d-%m-%Y}"
        if m.instrumento:
            propios = [(n, e) for n, e in explican if n.upper() == m.instrumento.upper()]
            if propios:
                resultado.confirmados += 1
            elif tabla.buscar(m.instrumento, clase, m.fecha, moneda):
                otros = ", ".join(sorted({n for n, _ in explican}))
                resultado.revisar.append(
                    f"{donde} va con {m.instrumento}, pero el monto no cuadra con el evento "
                    f"que DataFondos publica para ese fondo"
                    + (f" y sí con {otros}" if otros else "")
                )
            elif _parece_fondo(m.instrumento):
                # La tabla no tiene el reparto que pagó este abono.
                resultado.pendientes.add((m.instrumento, f"{m.fecha:%Y-%m}"))
            continue
        candidatos = sorted({n for n, _ in explican})
        if len(candidatos) == 1:
            m.instrumento = candidatos[0]
            resultado.asignados += 1
        elif candidatos:
            resultado.dudosos.append(f"{donde}: lo explican {', '.join(candidatos)}")
        else:
            cubiertos = [n for n in posiciones if tabla.cubre(n)]
            resultado.dudosos.append(
                f"{donde}: ninguno de los fondos de la cuenta que están en la tabla lo explica"
                if cubiertos
                else f"{donde}: ningún instrumento de la cuenta está en la tabla (DataFondos "
                f"publica los repartos de los fondos, no los dividendos de acciones)"
            )
            resultado.pendientes |= {
                (n, f"{m.fecha:%Y-%m}")
                for n in posiciones
                if not tabla.cubre(n) and _parece_fondo(n)
            }
    return resultado


def _explica_titulo(
    titulos: list[MovimientoTitulo], evento: Evento, monto: Decimal, moneda: str
) -> bool:
    """Si la cartola trae el movimiento de títulos del evento, con el mismo monto
    por cuota que publica DataFondos y el monto del abono."""
    return any(
        t.precio
        and TIPOS_TITULOS.get(t.tipo) == evento.clase
        and _mismo_por_cuota(t.precio, evento.monto_por_cuota)
        and (t.monto is None or _cuadra(t.monto, monto, moneda))
        and (
            evento.fecha_pago is None
            or abs((t.fecha - evento.fecha_pago).days) <= _DIAS_DESPUES
        )
        for t in titulos
    )


def _titulos_por_cuenta(
    cartola: Cartola, catalogo: Catalogo
) -> dict[tuple[str, str], list[MovimientoTitulo]]:
    """Movimientos de títulos por evento de capital, por cuenta y nemotécnico."""
    titulos: dict[tuple[str, str], list[MovimientoTitulo]] = {}
    for t in cartola.movimientos_titulos:
        if t.tipo not in TIPOS_TITULOS:
            continue
        nemo = t.nemotecnico
        if not nemo:
            i = catalogo.buscar(t.instrumento, t.moneda) or catalogo.buscar_nemotecnico(
                t.instrumento, t.moneda
            )
            nemo = i.nemotecnico if i else ""
        if nemo:
            titulos.setdefault((t.cuenta, nemo), []).append(t)
    return titulos


def _cuotas_por_cuenta(cartola: Cartola, catalogo: Catalogo) -> dict[str, dict[str, Decimal]]:
    """Cuotas por nemotécnico en cada cuenta, sumando las posiciones repetidas."""
    cuentas: dict[str, dict[str, Decimal]] = {}
    for p in cartola.posiciones:
        if not p.cantidad:
            continue
        i = catalogo.buscar(p.instrumento, p.moneda, p.precio_actual) or catalogo.buscar_nemotecnico(
            p.instrumento, p.moneda
        )
        nemo = i.nemotecnico if i else p.nemotecnico
        if not nemo:
            continue
        cuenta = cuentas.setdefault(p.cuenta, {})
        cuenta[nemo] = cuenta.get(nemo, Decimal(0)) + p.cantidad
    return cuentas


# --- Mantener la tabla desde las respuestas de DataFondos ---------------------


def _desde_json(datos: object) -> list[Evento]:
    """Eventos de una respuesta de la herramienta `dividendos` de DataFondos."""
    filas = datos.get("data", []) if isinstance(datos, dict) else datos
    if not isinstance(filas, list):
        raise ValueError("la respuesta no trae una lista de eventos en 'data'")
    eventos = []
    for r in filas:
        texto = str(r.get("evento") or "")
        eventos.append(
            Evento(
                rut_fondo=str(r.get("rut") or ""),
                nemotecnico=str(r.get("nemo") or ""),
                clase=clase_de(texto),
                moneda=moneda_de(str(r.get("moneda") or "") + " " + texto),
                monto_por_cuota=monto_de(texto, r.get("pago_por_accion")),
                fecha_limite=_fecha(str(r.get("fecha_limite") or "")),
                fecha_pago=_fecha(str(r.get("fecha_pago") or "")),
                anulado=bool(r.get("anulado")),
                texto=texto,
            )
        )
    return eventos


def _texto_monto(valor: Decimal | None) -> str:
    return str(valor).replace(".", ",") if valor is not None else ""


def escribir(eventos: list[Evento], ruta: Path) -> None:
    """Escribe la tabla ordenada por fondo y fecha de pago."""
    filas = sorted(
        eventos,
        key=lambda e: (e.nemotecnico, e.fecha_pago or date.min, e.clase, e.texto),
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(_COLUMNAS), delimiter=";", lineterminator="\n")
        w.writeheader()
        for e in filas:
            w.writerow(
                {
                    "RutFondo": e.rut_fondo,
                    "NemotecnicoInstrumento": e.nemotecnico,
                    "Clase": e.clase,
                    "Moneda": e.moneda,
                    "MontoPorCuota": _texto_monto(e.monto_por_cuota),
                    "FechaLimite": e.fecha_limite.isoformat() if e.fecha_limite else "",
                    "FechaPago": e.fecha_pago.isoformat() if e.fecha_pago else "",
                    "Anulado": "1" if e.anulado else "0",
                    "Evento": e.texto,
                }
            )


def _clave(e: Evento) -> tuple:
    return (e.rut_fondo, e.nemotecnico.upper(), e.fecha_pago, e.clase, e.texto)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cartolas.eventos_capital",
        description="Agrega a la tabla de eventos de capital las respuestas de la herramienta "
        "`dividendos` de DataFondos, guardadas como archivos JSON.",
    )
    parser.add_argument("respuestas", nargs="+", help="archivos JSON con la respuesta de DataFondos")
    parser.add_argument("--tabla", default=str(RUTA_TABLA), help="tabla a actualizar")
    parser.add_argument(
        "--desde",
        help="descartar los eventos pagados antes de esta fecha, AAAA-MM-DD",
    )
    parser.add_argument(
        "--reemplazar",
        action="store_true",
        help="escribir solo los eventos de los archivos, sin los que ya tenía la tabla",
    )
    args = parser.parse_args(argv)

    ruta = Path(args.tabla)
    desde = date.fromisoformat(args.desde) if args.desde else None
    tenia = [] if args.reemplazar else Tabla.cargar(ruta).eventos
    nuevos: list[Evento] = []
    for nombre in args.respuestas:
        try:
            with open(nombre, encoding="utf-8") as f:
                nuevos += _desde_json(json.load(f))
        except (OSError, ValueError, json.JSONDecodeError) as e:
            parser.error(f"{nombre}: {e}")

    eventos: list[Evento] = []
    vistos = set()
    for e in tenia + nuevos:
        if not e.nemotecnico or (desde and (e.fecha_pago is None or e.fecha_pago < desde)):
            continue
        if _clave(e) in vistos:
            continue
        vistos.add(_clave(e))
        eventos.append(e)
    escribir(eventos, ruta)
    periodo = Tabla(eventos).periodo()
    print(
        f"{len(eventos)} eventos en {ruta}"
        + (f", pagos del {periodo[0]} al {periodo[1]}" if periodo else "")
    )
    print(f"{len(nuevos)} leídos de {len(args.respuestas)} respuestas; {len(eventos) - len(tenia)} nuevos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
