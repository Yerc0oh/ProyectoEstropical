
from django.urls import path

from .catalogo_chat import consultar_catalogo
from . import views

app_name = "recommendations"

urlpatterns = [
    path(
        "recomendaciones/",
        views.lista_recomendaciones,
        name="lista",
    ),
    path(
        "recomendaciones/<int:pk>/",
        views.resultados_recomendaciones,
        name="resultados",
    ),
    path(
        "asistente/",
        views.pagina_chatbot,
        name="chatbot",
    ),
    path(
        "asistente/consultar/",
        views.consultar_chatbot,
        name="chatbot_consultar",
    ),
    
path(
    "ia/opciones/",
    consultar_catalogo,
    name="catalogo_chat",
),

]
