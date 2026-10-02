"""Anonimiza cartolas: reemplaza nombres y RUT de clientes en copias de los PDF y Excel.

Uso (en la carpeta "Interprete Cartolas", donde están "Training Data" y "Example"):

    py -m pip install pymupdf openpyxl
    py anonimizar_cartolas.py

1. La primera vez busca todos los RUT en las cartolas y crea "clientes.csv" con
   cada RUT y el nombre que aparece junto a él. Ábrelo en Excel, corrige los
   nombres y pon "no" en la columna "anonimizar" para los RUT que no son de
   clientes (por ejemplo, el RUT del banco).
2. La segunda vez escribe las copias anonimizadas en la carpeta "anonimizado",
   verifica que no quede ningún nombre ni RUT real y deja un resumen.

Los originales nunca se modifican. "clientes.csv", "mapeo_anonimizacion.csv" y
"reporte_anonimizacion.txt" tienen datos reales: quedan solo en este computador,
fuera de "anonimizado", y no deben subirse a ningún lado. Un archivo que no pasa
la verificación no se copia a "anonimizado", así que esa carpeta se puede
compartir completa.
"""

import argparse
import csv
import random
import re
import shutil
import sys
import unicodedata
from pathlib import Path

try:
    import pymupdf
except ImportError:  # versiones antiguas de PyMuPDF
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

try:
    import openpyxl
    import openpyxl.comments
except ImportError:
    openpyxl = None


CARPETAS_ENTRADA = ("Training Data", "Example")
CARPETA_SALIDA = "anonimizado"
ARCHIVO_CLIENTES = "clientes.csv"
ARCHIVO_MAPEO = "mapeo_anonimizacion.csv"
ARCHIVO_REPORTE = "reporte_anonimizacion.txt"
ARCHIVO_RESUMEN = "RESUMEN.txt"
ARCHIVO_CLAVES = "claves.txt"  # opcional: una clave de PDF por línea

EXT_PDF = {".pdf"}
EXT_EXCEL = {".xlsx", ".xlsm"}
EXT_TEXTO = {".csv", ".txt"}

# RUT con puntos (12.345.678-9) o sin puntos (12345678-9), con o sin espacios
# alrededor del guion. El cuerpo va de 1.000.000 a 99.999.999.
RUT_RE = re.compile(
    r"(?<![\d.])(\d{1,2}(?:\.\d{3}){2}|\d{7,8})(\s*-\s*)([\dkK])(?![\dA-Za-z])"
)

# Palabras que acompañan a un RUT o a un nombre y que no son parte del nombre.
ETIQUETAS = {
    "RUT", "R.U.T", "R.U.T.", "RUN", "NOMBRE", "NOMBRES", "CLIENTE", "TITULAR",
    "SR", "SR.", "SRA", "SRA.", "SRES", "SRES.", "SENOR", "SENORA", "SENORES",
    "DON", "DONA", "RAZON", "SOCIAL", "N", "NO", "NRO", "NUM",
}

# Palabras cortas que se dejan igual dentro de un nombre de empresa.
CONECTORES = {"DE", "DEL", "LA", "LAS", "EL", "LOS", "Y", "E", "&"}

SUFIJOS_EMPRESA = {
    "SPA", "LTDA", "LTDA.", "LIMITADA", "S.A.", "SA", "S.A", "EIRL", "E.I.R.L.",
    "INVERSIONES", "SOCIEDAD", "COMERCIAL", "ASESORIAS", "INMOBILIARIA",
}

# Dos listas para que los nombres de pila falsos de una persona no mezclen géneros.
NOMBRES_FALSOS = [
    [
        "Ana", "Eva", "Luz", "Ines", "Rosa", "Sara", "Elena", "Paula", "Laura",
        "Marta", "Julia", "Clara", "Sofia", "Lucia", "Andrea", "Camila", "Daniela",
        "Valeria", "Carolina", "Fernanda", "Gabriela", "Francisca", "Constanza",
    ],
    [
        "Ivo", "Leo", "Luis", "Raul", "Saul", "Hugo", "Ivan", "Pablo", "Pedro",
        "Mario", "Jorge", "Diego", "Tomas", "Andres", "Carlos", "Felipe", "Matias",
        "Rodrigo", "Gonzalo", "Ignacio", "Eduardo", "Cristian", "Sebastian",
        "Francisco", "Maximiliano",
    ],
]

APELLIDOS_FALSOS = [
    "Paz", "Lara", "Mena", "Vera", "Rojo", "Soto", "Lagos", "Ortiz", "Pinto",
    "Toro", "Vidal", "Bravo", "Reyes", "Rivas", "Ponce", "Molina", "Robles",
    "Tapia", "Fuentes", "Salinas", "Cabrera", "Aguilera", "Carrasco",
    "Figueroa", "Sepulveda", "Valenzuela", "Riquelme", "Saavedra", "Alvarado",
    "Contreras", "Hernandez", "Villalobos", "Valderrama", "Montenegro",
    "Santibanez", "Echeverria",
]

# Si el nombre junto a un RUT tiene alguna de estas palabras, probablemente es
# la institución y no un cliente: se propone "no" en clientes.csv.
PALABRAS_INSTITUCION = {
    "BANCO", "BANK", "CORREDORA", "CORREDORES", "AGF", "ADMINISTRADORA", "SEGUROS",
    "BOLSA", "VALORES", "CUSTODIA", "FINANCIERA", "AFP", "FONDO", "FONDOS",
}

