"""Eventos de capital de acciones y fondos, tomados de la Bolsa y de DataFondos.

Las cartolas abonan dividendos, repartos de capital y disminuciones de capital
en la caja del cliente, pero no siempre dicen de qué instrumento vienen ni de
qué evento se trata: la cartola BICE nueva imprime "DIVIDENDO EN PESOS" o
"REPARTO DE DINERO" sin el instrumento, y la Security pone el nemotécnico pero
no el monto por cuota con el que se puede comprobar el abono.

La Bolsa de Santiago y DataFondos publican cada dividendo y reparto con su
fecha límite, su fecha de pago y el monto por acción o cuota. Con esa tabla, un
abono se explica cuando el monto por cuota de un evento multiplicado por las
cuotas que el cliente tiene en ese instrumento da el monto abonado: eso
identifica el instrumento y distingue un dividendo de un reparto o una
disminución de capital. Lo que la tabla no explica queda marcado como dudoso en
el reporte, nunca completado a mano.

La tabla tiene dos partes:

- La de la Bolsa (`datos/eventos_bolsa_<AAAAMMDD>.csv`) sale del Excel de
  dividendos y repartos que la Bolsa publica cada día, con las acciones, los
  fondos de inversión y los emisores extranjeros que se transan en ella. Se
  baja y se regenera con `python -m cartolas.bolsa` (módulo `bolsa`).
- La de DataFondos (`datos/eventos_capital.csv`) se consulta fondo por fondo
  (`dividendos`) y completa los fondos que la Bolsa no publica. Junto a ella,
  `datos/datafondos_cobertura.csv` guarda lo que devuelve `resumen_dividendos`:
  qué fondos sigue DataFondos, hasta qué fecha tiene sus repartos y cuándo los
  actualizó. Para agregar las respuestas, guardar cada una en un archivo JSON y
  correr:

    python -m cartolas.eventos_capital <respuesta.json>...

Con la fecha del Excel de la Bolsa y la cobertura de DataFondos, cada abono
dudoso queda con su causa (falta bajar el Excel al día, falta consultar un
fondo, lo explican varios instrumentos, ningún reparto publicado cuadra, o nadie
publica un reparto que lo pague) y el reporte dice qué hacer.

Las tablas solo tienen datos públicos de instrumentos: nunca datos de clientes.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from .catalogo import Catalogo
from .modelo import Cartola, Control, MovimientoCaja, MovimientoTitulo
from .numeros import leer_monto

RUTA_TABLA = Path(__file__).parent / "datos" / "eventos_capital.csv"
RUTA_COBERTURA = Path(__file__).parent / "datos" / "datafondos_cobertura.csv"

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

_COLUMNAS_COBERTURA = (
    "Nemotecnico",
    "RutFondo",
    "Serie",
    "Nombre",
    "Eventos",
    "UltimaFecha",
    "Actualizado",
)

# De dónde viene un evento.
BOLSA = "Bolsa"
DATAFONDOS = "DataFondos"

# Causas de un abono dudoso, de las que se resuelven actualizando las tablas a
# las que ninguna fuente puede resolver.
POR_BAJAR = "Falta bajar el Excel de la Bolsa al día"
POR_CONSULTAR = "Falta consultar fondos en DataFondos"
VARIOS = "Lo explican varios instrumentos"
NO_CUADRA = "Ningún reparto publicado cuadra con el monto"
SIN_REPARTO = "Ni la Bolsa ni DataFondos publican un reparto que lo pague"
CAUSAS = (POR_BAJAR, POR_CONSULTAR, VARIOS, NO_CUADRA, SIN_REPARTO)

# Qué se sabe de un instrumento de la cuenta en la fecha de un abono.
_PUBLICADO = "con reparto publicado que no cuadra"
_BAJAR = "por bajar el Excel de la Bolsa"
_CONSULTAR = "por consultar en DataFondos"
_NO_SIGUE = "fondos que no siguen ni la Bolsa ni DataFondos"
_SIN_EVENTO = "sin reparto publicado en la fecha"
_OTRO = "acciones u otros instrumentos que la Bolsa no publica"
_ESTADOS = (_PUBLICADO, _BAJAR, _CONSULTAR, _NO_SIGUE, _SIN_EVENTO, _OTRO)

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
    # Texto tal como lo publica la fuente, para poder rastrear el dato.
    texto: str = ""
    fuente: str = DATAFONDOS


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
    # Abonos que traen su instrumento, pero ningún evento publicado los paga.
    sin_comprobar: list[str] = field(default_factory=list)
    # Discrepancias entre lo que trae la cartola y lo publicado.
    revisar: list[str] = field(default_factory=list)
    # Fondos y fechas que faltan en la tabla, para ampliarla desde DataFondos.
    pendientes: set[tuple[str, str]] = field(default_factory=set)
    # Abonos dudosos por causa (CAUSAS).
    causas: Counter = field(default_factory=Counter)

    def extender(self, otra: "Conciliacion") -> None:
        self.confirmados += otra.confirmados
        self.asignados += otra.asignados
        self.dudosos += otra.dudosos
        self.sin_comprobar += otra.sin_comprobar
        self.revisar += otra.revisar
        self.pendientes |= otra.pendientes
        self.causas += otra.causas


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

    def __init__(self, eventos: list[Evento], bolsa_al: date | None = None):
        self.eventos = eventos
        # Fecha del Excel de la Bolsa del que salieron sus eventos: trae todo
        # lo que la Bolsa había publicado ese día.
        self.bolsa_al = bolsa_al
        self._por_nemo: dict[str, list[Evento]] = {}
        for e in eventos:
            self._por_nemo.setdefault(_nemo_clave(e.nemotecnico), []).append(e)
        self._en_bolsa = {_nemo_clave(e.nemotecnico) for e in eventos if e.fuente == BOLSA}

    def __len__(self) -> int:
        return len(self.eventos)

    @classmethod
    def unir(cls, *tablas: "Tabla") -> "Tabla":
        fechas = [t.bolsa_al for t in tablas if t.bolsa_al]
        return cls([e for t in tablas for e in t.eventos], max(fechas) if fechas else None)

    def de(self, fuente: str) -> list[Evento]:
        return [e for e in self.eventos if e.fuente == fuente]

    def publica_la_bolsa(self, nemotecnico: str) -> bool:
        """Si la Bolsa publica los eventos de ese instrumento."""
        return _nemo_clave(nemotecnico) in self._en_bolsa

    @classmethod
    def cargar(
        cls, ruta: Path = RUTA_TABLA, fuente: str = DATAFONDOS, bolsa_al: date | None = None
    ) -> "Tabla":
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
                    fuente=fuente,
                )
                for r in filas
            ],
            bolsa_al,
        )

    def periodo(self, fuente: str | None = None) -> tuple[date, date] | None:
        """Primera y última fecha de pago de la tabla, o de una de sus fuentes."""
        eventos = self.eventos if fuente is None else self.de(fuente)
        fechas = [e.fecha_pago for e in eventos if e.fecha_pago]
        return (min(fechas), max(fechas)) if fechas else None

    def buscar(self, nemotecnico: str, clase: str, fecha: date, moneda: str = "") -> list[Evento]:
        """Eventos de ese fondo que pueden pagar un abono de esa clase en esa fecha."""
        clases = _EQUIVALENTES.get(clase, (clase,))
        return [
            e
            for e in self._por_nemo.get(_nemo_clave(nemotecnico), [])
            if e.clase in clases
            and not e.anulado
            and e.monto_por_cuota
            and e.fecha_pago
            and -timedelta(days=_DIAS_ANTES) <= fecha - e.fecha_pago <= timedelta(days=_DIAS_DESPUES)
            and (not moneda or not e.moneda or e.moneda == moneda)
        ]

    def ultimo_pago(self, nemotecnico: str) -> date | None:
        """Fecha de pago del último evento de ese fondo en la tabla."""
        fechas = [e.fecha_pago for e in self._por_nemo.get(_nemo_clave(nemotecnico), []) if e.fecha_pago]
        return max(fechas) if fechas else None


@dataclass(frozen=True)
class Seguido:
    """Un fondo y serie que DataFondos sigue, según `resumen_dividendos`."""

    nemotecnico: str  # como lo escribe DataFondos, para pedirle `dividendos`
    rut_fondo: str
    serie: str = ""
    nombre: str = ""
    # Repartos que tiene publicados y fecha del último.
    eventos: int = 0
    ultima_fecha: date | None = None
    # Cuándo DataFondos actualizó los repartos de este fondo.
    actualizado: date | None = None


class Cobertura:
    """Qué fondos sigue DataFondos y hasta cuándo tiene sus repartos."""

    def __init__(self, seguidos: list[Seguido]):
        self.seguidos = seguidos
        # DataFondos puede listar el mismo fondo con las dos grafías y los
        # repartos solo en una (CFI-AMG2AE sin eventos, CFIAMG2A-E con 45): vale
        # la que tiene más.
        self._por_nemo: dict[str, Seguido] = {}
        for x in sorted(seguidos, key=lambda x: (x.eventos, x.ultima_fecha or date.min)):
            self._por_nemo[_nemo_clave(x.nemotecnico)] = x

    def __len__(self) -> int:
        return len(self.seguidos)

    def buscar(self, nemotecnico: str) -> Seguido | None:
        return self._por_nemo.get(_nemo_clave(nemotecnico))

    def actualizada(self) -> date | None:
        fechas = [s.actualizado for s in self.seguidos if s.actualizado]
        return max(fechas) if fechas else None

    @classmethod
    def cargar(cls, ruta: Path = RUTA_COBERTURA) -> "Cobertura":
        if not ruta.exists():
            return cls([])
        with open(ruta, encoding="utf-8", newline="") as f:
            filas = list(csv.DictReader(f, delimiter=";"))
        faltan = [c for c in _COLUMNAS_COBERTURA if filas and c not in filas[0]]
        if faltan:
            raise ValueError(f"{ruta}: faltan las columnas {', '.join(faltan)}")
        return cls(
            [
                Seguido(
                    nemotecnico=r["Nemotecnico"],
                    rut_fondo=r["RutFondo"],
                    serie=r["Serie"],
                    nombre=r["Nombre"],
                    eventos=int(r["Eventos"] or 0),
                    ultima_fecha=_fecha(r["UltimaFecha"]),
                    actualizado=_fecha(r["Actualizado"]),
                )
                for r in filas
            ]
        )


def _nemo_clave(nemotecnico: str) -> str:
    """El nemotécnico sin guiones ni espacios, para buscarlo en la tabla.

    Un mismo fondo y serie se escribe con el guion en dos lugares, y el export de
    BICE usa los dos: `CFI-AMG3RE` y `CFIAMG3R-E`. DataFondos a veces publica
    solo uno, y la Bolsa pone uno en la columna de pesos y el otro en la de
    dólares.
    """
    return re.sub(r"[\s-]", "", nemotecnico.upper())


def _parece_fondo(nemotecnico: str) -> bool:
    """Si el nemotécnico es de un fondo, los únicos que sigue DataFondos.

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
    """Si el monto por cuota impreso en la cartola es el publicado, comparado
    con los decimales que imprime la cartola."""
    decimales = min(-impreso.as_tuple().exponent, 8)
    if decimales <= 0:
        return False
    unidad = Decimal(1).scaleb(-decimales)
    return abs(impreso - publicado.quantize(unidad)) <= unidad / 2


