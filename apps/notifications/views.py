
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.core.access import cliente_required
from .models import Notificacion


@cliente_required
def lista_notificaciones(request):

    notificaciones = Notificacion.objects.filter(
        usuario=request.user
    )

    pendientes = notificaciones.filter(
        leida=False
    ).count()

    return render(
        request,
        "notifications/lista.html",
        {
            "notificaciones": notificaciones,
            "pendientes": pendientes,
        }
    )


@cliente_required
@require_POST
def marcar_leida(request, pk):

    notificacion = get_object_or_404(
        Notificacion,
        pk=pk,
        usuario=request.user
    )

    notificacion.leida = True
    notificacion.save(update_fields=["leida"])

    return redirect("notifications:lista")


@cliente_required
@require_POST
def marcar_todas_leidas(request):

    Notificacion.objects.filter(
        usuario=request.user,
        leida=False
    ).update(leida=True)

    return redirect("notifications:lista")
