"""Lógica de negocio de documentos de proveedores (CU-13)."""
from django.db import transaction
from django.utils import timezone

from .models import ProveedorDocumento


class DocumentoYaRevisado(Exception):
    """La revisión solo puede realizarse una vez sobre un documento pendiente."""


class DecisionInvalida(Exception):
    """Decisión de revisión desconocida o rechazo sin motivo."""


@transaction.atomic
def revisar_documento(documento_id, revisor, decision, motivo=""):
    """Aprueba o rechaza un documento pendiente de forma atómica.

    ``select_for_update`` evita que dos administradores revisen el mismo
    documento a la vez en PostgreSQL: el segundo espera y vuelve a comprobar el
    estado, por lo que no se sobrescribe una revisión anterior.
    """
    documento = (ProveedorDocumento.objects.select_for_update()
                 .get(pk=documento_id))

    if documento.estado != ProveedorDocumento.Estado.PENDIENTE:
        raise DocumentoYaRevisado
    if decision not in {"aprobar", "rechazar"}:
        raise DecisionInvalida
    motivo = (motivo or "").strip()
    if decision == "rechazar" and not motivo:
        raise DecisionInvalida

    documento.estado = (ProveedorDocumento.Estado.APROBADO if decision == "aprobar"
                        else ProveedorDocumento.Estado.RECHAZADO)
    documento.observacion = motivo
    documento.revisado_por = revisor
    documento.fecha_revision = timezone.now()
    documento.save(update_fields=["estado", "observacion", "revisado_por",
                                  "fecha_revision"])
    return documento
