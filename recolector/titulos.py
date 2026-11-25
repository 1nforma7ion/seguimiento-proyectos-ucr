"""Arma un título corto y legible a partir del extracto oficial de un proyecto.

El portal no publica un nombre para cada proyecto: solo el extracto, redactado siempre como
continuación de una frase ("Derogando el Decreto…", "Expresando beneplácito por…"). Estas reglas
convierten el verbo inicial en un sustantivo ("Derogación del Decreto…") y cortan en la primera
idea, para que el título se lea como el nombre del proyecto. El extracto completo se sigue mostrando
debajo como descripción oficial.
"""
import re

LARGO_MAX = 110
COMA_PROTEGIDA = "‚"  # coma "baja" que reemplaza a las comas entre comillas mientras se corta

# --- encabezados y frases que no forman parte del tema ---------------------------------------
RE_NOTA = re.compile(r"^nota\s+((remitida|presentada|elevada)\s+)?(por|de)\s+(el|la|los|las)\s+.+?(,\s*|\s+)(?=[a-záéíóúñ]+(ando|endo|iendo)\b)", re.I)
RE_ARTICULO_CP = re.compile(r"\s*\((arts?\.?|artículos?)\s*[^)]*\)", re.I)
RE_GERUNDIO = re.compile(r",\s+([a-záéíóúñ]+(?:ando|endo|iendo))\b")
RE_ASPECTOS = re.compile(
    r"\b(sobre|acerca de)\s+(diversos\s+|distintos\s+|varios\s+|algunos\s+)?(aspectos|puntos|temas)\s+"
    r"(referidos|relacionados|vinculados|relativos)\s+"
    r"(a la|a los|a las|al|a|con el|con la|con los|con las|con)\s+", re.I)
ARTICULO = {"al": "el ", "a la": "la ", "a los": "los ", "a las": "las ", "a": "", "con el": "el ",
            "con la": "la ", "con los": "los ", "con las": "las ", "con": "", "la": "la ", "el": "el ",
            "los": "los ", "las": "las "}
RE_PROPOSITO = re.compile(r"\s+(con el (objeto|objetivo|fin|propósito) de|a fin de|a los efectos de|en el marco de|"
                          r"conforme (al|el|a lo|lo)\b|a (conmemorarse|celebrarse|desarrollarse|realizarse|llevarse a cabo)\b).*$", re.I)

# --- verbos ------------------------------------------------------------------------------------
# Se reemplazan por un sustantivo: "derogando el X" → "Derogación del X".
NOMINAL = {
    "derogando": "Derogación de", "modificando": "Modificación de", "incorporando": "Incorporación de",
    "regulando": "Regulación de", "prohibiendo": "Prohibición de", "autorizando": "Autorización de",
    "eliminando": "Eliminación de", "suspendiendo": "Suspensión de", "garantizando": "Garantía de",
    "promoviendo": "Promoción de", "otorgando": "Otorgamiento de", "eximiendo": "Exención de",
    "fijando": "Fijación de", "aprobando": "Aprobación de", "ratificando": "Ratificación de",
    "reglamentando": "Reglamentación de", "sustituyendo": "Sustitución de", "ampliando": "Ampliación de",
    "prorrogando": "Prórroga de", "transfiriendo": "Transferencia de", "declarando": "Declaración de",
    "convocando": "Convocatoria a", "designando": "Designación de", "nombrando": "Designación de",
    "denominando": "Denominación de", "ordenando": "Orden de", "aceptando": "Aceptación de",
    "desafectando": "Desafectación de", "afectando": "Afectación de", "facultando": "Autorización a",
    "habilitando": "Habilitación de", "restituyendo": "Restitución de", "reconociendo": "Reconocimiento a",
    "destacando": "Reconocimiento a", "repudiando": "Repudio a", "rechazando": "Rechazo a",
    "adhiriendo": "Adhesión a", "citando": "Citación a", "instruyendo": "Instrucción a",
    "convalidando": "Convalidación de", "condenando": "Condena a", "felicitando": "Felicitaciones a",
    "saludando": "Saludo a", "acompañando": "Acompañamiento a", "celebrando": "Celebración de",
    "conmemorando": "Conmemoración de", "lamentando": "Pesar por", "homenajeando": "Homenaje a",
}
# Su objeto ya es el nombre del proyecto: "Creando el Régimen de X" → "Régimen de X".
SIN_VERBO = {"creando", "instituyendo", "estableciendo", "implementando", "disponiendo", "instaurando"}
# Pedidos a otros poderes u organismos.
PEDIDO = {"solicitando", "instando", "requiriendo", "exhortando", "reiterando", "pidiendo", "urgiendo"}
OTROS = {"expresando", "expesando", "manifestando", "rindiendo", "dejando"}
CONOCIDOS = set(NOMINAL) | SIN_VERBO | PEDIDO | OTROS