def conciliar(
    cartolas: list[Cartola],
    catalogo: Catalogo,
    tabla: Tabla,
    cobertura: Cobertura | None = None,
) -> Conciliacion:
    """Identifica y comprueba con la tabla los abonos por eventos de capital.

    Completa el instrumento de los abonos que no lo traen cuando un solo
    instrumento de la cuenta explica el monto, y deja en la conciliación los
    que no se pudieron explicar, con su causa. No cambia un instrumento que la
    cartola ya trae: si no coincide con lo publicado, lo anota para revisar.
    Con la fecha del Excel de la Bolsa y la cobertura de DataFondos distingue un
    instrumento que falta actualizar o consultar de uno que nadie sigue o que no
    publicó un reparto en la fecha; sin la cobertura, todo fondo que no está en
    la tabla queda por consultar.
    """
    cobertura = cobertura or Cobertura([])
    total = Conciliacion()
    for cartola in cartolas:
        parte = _conciliar_cartola(cartola, catalogo, tabla, cobertura)
        total.extender(parte)
        if parte.asignados:
            cartola.avisos.append(
                f"{parte.asignados} abonos por eventos de capital identificados con los repartos "
                "publicados"
            )
        if parte.confirmados:
            cartola.controles.append(
                Control(
                    "Eventos de capital contra los repartos publicados",
                    True,
                    f"{parte.confirmados} abonos cuadran con el reparto publicado",
                )
            )
        for texto in parte.revisar:
            cartola.controles.append(
                Control("Evento de capital contra los repartos publicados", False, texto)
            )
        for texto in parte.dudosos:
            cartola.avisos.append(f"Abono dudoso: {texto}")
        for texto in parte.sin_comprobar:
            cartola.avisos.append(f"Abono sin comprobar: {texto}")
    return total