PALABRAS_EMPRESA_FALSAS = [
    "Alerce", "Coigue", "Quillay", "Peumo", "Boldo", "Maiten", "Litre",
    "Arrayan", "Canelo", "Lenga", "Raulí", "Ulmo", "Tepa", "Luma",
]


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------

def sin_acentos(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalizar(texto):
    """Mayúsculas, sin acentos y con espacios simples, para comparar."""
    return re.sub(r"\s+", " ", sin_acentos(texto).upper()).strip()


def limpiar_token(token):
    return normalizar(token).strip(".,;:()[]\"'")


def digito_verificador(cuerpo):
    suma, factor = 0, 2
    for d in reversed(str(cuerpo)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


def cuerpo_rut(texto_cuerpo):
    return int(texto_cuerpo.replace(".", ""))


def formatear_rut(cuerpo, dv, como):
    """Escribe un RUT con el mismo estilo (puntos, separador) que `como`."""
    cuerpo_txt = str(cuerpo)
    if "." in como.group(1):
        cuerpo_txt = f"{cuerpo:,}".replace(",", ".")
    if como.group(3).islower():
        dv = dv.lower()
    return f"{cuerpo_txt}{como.group(2)}{dv}"


def mismo_estilo(original, falso):
    """Copia mayúsculas/minúsculas del original al reemplazo, palabra por palabra."""
    pal_orig, pal_falso = original.split(), falso.split()
    if len(pal_orig) == len(pal_falso) and len(pal_orig) > 1:
        return " ".join(mismo_estilo(o, f) for o, f in zip(pal_orig, pal_falso))
    if limpiar_token(original) == limpiar_token(falso):
        return original  # palabra que no cambia (SpA, Ltda., de, los)
    letras = [c for c in original if c.isalpha()]
    if letras and all(c.isupper() for c in letras):
        return falso.upper()
    if letras and all(c.islower() for c in letras):
        return falso.lower()
    if letras and letras[0].isupper() and all(c.islower() for c in letras[1:]):
        return falso.capitalize()
    return falso


# --------------------------------------------------------------------------
# Clientes y mapeo real -> falso
# --------------------------------------------------------------------------

class Cliente:
    def __init__(self, rut, nombre, tipo):
        self.rut = rut  # int (cuerpo) o None
        self.nombre = nombre.strip()
        self.tipo = tipo
        self.palabras = [t for t in self.nombre.split() if limpiar_token(t)]
        self.tokens = [limpiar_token(t) for t in self.palabras]
        self.falsos = []
        self.rut_falso = None

    @property
    def es_empresa(self):
        return self.tipo == "empresa" or any(t in SUFIJOS_EMPRESA for t in self.tokens)

    def secuencias(self):
        """Órdenes en que el nombre puede aparecer, como listas de índices de token."""
        n = len(self.tokens)
        if n == 0:
            return []
        if self.es_empresa or n == 1:
            return [list(range(n))]
        if n == 2:
            return [[0, 1], [1, 0]]
        nombres = list(range(n - 2))
        apellidos = [n - 2, n - 1]
        primero, paterno = nombres[0], apellidos[0]
        candidatas = [
            nombres + apellidos,
            apellidos + nombres,
            [primero] + apellidos,
            apellidos + [primero],
            nombres + [paterno],
            [paterno] + nombres,
            [primero, paterno],
            [paterno, primero],
            apellidos,
        ]
        if len(nombres) >= 2:
            candidatas.append(nombres)
        unicas = []
        for s in candidatas:
            if s not in unicas:
                unicas.append(s)
        return sorted(unicas, key=len, reverse=True)

    def indices_apellidos(self):
        """Los dos últimos tokens son apellidos (uno solo si el nombre tiene dos)."""
        n = len(self.tokens)
        if self.es_empresa or n < 2:
            return []
        return [n - 1] if n == 2 else [n - 2, n - 1]

    def apellidos_sueltos(self):
        return [i for i in self.indices_apellidos() if len(self.tokens[i]) >= 4]

    def nombres_sueltos(self):
        apellidos = self.indices_apellidos()
        if not apellidos:
            return []
        return [i for i in range(apellidos[0]) if len(self.tokens[i]) >= 3]


def elegir_parecido(lista, largo, usados, rng):
    """Elige una palabra de largo parecido (preferentemente no más larga) que no
    sea real ni se haya usado antes, para que dos clientes no compartan apellido."""
    libres = [p for p in lista if p.upper() not in usados] or list(lista)
    candidatos = sorted(libres, key=lambda p: (len(p) > largo, abs(len(p) - largo)))
    elegido = rng.choice(candidatos[:6])
    usados.add(elegido.upper())
    return elegido


def asignar_falsos(clientes, mapeo_previo, rng):
    ruts_usados = {c.rut for c in clientes if c.rut}
    usados = {t for c in clientes for t in c.tokens}  # palabras reales
    usados |= {normalizar(f) for nombre, _ in mapeo_previo.values() for f in nombre.split()}
    for c in clientes:
        clave = c.rut if c.rut else normalizar(c.nombre)
        if clave in mapeo_previo:
            nombre_falso, rut_falso = mapeo_previo[clave]
            c.falsos = nombre_falso.split()
            c.rut_falso = rut_falso
        if c.rut and not c.rut_falso:
            # mismo largo y mismo primer dígito: un RUT de persona sigue
            # pareciendo de persona y uno de empresa, de empresa
            digitos = len(str(c.rut))
            base = int(str(c.rut)[0]) * 10 ** (digitos - 1)
            while True:
                candidato = rng.randint(base, base + 10 ** (digitos - 1) - 1)
                if candidato not in ruts_usados:
                    break
            ruts_usados.add(candidato)
            c.rut_falso = candidato
        if len(c.falsos) != len(c.tokens):
            c.falsos = []
            nombres_falsos = rng.choice(NOMBRES_FALSOS)
            for i, tok in enumerate(c.tokens):
                if c.es_empresa:
                    if tok in SUFIJOS_EMPRESA or tok in CONECTORES:
                        c.falsos.append(c.palabras[i])
                    else:
                        c.falsos.append(elegir_parecido(PALABRAS_EMPRESA_FALSAS, len(tok), usados, rng))
                elif i in c.indices_apellidos():
                    c.falsos.append(elegir_parecido(APELLIDOS_FALSOS, len(tok), usados, rng))
                else:
                    c.falsos.append(elegir_parecido(nombres_falsos, len(tok), usados, rng))


def leer_csv_flexible(ruta):
    texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
    delimitador = ";" if texto.count(";") >= texto.count(",") else ","
    return list(csv.DictReader(texto.splitlines(), delimiter=delimitador))


def escribir_csv(ruta, filas, columnas):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
        w.writeheader()
        for fila in filas:
            w.writerow(fila)


def leer_clientes(ruta):
    clientes = []
    for fila in leer_csv_flexible(ruta):
        fila = {k.strip().lower(): (v or "").strip() for k, v in fila.items() if k}
        if fila.get("anonimizar", "si").lower() in ("no", "n"):
            continue
        rut_txt = fila.get("rut", "")
        m = re.match(r"^\s*([\d.]+)\s*-?\s*[\dkK]?\s*$", rut_txt)
        rut = cuerpo_rut(m.group(1)) if m and m.group(1).replace(".", "") else None
        nombre = fila.get("nombre", "")
        if not rut and not nombre:
            continue
        clientes.append(Cliente(rut, nombre, fila.get("tipo", "").lower()))
    return clientes


def leer_mapeo(ruta):
    mapeo = {}
    if not ruta.exists():
        return mapeo
    for fila in leer_csv_flexible(ruta):
        rut_real = fila.get("rut_real", "").strip()
        clave = int(rut_real) if rut_real.isdigit() else normalizar(fila.get("nombre_real", ""))
        rut_falso = fila.get("rut_falso", "").strip()
        mapeo[clave] = (fila.get("nombre_falso", ""), int(rut_falso) if rut_falso.isdigit() else None)
    return mapeo


def guardar_mapeo(ruta, clientes):
    filas = [{
        "rut_real": c.rut or "",
        "nombre_real": c.nombre,
        "rut_falso": c.rut_falso or "",
        "nombre_falso": " ".join(c.falsos),
    } for c in clientes]
    escribir_csv(ruta, filas, ["rut_real", "nombre_real", "rut_falso", "nombre_falso"])


# --------------------------------------------------------------------------
# Reemplazo en texto plano (Excel, CSV, nombres de archivo)
# --------------------------------------------------------------------------

LETRAS_EQUIVALENTES = {
    "A": "AÁÀÄÂ", "E": "EÉÈËÊ", "I": "IÍÌÏÎ", "O": "OÓÒÖÔ", "U": "UÚÙÜÛ", "N": "NÑ", "C": "CÇ",
}


def patron_token(token):
    partes = []
    for c in token:
        grupo = LETRAS_EQUIVALENTES.get(c)
        if grupo:
            partes.append("[" + grupo + grupo.lower() + "]")
        else:
            partes.append(re.escape(c))
    return "".join(partes)


class Reemplazador:
    def __init__(self, clientes):
        self.clientes = clientes
        self.ruts = {c.rut: c for c in clientes if c.rut}
        self.patrones = []  # (regex, cliente, secuencia)
        for c in clientes:
            for seq in c.secuencias():
                piezas = [patron_token(c.tokens[i]) for i in seq]
                sep = r"[\s,]+"
                regex = re.compile(r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + sep.join(piezas) + r"(?![\wÁÉÍÓÚÑáéíóúñ])", re.IGNORECASE)
                self.patrones.append((regex, c, seq))
            for i in c.apellidos_sueltos():
                regex = re.compile(r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + patron_token(c.tokens[i]) + r"(?![\wÁÉÍÓÚÑáéíóúñ])", re.IGNORECASE)
                self.patrones.append((regex, c, [i]))
        self.patrones.sort(key=lambda p: len(p[2]), reverse=True)

    def rut_falso_texto(self, m):
        cliente = self.ruts.get(cuerpo_rut(m.group(1)))
        if not cliente:
            return None
        return formatear_rut(cliente.rut_falso, digito_verificador(cliente.rut_falso), m)

    def texto_falso(self, original, cliente, seq):
        palabras = [cliente.falsos[i] for i in seq]
        coma = "," in original
        if coma and len(seq) > 1:
            # "PEREZ GONZALEZ, JUAN": la coma va después de los apellidos.
            n_ap = len([i for i in seq if i in cliente.indices_apellidos()])
            falso = " ".join(palabras[:n_ap]) + ", " + " ".join(palabras[n_ap:])
        else:
            falso = " ".join(palabras)
        return mismo_estilo(original, falso)

    def reemplazar(self, texto):
        cambios = 0

        def sub_rut(m):
            nonlocal cambios
            nuevo = self.rut_falso_texto(m)
            if nuevo is None:
                return m.group(0)
            cambios += 1
            return nuevo

        texto = RUT_RE.sub(sub_rut, texto)
        for regex, cliente, seq in self.patrones:
            def sub_nombre(m, cliente=cliente, seq=seq):
                nonlocal cambios
                cambios += 1
                return self.texto_falso(m.group(0), cliente, seq)
            texto = regex.sub(sub_nombre, texto)
        return texto, cambios


# --------------------------------------------------------------------------
# Verificación
# --------------------------------------------------------------------------

class Verificador:
    def __init__(self, clientes):
        self.rut_res = []
        self.nombre_res = []
        self.suelto_res = []
        for c in clientes:
            if c.rut:
                self.rut_res.append(re.compile(
                    r"(?<!\d)" + str(c.rut) + r"\s*-?\s*" + digito_verificador(c.rut) + r"(?![\dA-Z])"))
            for seq in c.secuencias():
                if len(seq) >= 2 or c.es_empresa:
                    self.nombre_res.append(re.compile(
                        r"(?<![A-Z])" + r"[\s,]+".join(re.escape(c.tokens[i]) for i in seq) + r"(?![A-Z])"))
            for i in c.apellidos_sueltos():
                self.nombre_res.append(re.compile(r"(?<![A-Z])" + re.escape(c.tokens[i]) + r"(?![A-Z])"))
            for i in c.nombres_sueltos():
                self.suelto_res.append((c.tokens[i], re.compile(r"(?<![A-Z])" + re.escape(c.tokens[i]) + r"(?![A-Z])")))

    def revisar(self, texto):
        """Devuelve (problemas, avisos). Problemas impiden copiar el archivo."""
        norm = normalizar(texto)
        sin_puntos = norm.replace(".", "")
        problemas = []
        for r in self.rut_res:
            if r.search(sin_puntos):
                problemas.append("queda un RUT real")
                break
        for r in self.nombre_res:
            if r.search(norm):
                problemas.append("queda un nombre real")
                break
        avisos = sorted({tok for tok, r in self.suelto_res if r.search(norm)})
        return problemas, avisos


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def texto_legible(texto):
    utiles = [c for c in texto if not c.isspace()]
    if not utiles:
        return True
    raros = sum(1 for c in utiles if unicodedata.category(c).startswith("C") or c == "\ufffd")
    return raros / len(utiles) < 0.05


def pagina_escaneada(pagina):
    texto = pagina.get_text("text").strip()
    if len(texto) >= 50:
        return False
    area_pagina = abs(pagina.rect)
    area_imagenes = 0
    for info in pagina.get_image_info():
        area_imagenes += abs(pymupdf.Rect(info["bbox"]) & pagina.rect)
    return area_imagenes > 0.5 * area_pagina


def estilo_en(bloques, rect):
    """Tamaño, color y negrita del texto que cae en `rect`."""
    mejor = None
    for bloque in bloques:
        for linea in bloque.get("lines", []):
            for span in linea["spans"]:
                inter = pymupdf.Rect(span["bbox"]) & rect
                if inter.is_empty:
                    continue
                area = abs(inter)
                if mejor is None or area > mejor[0]:
                    mejor = (area, span, linea["dir"])
    if mejor is None:
        return 9, (0, 0, 0), False, (rect.x0, rect.y1), (1, 0)
    _, span, direccion = mejor
    color = span["color"]
    rgb = ((color >> 16) & 255) / 255, ((color >> 8) & 255) / 255, (color & 255) / 255
    negrita = bool(span["flags"] & 16) or "bold" in span["font"].lower()
    return span["size"], rgb, negrita, span["origin"], (round(direccion[0]), round(direccion[1]))


# Dirección del texto -> (rotación para insert_text, cómo ubicar el inicio)
ROTACIONES = {
    (1, 0): 0,     # horizontal normal
    (0, -1): 90,   # hacia arriba
    (-1, 0): 180,  # cabeza abajo
    (0, 1): 270,   # hacia abajo
}


def punto_inicio(rect, origen, direccion):
    """Dónde empieza a escribirse el reemplazo, sobre la línea base original."""
    return {
        (1, 0): pymupdf.Point(rect.x0, origen[1]),
        (0, -1): pymupdf.Point(origen[0], rect.y1),
        (-1, 0): pymupdf.Point(rect.x1, origen[1]),
        (0, 1): pymupdf.Point(origen[0], rect.y0),
    }[direccion]


def franja_central(rect, direccion):
    """La redacción borra todo carácter que toque el rectángulo; se usa solo la
    franja central (a lo largo del texto) para no borrar letras de líneas vecinas."""
    if direccion[1] == 0:
        alto = rect.height
        return pymupdf.Rect(rect.x0 + 0.3, rect.y0 + 0.3 * alto, rect.x1 - 0.3, rect.y1 - 0.3 * alto)
    ancho = rect.width
    return pymupdf.Rect(rect.x0 + 0.3 * ancho, rect.y0 + 0.3, rect.x1 - 0.3 * ancho, rect.y1 - 0.3)


def palabras_por_linea(pagina):
    lineas = {}
    for x0, y0, x1, y1, palabra, b, l, w in pagina.get_text("words"):
        lineas.setdefault((b, l), []).append((pymupdf.Rect(x0, y0, x1, y1), palabra))
    return list(lineas.values())


def buscar_nombres(pagina, reemplazador):
    """Busca secuencias de nombre en palabras consecutivas de una misma línea."""
    hallazgos = []
    for linea in palabras_por_linea(pagina):
        tokens = [limpiar_token(p) for _, p in linea]
        ocupado = [False] * len(linea)
        for _, cliente, seq in reemplazador.patrones:
            buscado = [cliente.tokens[i] for i in seq]
            n = len(buscado)
            for inicio in range(len(tokens) - n + 1):
                if any(ocupado[inicio:inicio + n]):
                    continue
                if tokens[inicio:inicio + n] == buscado:
                    rect = pymupdf.Rect(linea[inicio][0])
                    for r, _ in linea[inicio + 1:inicio + n]:
                        rect |= r
                    original = " ".join(p for _, p in linea[inicio:inicio + n])
                    falso = reemplazador.texto_falso(original, cliente, seq)
                    # conserva la puntuación pegada a las palabras, p. ej. "(PEREZ," o "PEREZ."
                    primera, final = linea[inicio][1], linea[inicio + n - 1][1]
                    cabeza = primera[:len(primera) - len(primera.lstrip("(\"'¿¡"))]
                    cola = final[len(final.rstrip(".,;:)\"'?!")):]
                    falso = cabeza + falso
                    if cola and not falso.endswith(cola):
                        falso += cola
                    hallazgos.append((rect, falso))
                    for k in range(inicio, inicio + n):
                        ocupado[k] = True
    return hallazgos


def buscar_ruts(pagina, reemplazador):
    hallazgos = []
    texto = pagina.get_text("text")
    vistos = set()
    for m in sorted(RUT_RE.finditer(texto), key=lambda m: len(m.group(0)), reverse=True):
        nuevo = reemplazador.rut_falso_texto(m)
        if nuevo is None or m.group(0) in vistos:
            continue
        vistos.add(m.group(0))
        for rect in pagina.search_for(m.group(0)):
            hallazgos.append((rect, nuevo))
    return hallazgos


def claves_de_rut(cuerpo):
    """Los bancos suelen proteger la cartola con el RUT del cliente o parte de él."""
    r, dv = str(cuerpo), digito_verificador(cuerpo)
    return [r, r + dv, r + "-" + dv, f"{cuerpo:,}".replace(",", ".") + "-" + dv, r[:4], r[:5], r[:6]]


def leer_claves_extra(raiz):
    ruta = raiz / ARCHIVO_CLAVES
    if not ruta.exists():
        return []
    return [l.strip() for l in ruta.read_text(encoding="utf-8-sig", errors="replace").splitlines() if l.strip()]


def claves_posibles(ruts, extra=()):
    claves = list(extra)
    for cuerpo in ruts:
        claves += claves_de_rut(cuerpo)
    return list(dict.fromkeys(claves))


def abrir_pdf(ruta, claves=()):
    """Abre el PDF, probando las claves si tiene. Devuelve None si ninguna sirve.

    Ojo: no se consulta needs_pass ni is_encrypted después de authenticate();
    en algunas versiones de PyMuPDF eso deja el contenido sin descifrar.
    """
    doc = pymupdf.open(ruta)
    if not doc.needs_pass:
        return doc
    for clave in claves:
        if doc.authenticate(clave):
            return doc
    doc.close()
    return None


def largo_texto(texto):
    return len(re.sub(r"\s+", "", texto))


def anonimizar_pdf(origen, destino, reemplazador, verificador, claves=()):
    doc = abrir_pdf(origen, claves)
    if doc is None:
        return 0, [f"el PDF tiene clave y no es el RUT de ningún cliente ni está en {ARCHIVO_CLAVES}"], []
    texto_original = largo_texto("".join(p.get_text("text") for p in doc))
    if texto_original == 0:
        doc.close()
        return 0, ["el PDF no tiene texto que se pueda leer (¿escaneado?)"], []
    problemas, avisos, cambios = [], [], 0
    for pagina in doc:
        for campo in pagina.widgets() or []:
            if isinstance(campo.field_value, str):
                nuevo, n = reemplazador.reemplazar(campo.field_value)
                if n:
                    campo.field_value = nuevo
                    campo.update()
                    cambios += n
        for anotacion in pagina.annots() or []:
            info = anotacion.info
            nuevo, n = reemplazador.reemplazar(info.get("content", ""))
            titulo, m = reemplazador.reemplazar(info.get("title", ""))
            if n or m:
                anotacion.set_info(content=nuevo, title=titulo)
                anotacion.update()
                cambios += n + m
        if pagina_escaneada(pagina):
            problemas.append(f"la página {pagina.number + 1} parece escaneada (imagen sin texto)")
            continue
        if not texto_legible(pagina.get_text("text")):
            problemas.append(f"el texto de la página {pagina.number + 1} no se puede leer bien")
            continue
        hallazgos = []
        for rect, nuevo in buscar_ruts(pagina, reemplazador) + buscar_nombres(pagina, reemplazador):
            if any(abs(rect & r) > 0.3 * abs(rect) for r, _ in hallazgos):
                continue
            hallazgos.append((rect, nuevo))
        if not hallazgos:
            continue
        bloques = pagina.get_text("dict")["blocks"]
        estilos = [estilo_en(bloques, rect) for rect, _ in hallazgos]
        if any(e[4] not in ROTACIONES for e in estilos):
            problemas.append(f"la página {pagina.number + 1} tiene un nombre o RUT en texto inclinado")
            continue
        for (rect, _), estilo in zip(hallazgos, estilos):
            pagina.add_redact_annot(franja_central(rect, estilo[4]), fill=None)
        opciones = {"images": pymupdf.PDF_REDACT_IMAGE_NONE}
        if hasattr(pymupdf, "PDF_REDACT_LINE_ART_NONE"):
            opciones["graphics"] = pymupdf.PDF_REDACT_LINE_ART_NONE
        pagina.apply_redactions(**opciones)
        for (rect, nuevo), (tamano, color, negrita, origen, direccion) in zip(hallazgos, estilos):
            pagina.insert_text(
                punto_inicio(rect, origen, direccion), nuevo,
                fontsize=tamano, fontname="hebo" if negrita else "helv", color=color,
                rotate=ROTACIONES[direccion],
            )
            cambios += 1
    if problemas:
        doc.close()
        return cambios, problemas, avisos

    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
    toc = doc.get_toc(simple=True)
    if toc:
        doc.set_toc([[nivel, reemplazador.reemplazar(titulo)[0], pag] for nivel, titulo, pag in toc])

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(destino, garbage=4, deflate=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
    doc.close()

    verificado = pymupdf.open(destino)
    partes = []
    for p in verificado:
        partes.append(p.get_text("text"))
        partes += [str(w.field_value) for w in (p.widgets() or []) if w.field_value]
        partes += [a.info.get("content", "") + " " + a.info.get("title", "") for a in (p.annots() or [])]
    texto = "\n".join(partes)
    texto += "\n" + " ".join(str(v) for v in (verificado.metadata or {}).values() if v)
    texto_final = largo_texto("".join(p.get_text("text") for p in verificado))
    verificado.close()
    problemas, avisos = verificador.revisar(texto)
    # Los reemplazos tienen largo parecido; si se pierde mucho texto, algo salió mal
    # y la verificación no sería confiable.
    if texto_final < 0.9 * texto_original:
        problemas.append(f"la copia perdió texto ({texto_final} de {texto_original} caracteres)")
    if problemas:
        destino.unlink()
    return cambios, problemas, avisos


# --------------------------------------------------------------------------
# Excel y texto
# --------------------------------------------------------------------------

def anonimizar_excel(origen, destino, reemplazador, verificador):
    libro = openpyxl.load_workbook(origen, keep_vba=origen.suffix.lower() == ".xlsm")
    cambios = 0
    for hoja in libro.worksheets:
        titulo, n = reemplazador.reemplazar(hoja.title)
        if n:
            hoja.title = titulo[:31]
            cambios += n
        columnas_rut, columnas_dv = set(), set()
        for fila in hoja.iter_rows():
            for celda in fila:
                if celda.comment is not None:
                    texto, n = reemplazador.reemplazar(celda.comment.text)
                    autor, m = reemplazador.reemplazar(celda.comment.author or "")
                    if n or m:
                        celda.comment = openpyxl.comments.Comment(texto, autor)
                        cambios += n + m
                v = celda.value
                if isinstance(v, str):
                    if re.search(r"\bR\.?U\.?[TN]\.?\b", sin_acentos(v).upper()):
                        columnas_rut.add(celda.column)
                    if re.fullmatch(r"\s*D\.?\s*V\.?\s*", v.upper()):
                        columnas_dv.add(celda.column)
                    nuevo, n = reemplazador.reemplazar(v)
                    if n:
                        celda.value = nuevo
                        cambios += n
                elif isinstance(v, int) and celda.column in columnas_rut and v in reemplazador.ruts:
                    # RUT guardado como número en una columna "RUT"
                    falso = reemplazador.ruts[v].rut_falso
                    celda.value = falso
                    cambios += 1
                    if celda.column + 1 in columnas_dv:
                        dv = hoja.cell(row=celda.row, column=celda.column + 1)
                        dv_falso = digito_verificador(falso)
                        dv.value = int(dv_falso) if isinstance(dv.value, int) and dv_falso.isdigit() else dv_falso
    libro.properties.creator = None
    libro.properties.lastModifiedBy = None
    libro.properties.title = None
    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)

    verificado = openpyxl.load_workbook(destino)
    textos, ruts_numericos = [], False
    for hoja in verificado.worksheets:
        textos.append(hoja.title)
        for fila in hoja.iter_rows():
            for celda in fila:
                if celda.value is not None:
                    textos.append(str(celda.value))
                    ruts_numericos |= isinstance(celda.value, int) and celda.value in reemplazador.ruts
                if celda.comment is not None:
                    textos.append(f"{celda.comment.text} {celda.comment.author or ''}")
    verificado.close()
    problemas, avisos = verificador.revisar("\n".join(textos))
    if ruts_numericos:
        problemas.append("queda un RUT real guardado como número")
    if problemas:
        destino.unlink()
    return cambios, problemas, avisos


def anonimizar_texto(origen, destino, reemplazador, verificador):
    contenido = origen.read_bytes()
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = contenido.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    nuevo, cambios = reemplazador.reemplazar(texto)
    problemas, avisos = verificador.revisar(nuevo)
    if not problemas:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(nuevo.encode(codificacion))
    return cambios, problemas, avisos


# --------------------------------------------------------------------------
# Detección inicial de clientes
# --------------------------------------------------------------------------

def parece_nombre(texto):
    tokens = [t for t in texto.replace(",", " ").split() if t]
    limpios = [limpiar_token(t) for t in tokens]
    limpios = [t for t in limpios if t and t not in ETIQUETAS]
    if not 2 <= len(limpios) <= 7:
        return None
    if not all(re.fullmatch(r"[A-Z.&'-]+", t) for t in limpios):
        return None
    return " ".join(t for t in tokens if limpiar_token(t) not in ETIQUETAS and limpiar_token(t))


class PdfConClave(Exception):
    pass


def textos_de(archivo, claves=()):
    """Líneas de texto de un archivo, para buscar RUT y nombres."""
    ext = archivo.suffix.lower()
    if ext in EXT_PDF:
        doc = abrir_pdf(archivo, claves)
        if doc is None:
            raise PdfConClave()
        lineas = [l for p in doc for l in p.get_text("text").splitlines()]
        doc.close()
        return lineas
    if ext in EXT_EXCEL:
        libro = openpyxl.load_workbook(archivo, read_only=True)
        lineas = []
        for hoja in libro.worksheets:
            for fila in hoja.iter_rows(values_only=True):
                lineas.append("  ".join(str(v) for v in fila if v is not None))
        libro.close()
        return lineas
    if ext in EXT_TEXTO:
        return archivo.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    return []


def detectar_clientes(archivos, raiz, claves_extra=()):
    encontrados = {}
    con_clave = []

    def revisar(archivo, claves):
        try:
            lineas = textos_de(archivo, claves)
        except PdfConClave:
            return False
        except Exception as e:
            print(f"  No pude leer {archivo.relative_to(raiz)}: {e}")
            return True
        partes = archivo.relative_to(raiz).parts
        carpeta = partes[1] if len(partes) > 2 else partes[0]
        for i, linea in enumerate(lineas):
            for m in RUT_RE.finditer(linea):
                cuerpo = cuerpo_rut(m.group(1))
                dv = m.group(3).upper()
                if digito_verificador(cuerpo) != dv:
                    continue  # no es un RUT válido (probablemente otro número)
                info = encontrados.setdefault(cuerpo, {"dv": dv, "nombres": {}, "veces": 0, "carpetas": set()})
                info["veces"] += 1
                info["carpetas"].add(carpeta)
                resto = (linea[:m.start()] + " " + linea[m.end():]).strip(" :-")
                candidatos = [resto] + [lineas[j] for j in (i - 1, i + 1) if 0 <= j < len(lineas)]
                for cand in candidatos:
                    nombre = parece_nombre(cand)
                    if nombre:
                        info["nombres"][nombre] = info["nombres"].get(nombre, 0) + 1
                        break
        return True

    for archivo in archivos:
        if not revisar(archivo, claves_extra):
            con_clave.append(archivo)
    # Los PDF con clave se reintentan con los RUT encontrados en los demás archivos.
    sin_abrir = [a for a in con_clave if not revisar(a, claves_posibles(encontrados, claves_extra))]
    if sin_abrir:
        print(f"  {len(sin_abrir)} PDF tienen una clave que no es ninguno de los RUT encontrados.")
        print(f"  Si sabes la clave, escríbela en {ARCHIVO_CLAVES} (una por línea) o agrega el RUT del cliente a {ARCHIVO_CLIENTES}.")

    filas = []
    for cuerpo, info in sorted(encontrados.items(), key=lambda kv: -kv[1]["veces"]):
        nombre = max(info["nombres"], key=info["nombres"].get) if info["nombres"] else ""
        institucion = any(limpiar_token(t) in PALABRAS_INSTITUCION for t in nombre.split())
        filas.append({
            "rut": f"{cuerpo:,}".replace(",", ".") + "-" + info["dv"],
            "nombre": nombre,
            "tipo": "persona" if cuerpo < 50_000_000 else "empresa",
            "anonimizar": "no" if institucion else "si",
            "veces": info["veces"],
            "carpetas": ", ".join(sorted(info["carpetas"])),
        })
    return filas


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------

def listar_archivos(raiz):
    archivos = []
    for nombre in CARPETAS_ENTRADA:
        carpeta = next((p for p in raiz.iterdir() if p.is_dir() and p.name.lower() == nombre.lower()), None)
        if carpeta is None:
            print(f"Aviso: no encontré la carpeta \"{nombre}\" en {raiz}")
            continue
        archivos.extend(sorted(p for p in carpeta.rglob("*") if p.is_file()))
    return archivos


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--carpeta", default=None,
                        help="carpeta que contiene Training Data y Example (por defecto, la de este script "
                             "o la carpeta actual)")
    parser.add_argument("--semilla", type=int, default=None, help="semilla para los datos falsos (pruebas)")
    args = parser.parse_args()

    if pymupdf is None or openpyxl is None:
        print("Faltan librerías. Instálalas con:\n    py -m pip install pymupdf openpyxl")
        return 1

    if args.carpeta:
        raiz = Path(args.carpeta).resolve()
    else:
        opciones = [Path(__file__).resolve().parent, Path.cwd()]
        raiz = next((c for c in opciones if any((c / n).is_dir() for n in CARPETAS_ENTRADA)), opciones[0])
    archivos = listar_archivos(raiz)
    if not archivos:
        print("No encontré archivos para anonimizar.")
        return 1

    ruta_clientes = raiz / ARCHIVO_CLIENTES
    if not ruta_clientes.exists():
        print(f"Buscando RUT en {len(archivos)} archivos...")
        filas = detectar_clientes(archivos, raiz, leer_claves_extra(raiz))
        escribir_csv(ruta_clientes, filas, ["rut", "nombre", "tipo", "anonimizar", "veces", "carpetas"])
        sin_nombre = sum(1 for f in filas if not f["nombre"])
        print(f"\nEncontré {len(filas)} RUT y los dejé en {ARCHIVO_CLIENTES}.")
        print("Ábrelo en Excel y revísalo antes de seguir:")
        print("  - Corrige el nombre de cada cliente tal como aparece en las cartolas (nombres y apellidos).")
        if sin_nombre:
            print(f"  - {sin_nombre} RUT no tienen nombre: complétalos si son clientes.")
        print("  - Revisa la columna \"anonimizar\": \"si\" para clientes, \"no\" para bancos, corredoras y emisores.")
        print("    Ya dejé \"no\" en los que parecen instituciones; confírmalo.")
        print("  - Puedes agregar filas con clientes que solo aparecen por nombre (sin RUT).")
        print("Después vuelve a correr este mismo comando.")
        return 0

    clientes = leer_clientes(ruta_clientes)
    if not clientes:
        print(f"{ARCHIVO_CLIENTES} no tiene clientes para anonimizar.")
        return 1
    rng = random.Random(args.semilla)
    ruta_mapeo = raiz / ARCHIVO_MAPEO
    asignar_falsos(clientes, leer_mapeo(ruta_mapeo), rng)
    guardar_mapeo(ruta_mapeo, clientes)
    reemplazador = Reemplazador(clientes)
    verificador = Verificador(clientes)
    claves = claves_posibles([c.rut for c in clientes if c.rut], leer_claves_extra(raiz))

    salida = raiz / CARPETA_SALIDA
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir()

    reporte, resumen = [], []
    copiados = fallidos = 0
    print(f"Anonimizando {len(archivos)} archivos de {len(clientes)} clientes...")
    for archivo in archivos:
        relativo = archivo.relative_to(raiz)
        partes = [reemplazador.reemplazar(p)[0] for p in relativo.parts]
        destino = salida.joinpath(*partes)
        ext = archivo.suffix.lower()
        try:
            if ext in EXT_PDF:
                cambios, problemas, avisos = anonimizar_pdf(archivo, destino, reemplazador, verificador, claves)
            elif ext in EXT_EXCEL:
                cambios, problemas, avisos = anonimizar_excel(archivo, destino, reemplazador, verificador)
            elif ext in EXT_TEXTO:
                cambios, problemas, avisos = anonimizar_texto(archivo, destino, reemplazador, verificador)
            else:
                cambios, problemas, avisos = 0, [f"tipo de archivo {ext or 'sin extensión'} no soportado"], []
        except Exception as e:
            cambios, problemas, avisos = 0, [f"error al procesar: {e}"], []
            if destino.exists():
                destino.unlink()

        destino_rel = Path(*partes)
        if problemas:
            fallidos += 1
            reporte.append(f"NO COPIADO  {relativo}: {'; '.join(problemas)}")
            resumen.append(f"NO COPIADO  {destino_rel}: {'; '.join(p.split(':')[0] for p in problemas)}")
        else:
            copiados += 1
            linea = f"OK          {relativo} ({cambios} reemplazos)"
            if avisos:
                linea += f"  revisar nombres sueltos: {', '.join(avisos)}"
            reporte.append(linea)
            resumen.append(f"OK          {destino_rel} ({cambios} reemplazos)" + ("  con avisos" if avisos else ""))

    encabezado = [
        f"Archivos revisados: {len(archivos)}",
        f"Copiados a {CARPETA_SALIDA}: {copiados}",
        f"No copiados (requieren revisión): {fallidos}",
        f"Clientes anonimizados: {len(clientes)}",
        "",
    ]
    (raiz / ARCHIVO_REPORTE).write_text("\n".join(encabezado + reporte) + "\n", encoding="utf-8")
    (salida / ARCHIVO_RESUMEN).write_text("\n".join(encabezado + resumen) + "\n", encoding="utf-8")

    print("\n".join(encabezado))
    if fallidos:
        print(f"Los archivos no copiados y el motivo están en {ARCHIVO_REPORTE}.")
    print(f"La carpeta {CARPETA_SALIDA} no tiene nombres ni RUT reales de los clientes de {ARCHIVO_CLIENTES}.")
    print(f"No compartas {ARCHIVO_CLIENTES}, {ARCHIVO_MAPEO} ni {ARCHIVO_REPORTE}: tienen datos reales.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