# "Expresando beneplácito por X" → "Beneplácito por X".
RE_EXPRESA = re.compile(
    r"^(exp?r?esando|manifestando|declarando|ratificando)\s+(su\s+|el\s+|la\s+|un\s+|una\s+)?"
    r"(más\s+)?(enérgico\s+|profundo\s+|total\s+|firme\s+|absoluto\s+)?"
    r"(beneplácito|beneplacito|adhesión|reconocimiento|preocupación|repudio|rechazo|solidaridad|pesar|"
    r"satisfacción|apoyo|agrado|homenaje|acompañamiento|condolencias|felicitaciones|felicitación|"
    r"congratulación|desagravio)\b", re.I)
RE_HOMENAJE = re.compile(r"^rindiendo\s+(un\s+)?(sentido\s+)?homenaje\b", re.I)
RE_SIN_EFECTO = re.compile(r"^dejando\s+(parcialmente\s+)?sin\s+efecto\b", re.I)
# "Declarando de interés legislativo la Semana X" → "Declaración de interés legislativo de la Semana X".
RE_DECLARA_INTERES = re.compile(r"^declarando\s+(de\s+inter[ée]s\s+[\wáéíóúñ ]{0,40}?)\s+(a la|a los|a las|al|el|la|los|las)\s+", re.I)
RE_INFORME = re.compile(r"\binform(e|es|en|ar|ación)\b", re.I)
RE_SOBRE = re.compile(r"\b(sobre|acerca\s+de|respecto\s+(de|a|al)|referid[oa]s?\s+(a|al)|relacionad[oa]s?\s+con|"
                      r"en\s+relación\s+(a|al|con)|vinculad[oa]s?\s+(a|al|con))\s+", re.I)
# Quien recibe un pedido: palabras con mayúscula ("Poder Ejecutivo", "Ministerio de Salud").
RE_DESTINO = re.compile(
    r"^(al|a la|a los|a las|a)\s+((?:Sres?\.?\s+|Sras?\.?\s+)?[A-ZÁÉÍÓÚÑ][\wáéíóúñ.]*"
    r"(?:\s+(?:(?:de|del|de la|de los|y|e)\s+)?[A-ZÁÉÍÓÚÑ][\wáéíóúñ.]*)*"
    r"(?:\s+(?:provincial|nacional|municipal)(?:es)?\b)?)\s*,?\s*")
RE_COMILLAS = re.compile(r"[\"“«]([^\"”»]{6,90})[\"”»]")


def _mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:] if texto else texto


def _contraer(texto: str) -> str:
    return re.sub(r"\bde el\b", "del", re.sub(r"\ba el\b", "al", texto))


def _sin_gritos(texto: str) -> str:
    """Pasa a minúsculas los extractos escritos todo en mayúsculas."""
    letras = [c for c in texto if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) > 0.6:
        texto = texto.lower()
        for mal, bien in ((r"\bc[óo]rdoba\b", "Córdoba"), (r"\bley\b", "Ley"), (r"\bnacional\b", "Nacional"), (r"\bn°", "N°")):
            texto = re.sub(mal, bien, texto)
    return texto