def _conciliar_cartola(
    cartola: Cartola, catalogo: Catalogo, tabla: Tabla, cobertura: Cobertura
) -> Conciliacion:
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
        if monto <= 0:
            # Un cargo (PAGO DE DIVIDENDOS) es el pago al cliente de un dividendo
            # ya abonado, no el evento: el export lo deja como caja.
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
            propios = [(n, e) for n, e in explican if _nemo_clave(n) == _nemo_clave(m.instrumento)]
            if propios:
                resultado.confirmados += 1
            elif tabla.buscar(m.instrumento, clase, m.fecha, moneda):
                otros = ", ".join(sorted({n for n, _ in explican}))
                resultado.revisar.append(
                    f"{donde} va con {m.instrumento}, pero el monto no cuadra con el evento "
                    f"publicado para ese instrumento"
                    + (f" y sí con {otros}" if otros else "")
                )
            else:
                estado = _estado(m.instrumento, clase, m.fecha, moneda, tabla, cobertura)
                resultado.sin_comprobar.append(f"{donde} va con {m.instrumento}: {estado}")
                if estado == _CONSULTAR:
                    # La tabla no tiene el reparto que pagó este abono y
                    # DataFondos puede tenerlo.
                    resultado.pendientes.add((m.instrumento, f"{m.fecha:%Y-%m}"))
            continue
        candidatos = sorted({n for n, _ in explican})
        if len(candidatos) == 1:
            m.instrumento = candidatos[0]
            resultado.asignados += 1
            continue
        if candidatos:
            causa, detalle = VARIOS, f"lo explican {', '.join(candidatos)}"
        else:
            estados = {
                n: _estado(n, clase, m.fecha, moneda, tabla, cobertura) for n in sorted(posiciones)
            }
            causa = (
                POR_BAJAR
                if _BAJAR in estados.values()
                else POR_CONSULTAR
                if _CONSULTAR in estados.values()
                else NO_CUADRA
                if _PUBLICADO in estados.values()
                else SIN_REPARTO
            )
            grupos = [
                f"{estado}: {', '.join(n for n, e in estados.items() if e == estado)}"
                for estado in _ESTADOS
                if estado in estados.values()
            ]
            detalle = "; ".join(grupos) if grupos else "la cuenta no tiene posiciones"
            resultado.pendientes |= {
                (n, f"{m.fecha:%Y-%m}") for n, e in estados.items() if e == _CONSULTAR
            }
        resultado.causas[causa] += 1
        resultado.dudosos.append(f"{donde}. {causa} ({detalle})")
    return resultado


