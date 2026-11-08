from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.access import AdminRequiredMixin
from apps.core.views_base import (AdminCapacidadUpdateView, AdminCreateView,
                                  AdminListView, AdminSoftDeleteView,
                                  AdminUpdateView)

from .forms import HotelForm, TarifaHabitacionForm, TipoHabitacionForm
from .models import Hotel, TarifaHabitacion, TipoHabitacion


class HotelLista(AdminListView):
    model = Hotel
    titulo = "Gestionar hoteles"
    columnas = [("Hotel", "nombre"), ("Destino", "destino"), ("Estrellas", "estrellas"),
                ("Proveedor", "proveedor"), ("Activo", "activo")]
    url_crear = "hotels:gestion_crear"
    url_editar = "hotels:gestion_editar"
    url_eliminar = "hotels:gestion_eliminar"
    url_extra = "hotels:gestion_habitaciones"
    texto_extra = "Habitaciones"


class HotelCrear(AdminCreateView):
    model = Hotel
    form_class = HotelForm
    titulo = "Nuevo hotel"
    url_listado = "hotels:gestion_lista"


class HotelEditar(AdminUpdateView):
    model = Hotel
    form_class = HotelForm
    titulo = "Editar hotel"
    url_listado = "hotels:gestion_lista"


class HotelEliminar(AdminSoftDeleteView):
    model = Hotel
    url_listado = "hotels:gestion_lista"


# ------------------------------------------------------- CU-14 Tipos de habitación
class HotelAnidadoMixin(AdminRequiredMixin):
    """Resuelve el hotel de la URL y lo expone a la plantilla."""

    def get_hotel(self):
        if not hasattr(self, "_hotel"):
            self._hotel = get_object_or_404(Hotel, pk=self.kwargs["hotel_pk"])
        return self._hotel

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["hotel"] = self.get_hotel()
        return ctx


class TipoHabitacionLista(HotelAnidadoMixin, ListView):
    template_name = "hotels/tipo_habitacion_list.html"
    context_object_name = "tipos"

    def get_queryset(self):
        return TipoHabitacion.objects.filter(hotel=self.get_hotel()).order_by("nombre")


class TipoHabitacionCrear(HotelAnidadoMixin, SuccessMessageMixin, CreateView):
    model = TipoHabitacion
    form_class = TipoHabitacionForm
    template_name = "hotels/tipo_habitacion_form.html"
    success_message = "Tipo de habitación creado."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        hotel = self.get_hotel()
        kwargs["hotel"] = hotel
        if kwargs.get("instance") is None:
            kwargs["instance"] = TipoHabitacion(hotel=hotel)
        return kwargs

    def get_success_url(self):
        return reverse("hotels:gestion_habitaciones", args=[self.get_hotel().pk])


class TipoHabitacionEditar(HotelAnidadoMixin, AdminCapacidadUpdateView):
    model = TipoHabitacion
    form_class = TipoHabitacionForm
    template_name = "hotels/tipo_habitacion_form.html"
    success_message = "Tipo de habitación actualizado."
    campo_capacidad = "habitaciones_total"

    def get_queryset(self):
        return TipoHabitacion.objects.filter(hotel_id=self.kwargs["hotel_pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["hotel"] = self.get_hotel()
        return kwargs

    def get_success_url(self):
        return reverse("hotels:gestion_habitaciones", args=[self.get_hotel().pk])


class TipoHabitacionEliminar(HotelAnidadoMixin, DeleteView):
    model = TipoHabitacion
    template_name = "hotels/tipo_habitacion_confirm_delete.html"

    def get_queryset(self):
        return TipoHabitacion.objects.filter(hotel_id=self.kwargs["hotel_pk"])

    def get_success_url(self):
        return reverse("hotels:gestion_habitaciones", args=[self.get_hotel().pk])

    def form_valid(self, form):
        """No se elimina un tipo de habitación referenciado por un paquete."""
        try:
            with transaction.atomic():
                response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar este tipo de habitación porque está asignado a "
                "uno o más paquetes. Quita primero esa asignación.")
            return redirect(self.get_success_url())
        messages.success(self.request, "Tipo de habitación eliminado.")
        return response


# ------------------------------------------------------------- CU-14 Tarifas
class TipoHabitacionAnidadoMixin(HotelAnidadoMixin):
    def get_tipo_habitacion(self):
        if not hasattr(self, "_tipo_habitacion"):
            self._tipo_habitacion = get_object_or_404(
                TipoHabitacion.objects.select_related("hotel"),
                pk=self.kwargs["tipo_pk"], hotel_id=self.kwargs["hotel_pk"])
        return self._tipo_habitacion

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tipo_habitacion"] = self.get_tipo_habitacion()
        return ctx


class TarifaHabitacionLista(TipoHabitacionAnidadoMixin, ListView):
    template_name = "hotels/tarifa_list.html"
    context_object_name = "tarifas"

    def get_queryset(self):
        return TarifaHabitacion.objects.filter(
            tipo_habitacion=self.get_tipo_habitacion()).order_by("fecha_inicio")


class TarifaHabitacionCrear(TipoHabitacionAnidadoMixin, SuccessMessageMixin, CreateView):
    model = TarifaHabitacion
    form_class = TarifaHabitacionForm
    template_name = "hotels/tarifa_form.html"
    success_message = "Tarifa creada."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        tipo = self.get_tipo_habitacion()
        kwargs["tipo_habitacion"] = tipo
        if kwargs.get("instance") is None:
            kwargs["instance"] = TarifaHabitacion(tipo_habitacion=tipo)
        return kwargs

    def get_success_url(self):
        return reverse("hotels:gestion_tarifas", args=[
            self.get_hotel().pk, self.get_tipo_habitacion().pk])


class TarifaHabitacionEditar(TipoHabitacionAnidadoMixin, SuccessMessageMixin, UpdateView):
    model = TarifaHabitacion
    form_class = TarifaHabitacionForm
    template_name = "hotels/tarifa_form.html"
    success_message = "Tarifa actualizada."

    def get_queryset(self):
        return TarifaHabitacion.objects.filter(
            tipo_habitacion_id=self.kwargs["tipo_pk"],
            tipo_habitacion__hotel_id=self.kwargs["hotel_pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tipo_habitacion"] = self.get_tipo_habitacion()
        return kwargs

    def get_success_url(self):
        return reverse("hotels:gestion_tarifas", args=[
            self.get_hotel().pk, self.get_tipo_habitacion().pk])


class TarifaHabitacionEliminar(TipoHabitacionAnidadoMixin, DeleteView):
    model = TarifaHabitacion
    template_name = "hotels/tarifa_confirm_delete.html"

    def get_queryset(self):
        return TarifaHabitacion.objects.filter(
            tipo_habitacion_id=self.kwargs["tipo_pk"],
            tipo_habitacion__hotel_id=self.kwargs["hotel_pk"])

    def get_success_url(self):
        return reverse("hotels:gestion_tarifas", args=[
            self.get_hotel().pk, self.get_tipo_habitacion().pk])

    def form_valid(self, form):
        messages.success(self.request, "Tarifa eliminada.")
        return super().form_valid(form)
