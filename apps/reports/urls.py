
from django.urls import path

from . import views


app_name = "reports"

urlpatterns = [
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "excel/",
        views.exportar_excel,
        name="excel",
    ),
    path(
        "pdf/",
        views.exportar_pdf,
        name="pdf",
    ),
]
