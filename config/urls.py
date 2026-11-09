from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    # Django admin: usuarios, grupos, logs y errores del sistema (solo superusuarios).
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("cuentas/", include("apps.accounts.urls")),
    path("", include("apps.destinations.urls")),
    path("", include("apps.suppliers.urls")),
    path("", include("apps.hotels.urls")),
    path("", include("apps.flights.urls")),
    path("", include("apps.packages.urls")),
    path("", include("apps.reservations.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.preferences.urls")),
    path("", include("apps.recommendations.urls")),
    path("notificaciones/", include("apps.notifications.urls")),
    path("reportes/", include("apps.reports.urls")),
    path("soporte/", include("apps.support.urls")),
    
    path("resenas/", include("apps.reviews.urls")),

]

if settings.DEBUG:
    # Archivos públicos en desarrollo. Se excluye expresamente la carpeta de
    # documentos de proveedores: esos archivos solo se sirven por la vista
    # protegida suppliers:documento_archivo.
    urlpatterns += [
        re_path(r"^media/(?!proveedores/)(?P<path>.*)$", login_not_required(serve),
                {"document_root": settings.MEDIA_ROOT}),
    ]