def _estado(
    nemotecnico: str, clase: str, fecha: date, moneda: str, tabla: Tabla, cobertura: Cobertura
) -> str:
    """Qué se sabe de lo que ese instrumento pudo pagar en la fecha."""
    if tabla.buscar(nemotecnico, clase, fecha, moneda):
        return _PUBLICADO
    if tabla.publica_la_bolsa(nemotecnico):
        # El Excel de la Bolsa trae los eventos anunciados hasta su fecha, que
        # se anuncian antes de pagarse: si es del día del abono o posterior, el
        # evento que lo pagó tendría que estar.
        return _SIN_EVENTO if tabla.bolsa_al and tabla.bolsa_al >= fecha else _BAJAR
    if not _parece_fondo(nemotecnico):
        # Sin tabla de la Bolsa no se sabe si la Bolsa publica sus dividendos.
        return _OTRO if tabla.bolsa_al else _BAJAR
    if not len(cobertura):
        # Sin saber qué fondos sigue DataFondos, todo fondo que falta se consulta.
        return _CONSULTAR
    seguido = cobertura.buscar(nemotecnico)
    if seguido is None:
        return _NO_SIGUE
    if seguido.actualizado is None or seguido.actualizado < fecha:
        # La cobertura es anterior al abono: DataFondos puede haber publicado
        # el reparto después.
        return _CONSULTAR
    ultimo = tabla.ultimo_pago(nemotecnico)
    if (
        seguido.ultima_fecha
        and seguido.ultima_fecha >= fecha - timedelta(days=_DIAS_DESPUES)
        and (ultimo is None or seguido.ultima_fecha > ultimo)
    ):
        # DataFondos tiene repartos de ese fondo más nuevos que la tabla.
        return _CONSULTAR
    return _SIN_EVENTO


def _explica_titulo(
    titulos: list[MovimientoTitulo], evento: Evento, monto: Decimal, moneda: str
) -> bool:
    """Si la cartola trae el movimiento de títulos del evento, con el mismo monto
    por cuota publicado y el monto del abono."""
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


def _filas(datos: object) -> list[dict]:
    filas = datos.get("data", []) if isinstance(datos, dict) else datos
    if not isinstance(filas, list) or not all(isinstance(r, dict) for r in filas):
        raise ValueError("la respuesta no trae una lista de filas en 'data'")
    return filas


