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
]

if settings.DEBUG:
    # Fotos subidas, públicas en desarrollo (en producción las sirve el servidor web).
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", login_not_required(serve),
                {"document_root": settings.MEDIA_ROOT}),
    ]

