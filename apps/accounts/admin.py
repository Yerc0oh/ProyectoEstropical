from django.contrib import admin

from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "tipo_documento", "nro_documento", "usuario")
    search_fields = ("nombres", "apellidos", "nro_documento", "usuario__email")
