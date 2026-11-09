
import html
import json
import re
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from PIL import Image, UnidentifiedImageError


# ============================================================
# CONFIGURACIÓN DE WIKIMEDIA COMMONS
# ============================================================

API = "https://commons.wikimedia.org/w/api.php"

MAX_BYTES = 5 * 1024 * 1024

SERVIDORES_PERMITIDOS = {
    "upload.wikimedia.org",
    "thumb.wikimedia.org",
}

FORMATOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

LICENCIAS_ADMITIDAS = {
    "cc0",
    "cc0-1.0",
    "cc-by-2.0",
    "cc-by-2.5",
    "cc-by-2.5-es",
    "cc-by-3.0",
    "cc-by-4.0",
    "cc-by-sa-2.0",
    "cc-by-sa-2.5",
    "cc-by-sa-2.5-es",
    "cc-by-sa-3.0",
    "cc-by-sa-4.0",
    "pd",
    "public-domain",
    "public domain",
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def texto_plano(valor):
    """
    Elimina etiquetas HTML de los metadatos de Wikimedia.
    """
    valor = re.sub(r"<[^>]*>", " ", str(valor or ""))
    return html.unescape(valor).strip()


def valor_metadata(metadata, nombre):
    """
    Obtiene un valor de los metadatos de una fotografía.
    """
    return metadata.get(nombre, {}).get("value", "")


def normalizar_licencia(valor):
    """
    Normaliza los nombres de licencias.
    """
    return (
        texto_plano(valor)
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )


def licencia_permitida(licencia, codigo):
    """
    Comprueba que la licencia esté entre las admitidas.
    No admite variantes NC o ND.
    """
    valores = {
        normalizar_licencia(licencia),
        normalizar_licencia(codigo),
    }

    for valor in valores:
        if not valor:
            continue

        if valor in LICENCIAS_ADMITIDAS:
            return True

        if valor.startswith("cc-by-") or valor.startswith("cc-by-sa-"):
            partes = valor.split("-")

            if "nc" in partes or "nd" in partes:
                continue

            # Aceptar variantes regionales de licencias BY/BY-SA.
            if re.fullmatch(
                r"cc-by(?:-sa)?-\d+(?:\.\d+)?(?:-[a-z]{2,3})?",
                valor,
            ):
                return True

        if valor.startswith("cc0-"):
            return True

    return False


def validar_url_imagen(url):
    """
    Acepta únicamente HTTPS en servidores autorizados.
    """
    if not url:
        raise ValidationError(
            "La fotografía no tiene una URL disponible."
        )

    partes = urlparse(url)

    if (
        partes.scheme != "https"
        or partes.hostname not in SERVIDORES_PERMITIDOS
        or partes.username is not None
        or partes.password is not None
        or partes.port not in (None, 443)
    ):
        raise ValidationError(
            "El servidor de fotografías no es válido."
        )

    return url


def crear_solicitud(url, acepta_json=False):
    """
    Crea una solicitud identificada para Wikimedia Commons.
    """
    encabezados = {
        "User-Agent": (
            "EstropicalAcademico/1.0 "
            "(proyecto educativo; integracion Wikimedia Commons)"
        ),
    }

    if acepta_json:
        encabezados["Accept"] = "application/json"

    return Request(url, headers=encabezados)


# ============================================================
# CONSULTA DE LA API
# ============================================================

def consultar_api(parametros):
    """
    Consulta la API pública de Wikimedia Commons.
    No requiere clave API.
    """
    parametros = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        **parametros,
    }

    url = API + "?" + urlencode(parametros)

    solicitud = crear_solicitud(
        url,
        acepta_json=True,
    )

    try:
        with urlopen(solicitud, timeout=15) as respuesta:
            datos = json.load(respuesta)

    except (
        HTTPError,
        URLError,
        TimeoutError,
        ValueError,
    ) as exc:
        raise ValidationError(
            "No se pudo consultar Wikimedia Commons. "
            "Comprueba la conexión a internet."
        ) from exc

    if "error" in datos:
        raise ValidationError(
            "Wikimedia Commons rechazó la consulta."
        )

    return datos


# ============================================================
# PROCESAMIENTO DE FOTOGRAFÍAS
# ============================================================

def procesar_pagina(pagina):
    """
    Convierte una respuesta de Wikimedia en una fotografía
    utilizable por Estropical.
    """
    imagenes = pagina.get("imageinfo") or []

    if not imagenes:
        return None

    info = imagenes[0]
    metadata = info.get("extmetadata") or {}

    licencia = normalizar_licencia(
        valor_metadata(metadata, "LicenseShortName")
    )

    licencia_codigo = normalizar_licencia(
        valor_metadata(metadata, "License")
    )

    if not licencia_permitida(
        licencia,
        licencia_codigo,
    ):
        return None

    tipo = info.get("mime")

    if tipo not in FORMATOS_PERMITIDOS:
        return None

    titulo = pagina.get("title", "")

    if not titulo.startswith("File:"):
        return None

    miniatura = info.get("thumburl") or info.get("url")
    url_original = info.get("url")

    if not miniatura or not url_original:
        return None

    try:
        validar_url_imagen(miniatura)
        validar_url_imagen(url_original)
    except ValidationError:
        return None

    autor = texto_plano(
        valor_metadata(metadata, "Artist")
    )

    if not autor:
        autor = "Autor indicado en Wikimedia Commons"

    return {
        "titulo": titulo,
        "miniatura": miniatura,
        "url": url_original,
        "pagina": info.get("descriptionurl", ""),
        "licencia": licencia or licencia_codigo,
        "licencia_url": valor_metadata(
            metadata,
            "LicenseUrl",
        ),
        "autor": autor[:120],
    }


