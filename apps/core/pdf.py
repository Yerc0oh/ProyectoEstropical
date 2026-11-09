"""Generador de PDF mínimo, sin librerías externas (Sprint 3 y 4).

Se usa para itinerarios (CU-25), comprobantes de pago (CU-26/28) y facturas (CU-30/31).
Escribe PDF 1.4 con las fuentes estándar Helvetica / Helvetica-Bold (codificación
WinAnsi = cp1252, por eso admite tildes, ñ, ¿ y ¡). Tamaño de página A4.

Uso:
    pdf = DocumentoPDF("Itinerario ET-AB12CD34")
    pdf.titulo("Itinerario de viaje")
    pdf.par("Cliente", "Ana López")
    pdf.tabla(["Día", "Actividad"], [["1", "City tour"]], [60, 400])
    return pdf.respuesta("itinerario.pdf")
"""
from datetime import datetime

ANCHO, ALTO = 595.28, 841.89      # A4 en puntos
MARGEN = 50
AZUL = (0.043, 0.325, 0.580)      # #0b5394, color de la marca
REEMPLAZOS = {"→": "->", "←": "<-", "✓": "Si", "✗": "No", "…": "...", "≥": ">=", "≤": "<="}

# Anchos de Helvetica (AFM, en milésimas de punto) para ajustar el texto al ancho de línea.
_W = {" ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191, "(": 333,
      ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278, ":": 278, ";": 278,
      "<": 584, "=": 584, ">": 584, "?": 556, "@": 1015, "I": 278, "J": 500, "M": 833, "W": 944,
      "f": 278, "i": 222, "j": 222, "l": 222, "m": 833, "r": 333, "t": 278, "w": 722, "|": 260}


def _ancho_caracter(c, negrita):
    if c in _W:
        w = _W[c]
    elif c.isupper():
        w = 722 if c not in "EFLPSTZ" else 611
    elif c.isdigit():
        w = 556
    else:
        w = 556 if c not in "ckszvxy" else 500
    return w * (1.05 if negrita else 1.0)


def ancho_texto(texto, tam, negrita=False):
    return sum(_ancho_caracter(c, negrita) for c in texto) * tam / 1000


def _limpiar(texto):
    texto = "" if texto is None else str(texto)
    for a, b in REEMPLAZOS.items():
        texto = texto.replace(a, b)
    return texto.replace("\r", "").replace("\t", "    ")


def _codificar(texto):
    datos = texto.encode("cp1252", errors="replace")
    return datos.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


class DocumentoPDF:
    def __init__(self, titulo_documento="", encabezado="Estropical · Tropical Tours Ltda."):
        self.titulo_documento = _limpiar(titulo_documento)
        self.encabezado = _limpiar(encabezado)
        self.paginas = []
        self.marca = None
        self._nueva_pagina()

    # ------------------------------------------------------------ bajo nivel
    def _op(self, linea):
        self.ops.append(linea if isinstance(linea, bytes) else linea.encode("latin-1"))

    def _texto_en(self, x, y, texto, tam=10, negrita=False, color=(0, 0, 0)):
        fuente = "F2" if negrita else "F1"
        r, g, b = color
        self._op(f"BT {r:.3f} {g:.3f} {b:.3f} rg /{fuente} {tam} Tf {x:.2f} {y:.2f} Td (")
        self.ops[-1] += _codificar(texto) + b") Tj ET"

    def _nueva_pagina(self):
        self.ops = []
        self.paginas.append(self.ops)
        # banda superior con el nombre de la agencia
        r, g, b = AZUL
        self._op(f"{r:.3f} {g:.3f} {b:.3f} rg 0 {ALTO - 40:.2f} {ANCHO:.2f} 40 re f")
        self._texto_en(MARGEN, ALTO - 26, self.encabezado, 12, True, (1, 1, 1))
        self.y = ALTO - 40 - 30

    def _asegurar(self, alto):
        if self.y - alto < MARGEN + 20:
            self._nueva_pagina()

    def _partir(self, texto, tam, negrita, ancho_max):
        lineas = []
        for parrafo in _limpiar(texto).split("\n"):
            actual = ""
            for palabra in parrafo.split(" "):
                prueba = f"{actual} {palabra}" if actual else palabra
                if ancho_texto(prueba, tam, negrita) <= ancho_max:
                    actual = prueba
                    continue
                if actual:
                    lineas.append(actual)
                # palabra más larga que la línea: se corta
                while ancho_texto(palabra, tam, negrita) > ancho_max and len(palabra) > 1:
                    corte = len(palabra)
                    while corte > 1 and ancho_texto(palabra[:corte], tam, negrita) > ancho_max:
                        corte -= 1
                    lineas.append(palabra[:corte])
                    palabra = palabra[corte:]
                actual = palabra
            lineas.append(actual)
        return lineas

    def _recortar(self, texto, tam, negrita, ancho_max):
        texto = _limpiar(texto).replace("\n", " ")
        if ancho_texto(texto, tam, negrita) <= ancho_max:
            return texto
        while texto and ancho_texto(texto + "...", tam, negrita) > ancho_max:
            texto = texto[:-1]
        return texto + "..."

    # ------------------------------------------------------------ alto nivel
    def titulo(self, texto, tam=18):
        self.texto(texto, tam, negrita=True, color=AZUL)
        self.espacio(4)

    def subtitulo(self, texto):
        self.espacio(6)
        self.texto(texto, 12, negrita=True, color=AZUL)
        self.linea()

    def texto(self, texto, tam=10, negrita=False, sangria=0, color=(0, 0, 0)):
        ancho_max = ANCHO - 2 * MARGEN - sangria
        for linea in self._partir(texto, tam, negrita, ancho_max):
            self._asegurar(tam * 1.4)
            self._texto_en(MARGEN + sangria, self.y - tam, linea, tam, negrita, color)
            self.y -= tam * 1.4

    def par(self, etiqueta, valor, tam=10, ancho_etiqueta=140):
        """Línea 'Etiqueta: valor' (el valor se ajusta a varias líneas si es largo)."""
        lineas = self._partir(str(valor if valor not in (None, "") else "-"), tam, False,
                              ANCHO - 2 * MARGEN - ancho_etiqueta)
        self._asegurar(tam * 1.4)
        self._texto_en(MARGEN, self.y - tam, f"{etiqueta}:", tam, True)
        for linea in lineas:
            self._asegurar(tam * 1.4)
            self._texto_en(MARGEN + ancho_etiqueta, self.y - tam, linea, tam)
            self.y -= tam * 1.4

    def tabla(self, encabezados, filas, anchos, tam=9, alinear_derecha=()):
        """Tabla simple. `anchos` en puntos (deben sumar <= 495). `alinear_derecha` = índices."""
        def dibujar_fila(celdas, negrita):
            self._asegurar(tam * 1.8)
            x = MARGEN
            for i, (celda, ancho) in enumerate(zip(celdas, anchos)):
                txt = self._recortar(celda, tam, negrita, ancho - 6)
                dx = ancho - 4 - ancho_texto(txt, tam, negrita) if i in alinear_derecha else 2
                self._texto_en(x + dx, self.y - tam, txt, tam, negrita)
                x += ancho
            self.y -= tam * 1.6

        if encabezados:
            self._asegurar(tam * 4)
            dibujar_fila(encabezados, True)
            self.linea(grosor=0.5)
        for fila in filas:
            dibujar_fila(fila, False)
        self.espacio(4)

    def linea(self, grosor=0.8):
        self._asegurar(6)
        self.y -= 2
        self._op(f"{grosor} w 0.6 0.6 0.6 RG {MARGEN} {self.y:.2f} m {ANCHO - MARGEN:.2f} {self.y:.2f} l S")
        self.y -= 6

    def espacio(self, puntos=8):
        self.y -= puntos

    def marca_de_agua(self, texto):
        """Texto grande en diagonal en todas las páginas (p. ej. 'ANULADA')."""
        self.marca = _limpiar(texto)

    # ------------------------------------------------------------ salida
    def bytes(self):
        objetos = []   # cuerpos de los objetos, el número de objeto es índice + 1

        def agregar(cuerpo):
            objetos.append(cuerpo)
            return len(objetos)

        catalogo = agregar(None)
        paginas_id = agregar(None)
        f1 = agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        f2 = agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        hijos = []
        total = len(self.paginas)
        generado = datetime.now().strftime("%d/%m/%Y %H:%M")
        for n, ops in enumerate(self.paginas, start=1):
            fondo, extra = [], []
            if self.marca:   # va primero para quedar detrás del contenido
                fondo.append(b"BT 0.97 0.80 0.80 rg /F2 90 Tf 0.707 0.707 -0.707 0.707 150 260 Tm ("
                             + _codificar(self.marca) + b") Tj ET")
            pie = f"{self.titulo_documento}  ·  Generado el {generado}  ·  Página {n} de {total}"
            extra.append(b"BT 0.4 0.4 0.4 rg /F1 8 Tf " + f"{MARGEN} 30 Td (".encode("latin-1")
                         + _codificar(pie) + b") Tj ET")
            contenido = b"\n".join(fondo + ops + extra)
            cont_id = agregar(b"<< /Length " + str(len(contenido)).encode() + b" >>\nstream\n"
                              + contenido + b"\nendstream")
            hijos.append(agregar(
                f"<< /Type /Page /Parent {paginas_id} 0 R /MediaBox [0 0 {ANCHO} {ALTO}] "
                f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >> /Contents {cont_id} 0 R >>"
                .encode()))
        objetos[catalogo - 1] = f"<< /Type /Catalog /Pages {paginas_id} 0 R >>".encode()
        objetos[paginas_id - 1] = (f"<< /Type /Pages /Count {len(hijos)} /Kids ["
                                   + " ".join(f"{h} 0 R" for h in hijos) + "] >>").encode()
        titulo_info = self.titulo_documento.encode("latin-1", errors="replace").decode("latin-1")
        info = agregar(b"<< /Title (" + _codificar(titulo_info) + b") /Producer (Estropical) >>")

        salida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        posiciones = []
        for i, cuerpo in enumerate(objetos, start=1):
            posiciones.append(len(salida))
            salida += f"{i} 0 obj\n".encode() + cuerpo + b"\nendobj\n"
        inicio_xref = len(salida)
        salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
        for p in posiciones:
            salida += f"{p:010d} 00000 n \n".encode()
        salida += (f"trailer\n<< /Size {len(objetos) + 1} /Root {catalogo} 0 R /Info {info} 0 R >>\n"
                   f"startxref\n{inicio_xref}\n%%EOF\n").encode()
        return bytes(salida)

    def respuesta(self, nombre_archivo, descargar=True):
        """HttpResponse listo para devolver desde una vista."""
        from django.http import HttpResponse
        r = HttpResponse(self.bytes(), content_type="application/pdf")
        modo = "attachment" if descargar else "inline"
        r["Content-Disposition"] = f'{modo}; filename="{nombre_archivo}"'
        return r
