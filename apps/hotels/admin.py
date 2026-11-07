from django.contrib import admin

from .models import Hotel, TarifaHabitacion, TipoHabitacion

admin.site.register([Hotel, TipoHabitacion, TarifaHabitacion])