def _limpiar(tema: str) -> str:
    t = _sin_gritos(" ".join((tema or "").split()))
    t = RE_NOTA.sub("", t)
    t = RE_ARTICULO_CP.sub("", t)
    t = RE_ASPECTOS.sub(lambda m: m.group(1) + " " + ARTICULO[m.group(5).lower()], t)
    primera = t.split(" ", 1)[0].lower().strip(",.") if t else ""
    if primera not in CONOCIDOS:
        # El encabezado de autores no se pudo separar: el tema empieza en el primer verbo conocido.
        for g in RE_GERUNDIO.finditer(t[:400]):
            if g.group(1).lower() in CONOCIDOS:
                return _mayuscula(t[g.start(1):])
    return _mayuscula(t)


# Palabras con las que empieza una aclaración (y no la continuación de una lista de sustantivos).
NO_ENUMERA = {"que", "a", "al", "en", "de", "del", "para", "por", "con", "el", "la", "los", "las", "un", "una",
              "conforme", "cuyo", "cuya", "sin", "desde", "hasta", "entre", "según", "como", "donde", "quien",
              "y", "e", "o", "su", "sus", "este", "esta", "dicho", "dicha", "mediante", "ante", "sobre", "tras"}


def _sigue_enumeracion(parte: str) -> bool:
    """"La prevención, seguridad, rescate y salvamento": la coma separa sustantivos de una misma lista."""
    palabra = parte.split(" ", 1)[0]
    p = palabra.lower()
    # Solo sustantivos comunes: una palabra con mayúscula ("Dpto.", un nombre propio) es una aclaración.
    return bool(p) and palabra[0].islower() and p not in NO_ENUMERA \
        and not re.search(r"(ando|endo|iendo|ado|ada|ido|ida|ados|adas|idos|idas)$", p)


def _cortar(texto: str) -> str:
    """Corta en la primera idea: hasta la primera coma o punto y coma, salvo que lo que sigue
    explique una ley o un decreto citado por número ("Ley N° 27043, que declara…")."""
    texto = re.sub(r"[\"“«][^\"”»]*[\"”»]", lambda m: m.group(0).replace(",", COMA_PROTEGIDA), texto)
    partes = re.split(r"\s*[;,]\s+(?!\d)|\.\s+(?=[a-záéíóúñ])", texto)
    titulo, i = partes[0], 1
    while i < len(partes) and (
            len(titulo) < 20
            or (re.search(r"(N[°º]|Nro\.?|N\.)\s*[\d./]+$|\d$", titulo) and re.match(r"(que|de|sobre|por)\b", partes[i], re.I))
            or (len(titulo) < 70 and _sigue_enumeracion(partes[i]))
            # "Sistema de Prevención, Detección Temprana y Gestión de…": un nombre propio con comas.
            or (len(titulo) < 60 and partes[i][:1].isupper() and " y " in partes[i] and not partes[i].startswith("Dpto"))):
        titulo += ", " + partes[i]
        i += 1
    titulo = re.sub(r"\s+y\s+(toda|todo|cualquier)\s+otra?\b.*$", "", titulo, flags=re.I)
    corto = RE_PROPOSITO.sub("", titulo)
    if len(corto) >= 30:
        titulo = corto
    titulo = titulo.replace(COMA_PROTEGIDA, ",").strip(" .:-")
    if len(titulo) > LARGO_MAX:
        titulo = titulo[:LARGO_MAX].rsplit(" ", 1)[0].rstrip(" ,;.:(") + "…"
    return titulo


