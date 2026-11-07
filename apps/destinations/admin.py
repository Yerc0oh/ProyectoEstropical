from django.contrib import admin

from .models import Categoria, Destino, DestinoFoto, Pais

admin.site.register([Pais, Categoria, DestinoFoto])


@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais", "categoria", "activo")
    list_filter = ("pais", "categoria", "activo")
    search_fields = ("nombre",)
