
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Perfil
from apps.core.access import cliente_required

from .forms import PreferenciaViajeForm
from .models import PreferenciaViaje


def obtener_perfil(request):
    """Obtiene el perfil asociado al usuario autenticado."""
    return Perfil.objects.filter(usuario=request.user).first()


@cliente_required
def lista_preferencias(request):
    """Muestra únicamente las preferencias del cliente autenticado."""
    perfil = obtener_perfil(request)

    if perfil is None:
        return HttpResponseForbidden(
            "No tienes un perfil registrado."
        )

    preferencias = (
        PreferenciaViaje.objects
        .filter(cliente=perfil)
        .prefetch_related("destinos")
        .order_by("-fecha_actualizacion")
    )

    return render(
        request,
        "preferences/lista.html",
        {
            "preferencias": preferencias
        }
    )


@cliente_required
def crear_preferencia(request):
    """Permite registrar una nueva preferencia de viaje."""
    perfil = obtener_perfil(request)

    if perfil is None:
        return HttpResponseForbidden(
            "No tienes un perfil registrado."
        )

    if request.method == "POST":
        formulario = PreferenciaViajeForm(
            request.POST,
            cliente=perfil
        )

        if formulario.is_valid():
            preferencia = formulario.save(commit=False)
            preferencia.cliente = perfil
            preferencia.save()
            formulario.save_m2m()

            messages.success(
                request,
                "La preferencia se registró correctamente."
            )

            return redirect("preferences:lista")

    else:
        formulario = PreferenciaViajeForm(
            cliente=perfil
        )

    return render(
        request,
        "preferences/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Registrar preferencia de viaje"
        }
    )


@cliente_required
def detalle_preferencia(request, pk):
    """Permite consultar una preferencia propia."""
    perfil = obtener_perfil(request)

    if perfil is None:
        return HttpResponseForbidden(
            "No tienes un perfil registrado."
        )

    preferencia = get_object_or_404(
        PreferenciaViaje.objects.prefetch_related(
            "destinos__pais"
        ),
        pk=pk,
        cliente=perfil
    )

    return render(
        request,
        "preferences/detalle.html",
        {
            "preferencia": preferencia
        }
    )


@cliente_required
def editar_preferencia(request, pk):
    """Permite modificar únicamente una preferencia propia."""
    perfil = obtener_perfil(request)

    if perfil is None:
        return HttpResponseForbidden(
            "No tienes un perfil registrado."
        )

    preferencia = get_object_or_404(
        PreferenciaViaje,
        pk=pk,
        cliente=perfil
    )

    if request.method == "POST":
        formulario = PreferenciaViajeForm(
            request.POST,
            instance=preferencia,
            cliente=perfil
        )

        if formulario.is_valid():
            formulario.save()

            messages.success(
                request,
                "La preferencia se actualizó correctamente."
            )

            return redirect("preferences:lista")

    else:
        formulario = PreferenciaViajeForm(
            instance=preferencia,
            cliente=perfil
        )

    return render(
        request,
        "preferences/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar preferencia de viaje"
        }
    )


@cliente_required
@require_POST
def eliminar_preferencia(request, pk):
    """Elimina una preferencia propia mediante una solicitud POST."""
    perfil = obtener_perfil(request)

    if perfil is None:
        return HttpResponseForbidden(
            "No tienes un perfil registrado."
        )

    preferencia = get_object_or_404(
        PreferenciaViaje,
        pk=pk,
        cliente=perfil
    )

    preferencia.delete()

    messages.success(
        request,
        "La preferencia se eliminó correctamente."
    )

    return redirect("preferences:lista")
