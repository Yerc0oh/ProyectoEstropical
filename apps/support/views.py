
from django.contrib import messages
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import require_POST

from apps.core.access import cliente_required, admin_required
from apps.notifications.services import crear_notificacion

from .forms import (
    TicketForm,
    RespuestaTicketForm,
    GestionTicketForm,
)
from .models import Ticket


@cliente_required
def mis_tickets(request):
    tickets = Ticket.objects.filter(
        cliente=request.user
    )

    return render(
        request,
        "support/mis_tickets.html",
        {"tickets": tickets},
    )


@cliente_required
def crear_ticket(request):
    if request.method == "POST":
        formulario = TicketForm(request.POST)

        if formulario.is_valid():
            ticket = formulario.save(commit=False)
            ticket.cliente = request.user
            ticket.save()

            messages.success(
                request,
                "Tu solicitud fue registrada correctamente.",
            )

            return redirect(
                "support:detalle",
                pk=ticket.pk,
            )
    else:
        formulario = TicketForm()

    return render(
        request,
        "support/crear_ticket.html",
        {"formulario": formulario},
    )


@cliente_required
def detalle_ticket(request, pk):
    ticket = get_object_or_404(
        Ticket,
        pk=pk,
        cliente=request.user,
    )

    respuestas = ticket.respuestas.select_related(
        "autor"
    )

    return render(
        request,
        "support/detalle_ticket.html",
        {
            "ticket": ticket,
            "respuestas": respuestas,
            "es_gestion": False,
        },
    )


@admin_required
def gestion_tickets(request):
    tickets = Ticket.objects.select_related(
        "cliente"
    )

    estado = request.GET.get("estado", "").strip()

    estados_validos = {
        codigo for codigo, _ in Ticket.ESTADOS
    }

    if estado in estados_validos:
        tickets = tickets.filter(estado=estado)

    return render(
        request,
        "support/gestion_tickets.html",
        {
            "tickets": tickets,
            "estado_actual": estado,
            "estados": Ticket.ESTADOS,
        },
    )


@admin_required
def gestionar_ticket(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("cliente"),
        pk=pk,
    )

    if request.method == "POST":
        formulario = GestionTicketForm(
            request.POST,
            instance=ticket,
        )

        respuesta_form = RespuestaTicketForm(
            request.POST
        )

        if formulario.is_valid() and respuesta_form.is_valid():

            mensaje = respuesta_form.cleaned_data["mensaje"].strip()

            with transaction.atomic():
                ticket = formulario.save()

                respuesta = respuesta_form.save(commit=False)
                respuesta.ticket = ticket
                respuesta.autor = request.user
                respuesta.save()

                transaction.on_commit(
                    lambda: crear_notificacion(
                        usuario=ticket.cliente,
                        titulo="Respuesta a tu solicitud",
                        mensaje=(
                            f"Tu ticket #{ticket.pk} "
                            f"recibió una nueva respuesta."
                        ),
                        tipo="sistema",
                        url=f"/soporte/tickets/{ticket.pk}/",
                    )
                )

            messages.success(
                request,
                "La respuesta fue registrada correctamente.",
            )

            return redirect(
                "support:gestionar",
                pk=ticket.pk,
            )

    else:
        formulario = GestionTicketForm(
            instance=ticket
        )
        respuesta_form = RespuestaTicketForm()

    respuestas = ticket.respuestas.select_related(
        "autor"
    )

    return render(
        request,
        "support/detalle_ticket.html",
        {
            "ticket": ticket,
            "respuestas": respuestas,
            "formulario": formulario,
            "respuesta_form": respuesta_form,
            "es_gestion": True,
        },
    )
