import datetime as dt

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from apps.core.access import ROL_ADMIN
from apps.destinations.models import Categoria, Destino, Pais
from apps.packages.models import Paquete


class GestionYCatalogoTests(TestCase):
    def setUp(self):
        u = User.objects.create_user("a@test.com", "a@test.com", "Clave-segura-123")
        u.groups.add(Group.objects.get(name=ROL_ADMIN))
        self.client.force_login(u)

    def test_admin_crea_destino_y_paquete_y_visitante_lo_ve(self):
        r = self.client.post(reverse("destinations:gestion_crear"), {
            "pais": Pais.objects.get(codigo_iso="BO").pk, "categoria": Categoria.objects.first().pk,
            "nombre": "Uyuni", "codigo_iata": "UYU", "descripcion": "Salar", "activo": "on"})
        self.assertEqual(r.status_code, 302)
        destino = Destino.objects.get(nombre="Uyuni")
        hoy = dt.date.today()
        r = self.client.post(reverse("packages:gestion_crear"), {
            "destino": destino.pk, "nombre": "Salar 3D", "descripcion": "x", "condiciones": "y",
            "fecha_salida": hoy + dt.timedelta(days=30), "fecha_retorno": hoy + dt.timedelta(days=33),
            "precio_persona": "1500.00", "cupos_total": 10,
            "venta_desde": hoy, "venta_hasta": hoy + dt.timedelta(days=20), "estado": "publicado"})
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        p = Paquete.objects.get(nombre="Salar 3D")
        self.assertEqual(p.cupos_disponibles, 10)
        self.assertEqual(p.duracion_dias, 4)
        self.client.logout()  # visitante sin cuenta
        self.assertContains(self.client.get(reverse("packages:catalogo")), "Salar 3D")
        self.assertEqual(self.client.get(reverse("packages:detalle", args=[p.pk])).status_code, 200)
        self.assertContains(self.client.get(reverse("packages:comparar") + f"?ids={p.pk}"), "Salar 3D")

    def test_eliminar_es_logico(self):
        p = Pais.objects.first()
        d = Destino.objects.create(pais=p, categoria=Categoria.objects.first(), nombre="X")
        self.client.post(reverse("destinations:gestion_eliminar", args=[d.pk]))
        d.refresh_from_db()
        self.assertFalse(d.activo)
