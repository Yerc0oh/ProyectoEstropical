
import json

from django.shortcuts import render, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.core.access import cliente_required
from apps.accounts.models import Perfil
from apps.preferences.models import PreferenciaViaje

from .services import recomendar_paquetes
from .chatbot_service import responder_chatbot


# ==========================================================
# OBTENER PERFIL DEL CLIENTE
# ==========================================================

def obtener_perfil(request):
    """
    Obtiene el perfil asociado al usuario autenticado.
    """

    perfil = Perfil.objects.filter(
        usuario=request.user
    ).first()

    if perfil is None:
        raise PermissionDenied(
            "No tienes un perfil de cliente."
        )

    return perfil


# ==========================================================
# LISTADO DE RECOMENDACIONES
# ==========================================================

@cliente_required
def lista_recomendaciones(request):
    """
    Muestra las preferencias de viaje del cliente.
    """

    perfil = obtener_perfil(request)

    preferencias = PreferenciaViaje.objects.filter(
        cliente=perfil,
        activa=True
    ).order_by("-id")

    return render(
        request,
        "recommendations/lista.html",
        {
            "preferencias": preferencias,
        }
    )


# ==========================================================
# RESULTADOS DE RECOMENDACIONES
# ==========================================================

@cliente_required
def resultados_recomendaciones(request, pk):
    """
    Genera recomendaciones según una preferencia
    perteneciente al cliente autenticado.
    """

    perfil = obtener_perfil(request)

    preferencia = get_object_or_404(
        PreferenciaViaje,
        pk=pk,
        cliente=perfil,
        activa=True,
    )

    resultados = recomendar_paquetes(preferencia)

    return render(
        request,
        "recommendations/resultados.html",
        {
            "preferencia": preferencia,
            "resultados": resultados,
        }
    )


# ==========================================================
# PÁGINA DEL CHATBOT
# ==========================================================

@cliente_required
def pagina_chatbot(request):
    """
    Muestra la interfaz del asistente inteligente.
    """

    return render(
        request,
        "recommendations/chatbot.html"
    )


# ==========================================================
# CONSULTAR CHATBOT CON MEMORIA CONVERSACIONAL
# ==========================================================

@cliente_required
@require_POST
def consultar_chatbot(request):
    """
    Procesa las consultas del chatbot.

    Funcionalidades:
    - Recibe preguntas desde JavaScript o formularios.
    - Valida el contenido recibido.
    - Recupera el historial reciente de la sesión.
    - Consulta el servicio de Gemini.
    - Guarda la conversación en la sesión.
    - Devuelve la respuesta en formato JSON.
    """

    # ------------------------------------------------------
    # 1. OBTENER LA PREGUNTA
    # ------------------------------------------------------

    try:
        if "application/json" in request.content_type:
            datos = json.loads(request.body)
            pregunta = datos.get("pregunta", "")
        else:
            pregunta = request.POST.get("pregunta", "")

    except (ValueError, TypeError, AttributeError):
        return JsonResponse(
            {
                "error": "El formato de la solicitud no es válido."
            },
            status=400
        )

    # ------------------------------------------------------
    # 2. VALIDAR LA PREGUNTA
    # ------------------------------------------------------

    if not isinstance(pregunta, str):
        return JsonResponse(
            {
                "error": "La pregunta debe contener texto."
            },
            status=400
        )

    pregunta = pregunta.strip()

    if not pregunta:
        return JsonResponse(
            {
                "error": "Debes escribir una pregunta."
            },
            status=400
        )

    if len(pregunta) > 1000:
        return JsonResponse(
            {
                "error": "Máximo 1000 caracteres."
            },
            status=400
        )

    # ------------------------------------------------------
    # 3. RECUPERAR EL HISTORIAL DE LA SESIÓN
    # ------------------------------------------------------

    historial = request.session.get(
        "estropical_chat_historial",
        []
    )

    if not isinstance(historial, list):
        historial = []

    historial = historial[-8:]

    # ------------------------------------------------------
    # 4. CONSULTAR EL ASISTENTE INTELIGENTE
    # ------------------------------------------------------

    respuesta = responder_chatbot(
        pregunta,
        historial=historial
    )

    # ------------------------------------------------------
    # 5. GUARDAR LOS MENSAJES EN LA SESIÓN
    # ------------------------------------------------------

    historial.append({
        "rol": "usuario",
        "contenido": pregunta
    })

    historial.append({
        "rol": "asistente",
        "contenido": respuesta
    })

    request.session["estropical_chat_historial"] = (
        historial[-8:]
    )

    request.session.modified = True

    # ------------------------------------------------------
    # 6. DEVOLVER LA RESPUESTA AL NAVEGADOR
    # ------------------------------------------------------

    return JsonResponse({
        "respuesta": respuesta
    })
