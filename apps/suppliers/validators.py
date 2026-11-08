"""Validación de archivos de documentos de proveedores (CU-13).

La extensión y el ``content_type`` enviados por el navegador no son confiables.
Aquí se comprueba además la firma real del archivo (magic bytes) y se limita el
tamaño. Los nombres originales nunca se usan para construir la ruta final.
"""
import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError

EXTENSIONES_PERMITIDAS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

MIME_POR_FIRMA = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}

TAMANO_MAXIMO_POR_DEFECTO = 5 * 1024 * 1024


def _mime_real(archivo):
    """Devuelve el MIME deducido de la cabecera, sin confiar en el navegador."""
    posicion = archivo.tell()
    try:
        cabecera = archivo.read(8)
    finally:
        archivo.seek(posicion)
    for firma, mime in MIME_POR_FIRMA.items():
        if cabecera.startswith(firma):
            return mime
    return None


def _origen(archivo):
    """Devuelve el archivo con ``content_type`` cuando el valor es un FieldFile."""
    if not hasattr(archivo, "content_type") and hasattr(archivo, "file"):
        return archivo.file
    return archivo


def validar_archivo_documento(archivo):
    nombre = getattr(archivo, "name", "") or ""
    if not nombre or "\x00" in nombre or "/" in nombre or "\\" in nombre or ".." in nombre:
        raise ValidationError("El nombre del archivo no es válido.")

    extension = Path(nombre).suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        permitidas = ", ".join(sorted(EXTENSIONES_PERMITIDAS))
        raise ValidationError(f"Formato no permitido. Usa uno de: {permitidas}.")

    origen = _origen(archivo)
    tamano = getattr(archivo, "size", None)
    if not tamano:
        raise ValidationError("El archivo está vacío.")
    maximo = getattr(settings, "DOCUMENTO_PROVEEDOR_MAX_BYTES",
                     TAMANO_MAXIMO_POR_DEFECTO)
    if tamano > maximo:
        etiqueta = (f"{maximo / (1024 * 1024):g} MB" if maximo >= 1024 * 1024
                    else f"{maximo} bytes")
        raise ValidationError(
            f"El archivo supera el tamaño máximo permitido ({etiqueta}).")

    mime_real = _mime_real(origen)
    mime_esperado = EXTENSIONES_PERMITIDAS[extension]
    if mime_real != mime_esperado:
        raise ValidationError(
            "El contenido del archivo no corresponde a un PDF, JPG o PNG válido.")

    declarado = (getattr(origen, "content_type", "") or "").split(";")[0].strip().lower()
    if declarado and declarado not in {mime_real, "application/octet-stream"}:
        raise ValidationError(
            "El tipo MIME declarado no coincide con el contenido real del archivo.")


def ruta_documento_proveedor(instance, filename):
    """Genera un nombre aleatorio y seguro; descarta cualquier ruta original."""
    extension = Path(os.path.basename(filename or "")).suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        extension = ""
    return f"proveedores/{uuid4().hex}{extension}"
