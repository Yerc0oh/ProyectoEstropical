
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.packages.models import Paquete
from .forms import ResenaForm
from .models import Resena


@login_required
def mis_resenas(request):
    resenas = Resena.objects.filter(
        cliente=request.user
    ).select_related("paquete")

    return render(
        request,
        "reviews/mis_resenas.html",
        {"resenas": resenas}
    )


@login_required
def crear_resena(request, paquete_id):
    paquete = get_object_or_404(Paquete, pk=paquete_id)

    if Resena.objects.filter(
        cliente=request.user,
        paquete=paquete
    ).exists():
        messages.warning(
            request,
            "Ya tienes una reseña para este paquete."
        )
        return redirect("reviews:mis_resenas")

    if request.method == "POST":
        form = ResenaForm(request.POST)

        if form.is_valid():
            resena = form.save(commit=False)
            resena.cliente = request.user
            resena.paquete = paquete
            resena.estado = "pendiente"

            try:
                with transaction.atomic():
                    resena.save()
            except IntegrityError:
                messages.error(
                    request,
                    "Ya existe una reseña para este paquete."
                )
                return redirect("reviews:mis_resenas")

            messages.success(
                request,
                "Tu reseña fue enviada para revisión."
            )
            return redirect("reviews:mis_resenas")
    else:
        form = ResenaForm()

    return render(
        request,
        "reviews/formulario.html",
        {"form": form, "paquete": paquete}
    )


@login_required
def editar_resena(request, pk):
    resena = get_object_or_404(
        Resena,
        pk=pk,
        cliente=request.user
    )

    if request.method == "POST":
        form = ResenaForm(request.POST, instance=resena)

        if form.is_valid():
            resena = form.save(commit=False)
            resena.estado = "pendiente"
            resena.save()

            messages.success(
                request,
                "Reseña actualizada correctamente."
            )
            return redirect("reviews:mis_resenas")
    else:
        form = ResenaForm(instance=resena)

    return render(
        request,
        "reviews/formulario.html",
        {
            "form": form,
            "paquete": resena.paquete,
            "editando": True
        }
    )


@login_required
@require_POST
def eliminar_resena(request, pk):
    resena = get_object_or_404(
        Resena,
        pk=pk,
        cliente=request.user
    )

    resena.delete()

    messages.success(
        request,
        "Reseña eliminada correctamente."
    )

    return redirect("reviews:mis_resenas")


def resenas_paquete(request, paquete_id):
    paquete = get_object_or_404(Paquete, pk=paquete_id)

    resenas = Resena.objects.filter(
        paquete=paquete,
        estado="aprobada"
    ).select_related("cliente")

    return render(
        request,
        "reviews/resenas_paquete.html",
        {
            "paquete": paquete,
            "resenas": resenas
        }
    )
