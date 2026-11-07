from django.shortcuts import render


def home(request):
    # TODO Sprint 1/2: mostrar destinos y paquetes destacados.
    return render(request, "core/home.html")
