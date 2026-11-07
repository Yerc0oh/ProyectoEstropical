from django.urls import path

from .access import public
from . import views

app_name = "core"

urlpatterns = [
    path("", public(views.home), name="home"),
]