def _pedido(t: str, resto: str) -> str:
    if RE_INFORME.search(t[:120]):
        sobre = RE_SOBRE.search(t)
        if sobre and sobre.start() < 160:
            return f"Pedido de informes sobre {t[sobre.end():]}"
        # "…informe (Art. 102) detalladamente la cantidad de…" → "Pedido de informes sobre la cantidad de…"
        inf = RE_INFORME.search(t)
        objeto = re.sub(r"^(\s*,?\s*(detalladamente|al cuerpo|a esta legislatura|de manera oficial|a la brevedad|en detalle)\s*,?)+",
                        "", t[inf.end():], flags=re.I).strip(" ,")
        if re.match(r"(el|la|los|las|lo)\b", objeto, re.I):
            return f"Pedido de informes sobre {objeto}"
        return f"Pedido de informes: {objeto}" if objeto else "Pedido de informes"
    if d := RE_DESTINO.match(resto):
        a_quien, pedido = f"{d.group(1)} {d.group(2)}", resto[d.end():]
        if m := re.match(r"(el|la|los|las|un|una)\s+", pedido, re.I):
            return f"Pedido {a_quien}: {pedido[m.end():]}"
        if m := re.match(r"a\s+(?=[a-záéíóúñ]+(ar|er|ir)\b)", pedido):
            return f"Pedido {a_quien}: {pedido[m.end():]}"
        if re.match(r"(que|para que|a fin de|a que)\b", pedido, re.I):
            return f"Pedido {a_quien} {pedido}"
        return f"Pedido {a_quien} que {pedido}"
    if m := re.match(r"a\s+(?=[a-záéíóúñ]+(ar|er|ir)\b)", resto):       # "instando a excluir…"
        return "Pedido para " + resto[m.end():]
    if m := re.match(r"(el|la|los|las|al)\s+", resto, re.I):           # "solicitando la rehabilitación…"
        return "Pedido de " + resto[m.end():]
    if re.match(r"(a la|a los|a las|a)\s+", resto, re.I):              # "instando a las autoridades…"
        return "Pedido " + resto
    return "Pedido de " + resto


def titulo_de(tema: str, extracto: str | None = None) -> str:
    """Título corto para mostrar. `tema` es el extracto sin el encabezado de autores.

    Si el tema quedó mal separado del encabezado (empieza en "Que…" o "Siendo…"), se arma a partir
    del extracto completo.
    """
    if extracto and re.match(r"(que|siendo|informando|y|e|el cual|la cual)\b", tema or "", re.I):
        return titulo_de(extracto)
    t = _limpiar(tema)
    if not t:
        return tema
    verbo = t.split(" ", 1)[0]
    primera, resto = verbo.lower().strip(",."), t[len(verbo):].lstrip()

    if m := RE_DECLARA_INTERES.match(t):
        titulo = "Declaración " + m.group(1).strip().lower() + " de " + ARTICULO[m.group(2).lower()] + t[m.end():]
    elif m := RE_EXPRESA.match(t):
        titulo = m.group(5).lower().replace("beneplacito", "beneplácito").capitalize() + " " + t[m.end():].lstrip()
    elif m := RE_HOMENAJE.match(t):
        titulo = "Homenaje " + t[m.end():].lstrip()
    elif m := RE_SIN_EFECTO.match(t):
        titulo = ("Derogación parcial de " if m.group(1) else "Derogación de ") + t[m.end():].lstrip()
    elif primera in PEDIDO:
        titulo = _pedido(t, resto)
    elif primera in SIN_VERBO:
        if re.match(r"que\b", resto, re.I):          # "Estableciendo que la tasa…" → "Dispone que la tasa…"
            return _mayuscula(_cortar(_contraer("Dispone " + resto)))
        objeto = re.sub(r"^(el|la|los|las|un|una)\s+", "", resto, flags=re.I)
        comillas = RE_COMILLAS.search(objeto[:140])
        titulo = comillas.group(1).strip() if primera == "instituyendo" and comillas else objeto
    elif primera in NOMINAL:
        nombre = NOMINAL[primera]
        if primera == "adhiriendo":                     # "Adhiriendo la Provincia de Córdoba a la Ley…"
            resto = re.sub(r"^la provincia( de córdoba)?\s+", "", resto, flags=re.I)
        if nombre.endswith(" a") and re.match(r"(a|al)\b", resto, re.I):   # "Adhesión a" + "a la Fiesta…"
            nombre = nombre[:-2]
        titulo = nombre + " " + resto
    else:
        titulo = t
    return _mayuscula(_cortar(_contraer(_mayuscula(titulo.strip()))))