def _es_resumen(filas: list[dict]) -> bool:
    """Si las filas son de `resumen_dividendos` (un fondo por fila) y no de
    `dividendos` (un evento por fila)."""
    return bool(filas) and all("evento" not in r and "total" in r for r in filas)


def _cobertura_json(datos: object) -> list[Seguido]:
    """Fondos de una respuesta de la herramienta `resumen_dividendos`."""
    return [
        Seguido(
            nemotecnico=str(r.get("nemo") or ""),
            rut_fondo=str(r.get("rut") or ""),
            serie=str(r.get("serie") or ""),
            nombre=str(r.get("nombre") or ""),
            eventos=int(r.get("total") or 0),
            ultima_fecha=_fecha(str(r.get("ultima_fecha") or "")),
            actualizado=_fecha(
                str(r.get("ultima_actualizacion_exitosa") or r.get("ultima_actualizacion") or "")[:10]
            ),
        )
        for r in _filas(datos)
        if r.get("nemo")
    ]


def escribir_cobertura(seguidos: list[Seguido], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(_COLUMNAS_COBERTURA), delimiter=";", lineterminator="\n")
        w.writeheader()
        for x in sorted(seguidos, key=lambda x: (x.nombre, x.serie, x.nemotecnico)):
            w.writerow(
                {
                    "Nemotecnico": x.nemotecnico,
                    "RutFondo": x.rut_fondo,
                    "Serie": x.serie,
                    "Nombre": x.nombre,
                    "Eventos": x.eventos,
                    "UltimaFecha": x.ultima_fecha.isoformat() if x.ultima_fecha else "",
                    "Actualizado": x.actualizado.isoformat() if x.actualizado else "",
                }
            )


def _desde_json(datos: object) -> list[Evento]:
    """Eventos de una respuesta de la herramienta `dividendos` de DataFondos."""
    filas = _filas(datos)
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
    # Sin notación científica: 1E-7 no se podría volver a leer.
    return format(valor, "f").replace(".", ",") if valor is not None else ""


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
        description="Agrega las respuestas de DataFondos, guardadas como archivos JSON: las de "
        "`dividendos` van a la tabla de eventos de capital y las de `resumen_dividendos`, a la "
        "cobertura (qué fondos sigue DataFondos y hasta cuándo).",
    )
    parser.add_argument("respuestas", nargs="+", help="archivos JSON con la respuesta de DataFondos")
    parser.add_argument("--tabla", default=str(RUTA_TABLA), help="tabla a actualizar")
    parser.add_argument("--cobertura", default=str(RUTA_COBERTURA), help="cobertura a actualizar")
    parser.add_argument(
        "--desde",
        help="no agregar de las respuestas los eventos pagados antes de esta fecha, AAAA-MM-DD "
        "(los que ya tenía la tabla se mantienen)",
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
    seguidos: list[Seguido] = []
    con_eventos = 0
    for nombre in args.respuestas:
        try:
            with open(nombre, encoding="utf-8") as f:
                datos = json.load(f)
            if _es_resumen(_filas(datos)):
                seguidos += _cobertura_json(datos)
            else:
                nuevos += _desde_json(datos)
                con_eventos += 1
        except (OSError, ValueError, json.JSONDecodeError) as e:
            parser.error(f"{nombre}: {e}")

    if seguidos:
        ruta_cobertura = Path(args.cobertura)
        # Cada resumen trae todos los fondos que sigue DataFondos: el más nuevo
        # de cada fondo reemplaza al que había.
        por_nemo = {x.nemotecnico.upper(): x for x in Cobertura.cargar(ruta_cobertura).seguidos}
        por_nemo.update({x.nemotecnico.upper(): x for x in seguidos})
        cobertura = Cobertura(list(por_nemo.values()))
        escribir_cobertura(cobertura.seguidos, ruta_cobertura)
        print(
            f"Cobertura: {len(cobertura)} fondos en {ruta_cobertura}, actualizada al "
            f"{cobertura.actualizada()}"
        )
    if not con_eventos:
        return 0

    leidos = len(nuevos)
    if desde:
        nuevos = [e for e in nuevos if e.fecha_pago and e.fecha_pago >= desde]
    eventos: list[Evento] = []
    vistos = set()
    for e in tenia + nuevos:
        if not e.nemotecnico:
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
    print(f"{leidos} leídos de {con_eventos} respuestas; {len(eventos) - len(tenia)} nuevos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
