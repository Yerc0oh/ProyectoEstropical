from django.contrib import admin

from .models import Proveedor, ProveedorDocumento

admin.site.register([Proveedor, ProveedorDocumento])
