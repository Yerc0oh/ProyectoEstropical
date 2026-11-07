"""Pruebas de seguridad: los tres tipos de visitante (sin cuenta, cliente, administrador)."""
import re

from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.core.access import ROL_ADMIN, ROL_CLIENTE

PUBLICAS = ["core:home", "destinations:catalogo", "packages:catalogo", "packages:comparar",
            "accounts:login", "accounts:registro", "accounts:password_reset"]
SOLO_ADMIN = ["accounts:usuarios", "destinations:gestion_lista", "destinations:gestion_crear",
              "packages:gestion_lista", "packages:gestion_crear", "suppliers:gestion_lista",
              "hotels:gestion_lista", "flights:gestion_lista"]
SOLO_LOGUEADO = ["accounts:perfil"]


def crear_usuario(email, rol, **extra):
    u = User.objects.create_user(username=email, email=email, password="Clave-segura-123", **extra)
    u.groups.add(Group.objects.get(name=rol))
    return u


class AccesoPorRolTests(TestCase):
    def setUp(self):
        self.cliente_u = crear_usuario("cliente@test.com", ROL_CLIENTE)
        self.admin_u = crear_usuario("admin@test.com", ROL_ADMIN)

    def test_anonimo_ve_vistas_publicas(self):
        for nombre in PUBLICAS:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_anonimo_es_redirigido_al_login(self):
        for nombre in SOLO_ADMIN + SOLO_LOGUEADO:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)
            self.assertIn(reverse("accounts:login"), r.url, nombre)

    def test_cliente_no_accede_a_gestion(self):
        self.client.force_login(self.cliente_u)
        for nombre in SOLO_ADMIN:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403, nombre)
        self.assertEqual(self.client.get(reverse("accounts:perfil")).status_code, 200)

    def test_cliente_no_puede_enviar_posts_de_gestion(self):
        self.client.force_login(self.cliente_u)
        r = self.client.post(reverse("accounts:usuario_activo", args=[self.admin_u.pk]))
        self.assertEqual(r.status_code, 403)
        self.admin_u.refresh_from_db()
        self.assertTrue(self.admin_u.is_active)

    def test_admin_accede_a_gestion(self):
        self.client.force_login(self.admin_u)
        for nombre in SOLO_ADMIN + SOLO_LOGUEADO:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_django_admin_solo_superusuario(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.force_login(self.admin_u)  # rol Administrador de la app, no es staff
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        su = User.objects.create_superuser("root@test.com", "root@test.com", "Clave-segura-123")
        self.client.force_login(su)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_logout_solo_por_post(self):
        self.client.force_login(self.cliente_u)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("accounts:perfil")).status_code, 302)

    def test_admin_no_puede_bloquearse_a_si_mismo(self):
        self.client.force_login(self.admin_u)
        self.client.post(reverse("accounts:usuario_activo", args=[self.admin_u.pk]))
        self.admin_u.refresh_from_db()
        self.assertTrue(self.admin_u.is_active)

    def test_admin_bloquea_y_cambia_rol(self):
        self.client.force_login(self.admin_u)
        self.client.post(reverse("accounts:usuario_activo", args=[self.cliente_u.pk]))
        self.cliente_u.refresh_from_db()
        self.assertFalse(self.cliente_u.is_active)
        self.client.post(reverse("accounts:usuario_rol", args=[self.cliente_u.pk]), {"rol": ROL_ADMIN})
        self.assertEqual(list(self.cliente_u.groups.values_list("name", flat=True)), [ROL_ADMIN])

    def test_usuario_bloqueado_no_puede_ingresar(self):
        self.cliente_u.is_active = False
        self.cliente_u.save()
        r = self.client.post(reverse("accounts:login"),
                             {"username": "cliente@test.com", "password": "Clave-segura-123"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_correcto_y_redireccion_next(self):
        r = self.client.post(reverse("accounts:login") + "?next=" + reverse("accounts:perfil"),
                             {"username": "CLIENTE@test.com", "password": "Clave-segura-123",
                              "next": reverse("accounts:perfil")})
        self.assertRedirects(r, reverse("accounts:perfil"))


class RegistroTests(TestCase):
    DATOS = {"nombres": "Ana", "apellidos": "Lopez", "email": "Ana@Test.com", "tipo_documento": "CI",
             "nro_documento": "1234567", "telefono": "70000000",
             "password1": "Clave-segura-123", "password2": "Clave-segura-123"}

    def setUp(self):
        for rol in (ROL_ADMIN, ROL_CLIENTE):
            Group.objects.get_or_create(name=rol)

    def test_flujo_registro_verificacion_login(self):
        r = self.client.post(reverse("accounts:registro"), self.DATOS)
        self.assertEqual(r.status_code, 200)
        user = User.objects.get(username="ana@test.com")
        self.assertFalse(user.is_active)
        self.assertTrue(user.groups.filter(name=ROL_CLIENTE).exists())
        self.assertEqual(user.perfil.nro_documento, "1234567")
        # no puede ingresar antes de verificar
        self.client.post(reverse("accounts:login"), {"username": "ana@test.com", "password": "Clave-segura-123"})
        self.assertNotIn("_auth_user_id", self.client.session)
        # verifica con el enlace del correo
        enlace = re.search(r"http://\S+/cuentas/activar/\S+", mail.outbox[0].body).group(0)
        path = enlace.replace("http://localhost:8000", "")
        self.assertEqual(self.client.get(path).status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(self.client.get(path).status_code, 400)  # el token es de un solo uso
        self.client.post(reverse("accounts:login"), {"username": "ana@test.com", "password": "Clave-segura-123"})
        self.assertIn("_auth_user_id", self.client.session)

    def test_correo_y_documento_duplicados(self):
        self.client.post(reverse("accounts:registro"), self.DATOS)
        r = self.client.post(reverse("accounts:registro"), {**self.DATOS, "email": "otro@test.com"})
        self.assertContains(r, "documento ya está registrado")
        r = self.client.post(reverse("accounts:registro"), {**self.DATOS, "nro_documento": "999"})
        self.assertContains(r, "Ya existe una cuenta")

    def test_contrasena_debil(self):
        r = self.client.post(reverse("accounts:registro"),
                             {**self.DATOS, "password1": "123", "password2": "123"})
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(r.status_code, 200)

    def test_recuperar_contrasena(self):
        u = User.objects.create_user("c@test.com", "c@test.com", "Clave-segura-123")
        self.client.post(reverse("accounts:password_reset"), {"email": "c@test.com"})
        self.assertEqual(len(mail.outbox), 1)
        m = re.search(r"/cuentas/recuperar/(\S+)/(\S+)/", mail.outbox[0].body)
        r = self.client.get(f"/cuentas/recuperar/{m.group(1)}/{m.group(2)}/", follow=True)
        r = self.client.post(r.redirect_chain[-1][0], {"new_password1": "Otra-clave-456", "new_password2": "Otra-clave-456"})
        u.refresh_from_db()
        self.assertTrue(u.check_password("Otra-clave-456"))