# ============================================================
# BUSCAR FOTOGRAFÍAS
# ============================================================

def buscar_fotografias(destino, pais="", limite=9):
    """
    Busca fotografías según el nombre del destino y país.
    """
    consulta = f"{destino} {pais}".strip()

    if not consulta:
        return []

    limite = max(1, min(int(limite), 20))

    datos = consultar_api({
        "generator": "search",
        "gsrsearch": consulta,
        "gsrnamespace": 6,
        "gsrlimit": min(limite * 3, 40),
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 700,
    })

    paginas = datos.get(
        "query", {}
    ).get("pages", [])

    resultados = []

    for pagina in paginas:
        foto = procesar_pagina(pagina)

        if foto:
            resultados.append(foto)

        if len(resultados) >= limite:
            break

    return resultados


# ============================================================
# OBTENER UNA FOTOGRAFÍA ESPECÍFICA
# ============================================================

def obtener_fotografia(titulo):
    """
    Consulta nuevamente una fotografía seleccionada.
    No confía únicamente en los datos del formulario.
    """
    if (
        not isinstance(titulo, str)
        or not titulo.startswith("File:")
        or len(titulo) > 255
    ):
        raise ValidationError(
            "La fotografía seleccionada no es válida."
        )

    datos = consultar_api({
        "titles": titulo,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 1200,
    })

    paginas = datos.get(
        "query", {}
    ).get("pages", [])

    if not paginas:
        raise ValidationError(
            "No se encontró la fotografía."
        )

    foto = procesar_pagina(paginas[0])

    if not foto:
        raise ValidationError(
            "La fotografía no tiene una licencia admitida "
            "o su formato no es compatible."
        )

    return foto


# ============================================================
# DESCARGAR FOTOGRAFÍA
# ============================================================

def descargar_fotografia(foto):
    """
    Descarga una fotografía de Wikimedia Commons.

    Se permite:
    - upload.wikimedia.org
    - thumb.wikimedia.org

    Comprueba:
    - HTTPS
    - servidor autorizado
    - tamaño máximo
    - contenido real de imagen
    - formato JPG, PNG o WebP
    """
    url = foto.get("miniatura")

    validar_url_imagen(url)

    solicitud = crear_solicitud(url)

    try:
        with urlopen(solicitud, timeout=25) as respuesta:

            # Comprobar también la URL final.
            validar_url_imagen(respuesta.geturl())

            contenido = respuesta.read(MAX_BYTES + 1)

            if len(contenido) > MAX_BYTES:
                raise ValidationError(
                    "La fotografía supera los 5 MB."
                )

    except (
        HTTPError,
        URLError,
        TimeoutError,
    ) as exc:
        raise ValidationError(
            "No se pudo descargar la fotografía "
            "desde Wikimedia Commons."
        ) from exc

    # Validar el contenido real con Pillow.
    try:
        with Image.open(BytesIO(contenido)) as imagen:
            imagen.verify()

        with Image.open(BytesIO(contenido)) as imagen:
            tipo = Image.MIME.get(imagen.format)

            if tipo not in FORMATOS_PERMITIDOS:
                raise ValidationError(
                    "El formato de imagen no está permitido."
                )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise ValidationError(
            "El archivo descargado no es una imagen válida."
        ) from exc

    extension = FORMATOS_PERMITIDOS[tipo]

    titulo = foto.get("titulo", "fotografia")

    nombre_limpio = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        titulo[:65],
    )

    nombre = (
        f"wikimedia_{nombre_limpio}{extension}"
    )

    return nombre, ContentFile(contenido)


# ============================================================
# GUARDAR FOTOGRAFÍA COMO PORTADA
# ============================================================

def guardar_portada(destino, foto, reemplazar=False):
    """
    Guarda una fotografía en DestinoFoto.

    Si reemplazar=False:
        conserva la portada existente.

    Si reemplazar=True:
        establece la nueva fotografía como portada.

    No elimina las fotografías anteriores.
    """
    from .models import Destino, DestinoFoto

    if destino.portada and not reemplazar:
        return destino.portada

    nombre, archivo = descargar_fotografia(foto)

    descripcion = (
        f"Wikimedia Commons | "
        f"{foto.get('autor', '')} | "
        f"{foto.get('licencia', '')} | "
        f"{foto.get('titulo', '')}"
    )[:200]

    nueva = DestinoFoto(
        destino=destino,
        descripcion=descripcion,
        orden=0,
        es_portada=False,
    )

    # El archivo se guarda en media/destinos/.
    nueva.archivo.save(
        nombre,
        archivo,
        save=False,
    )

    try:
        with transaction.atomic():

            # Bloquear el destino durante el cambio de portada.
            Destino.objects.select_for_update().get(
                pk=destino.pk
            )

            # Revisar de nuevo la portada dentro del bloqueo.
            if not reemplazar:
                existente = destino.portada

                if existente:
                    nueva.archivo.delete(save=False)
                    return existente

            # Desmarcar la portada anterior.
            DestinoFoto.objects.filter(
                destino=destino,
                es_portada=True,
            ).update(es_portada=False)

            # Guardar la nueva portada.
            nueva.es_portada = True
            nueva.save()

    except Exception:
        nueva.archivo.delete(save=False)
        raise

    return nueva
