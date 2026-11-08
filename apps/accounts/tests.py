"""Pruebas de seguridad: los tres tipos de visitante (sin cuenta, cliente, administrador)."""
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Perfil
from apps.accounts.services import obtener_perfil, registrar_cliente
from apps.core.access import ROL_ADMIN, ROL_CLIENTE

PUBLICAS = ["core:home", "destinations:catalogo", "packages:catalogo", "packages:comparar",
            "accounts:login", "accounts:registro", "accounts:password_reset",
            "accounts:reenviar_activacion"]
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


class PerfilTests(TestCase):
    def setUp(self):
        self.cliente = crear_usuario("cliente@test.com", ROL_CLIENTE)
        self.admin = crear_usuario("admin@test.com", ROL_ADMIN)
        self.otro = crear_usuario("otro@test.com", ROL_CLIENTE)
        self.perfil_cliente = Perfil.objects.create(
            usuario=self.cliente, nombres="Ana", apellidos="Lopez", nro_documento="111111")
        self.perfil_admin = Perfil.objects.create(
            usuario=self.admin, nombres="Admin", apellidos="Uno", nro_documento="222222")
        self.perfil_otro = Perfil.objects.create(
            usuario=self.otro, nombres="Otro", apellidos="Usuario", nro_documento="333333")

    def _datos(self, **cambios):
        datos = {"nombres": "Ana", "apellidos": "Lopez", "tipo_documento": "CI",
                 "nro_documento": "111111", "fecha_nacimiento": "1990-01-01",
                 "telefono": "70000000", "direccion": "Calle 1", "nacionalidad": "",
                 "nit": "123456", "razon_social": "Ana SRL"}
        datos.update(cambios)
        return datos

    def test_anonimo_no_puede_acceder_al_perfil(self):
        r = self.client.get(reverse("accounts:perfil"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r.url)
        r = self.client.post(reverse("accounts:perfil"), self._datos(nombres="Intruso"))
        self.assertEqual(r.status_code, 302)
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nombres, "Ana")

    def test_cliente_consulta_y_modifica_su_perfil(self):
        self.client.force_login(self.cliente)
        r = self.client.get(reverse("accounts:perfil"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "cliente@test.com")
        r = self.client.post(reverse("accounts:perfil"),
                             self._datos(nombres="  Ana María  ", telefono="71111111"))
        self.assertRedirects(r, reverse("accounts:perfil"))
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nombres, "Ana María")
        self.assertEqual(self.perfil_cliente.telefono, "71111111")

    def test_admin_consulta_y_modifica_su_perfil(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("accounts:perfil")).status_code, 200)
        r = self.client.post(reverse("accounts:perfil"),
                             self._datos(nombres="Admin Editado", nro_documento="222222"))
        self.assertRedirects(r, reverse("accounts:perfil"))
        self.perfil_admin.refresh_from_db()
        self.assertEqual(self.perfil_admin.nombres, "Admin Editado")

    def test_no_puede_modificar_el_perfil_de_otro_usuario(self):
        self.client.force_login(self.cliente)
        r = self.client.get(reverse("accounts:perfil") + f"?usuario={self.otro.pk}")
        self.assertContains(r, "Ana")
        self.assertNotContains(r, "Otro")
        r = self.client.post(reverse("accounts:perfil"), self._datos(
            nombres="Cliente Editado", usuario=self.otro.pk))
        self.assertRedirects(r, reverse("accounts:perfil"))
        self.perfil_cliente.refresh_from_db()
        self.perfil_otro.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nombres, "Cliente Editado")
        self.assertEqual(self.perfil_otro.nombres, "Otro")

    def test_documento_duplicado_produce_error_comprensible(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse("accounts:perfil"), self._datos(nro_documento="333333"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ya existe un perfil con este tipo y número de documento")
        self.assertIn("nro_documento", r.context["form"].errors)
        self.assertNotIn("__all__", r.context["form"].errors)
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nro_documento, "111111")

    def test_editar_el_mismo_documento_no_genera_falso_duplicado(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse("accounts:perfil"),
                             self._datos(nombres="Ana Actualizada", nro_documento="111111"))
        self.assertRedirects(r, reverse("accounts:perfil"))
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nombres, "Ana Actualizada")

    def test_fecha_nacimiento_futura_es_rechazada(self):
        self.client.force_login(self.cliente)
        manana = timezone.localdate() + timedelta(days=1)
        r = self.client.post(reverse("accounts:perfil"),
                             self._datos(fecha_nacimiento=manana.isoformat()))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "La fecha de nacimiento no puede ser futura")
        self.perfil_cliente.refresh_from_db()
        self.assertIsNone(self.perfil_cliente.fecha_nacimiento)

    def test_longitudes_maximas_de_telefono_nit_y_razon_social(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse("accounts:perfil"), self._datos(
            telefono="1" * 21, nit="2" * 21, razon_social="x" * 151))
        self.assertEqual(r.status_code, 200)
        errores = r.context["form"].errors
        for campo in ("telefono", "nit", "razon_social"):
            self.assertIn(campo, errores)
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.telefono, "")
        self.assertEqual(self.perfil_cliente.nit, "")
        self.assertEqual(self.perfil_cliente.razon_social, "")

    def test_formulario_invalido_no_guarda_cambios_parciales(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse("accounts:perfil"),
                             self._datos(nombres="", telefono="79999999"))
        self.assertEqual(r.status_code, 200)
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nombres, "Ana")
        self.assertEqual(self.perfil_cliente.telefono, "")

    def test_superusuario_sin_perfil_obtiene_uno_provisional(self):
        superuser = User.objects.create_superuser(
            "root@test.com", "root@test.com", "Clave-segura-123")
        self.assertFalse(Perfil.objects.filter(usuario=superuser).exists())
        self.client.force_login(superuser)
        r = self.client.get(reverse("accounts:perfil"))
        self.assertEqual(r.status_code, 200)
        perfil = Perfil.objects.get(usuario=superuser)
        self.assertEqual(perfil.nro_documento, f"USR-{superuser.pk}")
        self.assertContains(r, "datos provisionales")

    def test_perfil_existente_no_se_sobrescribe_al_consultarlo(self):
        obtener_perfil(self.cliente)
        obtener_perfil(self.cliente)
        self.perfil_cliente.refresh_from_db()
        self.assertEqual(self.perfil_cliente.nombres, "Ana")
        self.assertEqual(self.perfil_cliente.apellidos, "Lopez")
        self.assertEqual(self.perfil_cliente.nro_documento, "111111")


class LoginSuperuserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("Yerco", "abed@test.com", "Clave-segura-123")

    def test_login_con_username_o_email_sin_importar_mayusculas(self):
        for identificador in ("Yerco", "yerco", "ABED@test.com"):
            self.client.logout()
            r = self.client.post(reverse("accounts:login"),
                                 {"username": identificador, "password": "Clave-segura-123"})
            self.assertRedirects(r, reverse("core:home"), msg_prefix=identificador)
            self.assertIn("_auth_user_id", self.client.session)


class RegistroTests(TestCase):
    DATOS = {"nombres": "Ana", "apellidos": "Lopez", "email": "Ana@Test.com", "tipo_documento": "CI",
             "nro_documento": "1234567", "telefono": "70000000",
             "password1": "Clave-segura-123", "password2": "Clave-segura-123"}

    def setUp(self):
        for rol in (ROL_ADMIN, ROL_CLIENTE):
            Group.objects.get_or_create(name=rol)

    def test_flujo_registro_verificacion_login(self):
        with self.captureOnCommitCallbacks(execute=True):
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

    def test_no_reutiliza_el_correo_de_otro_usuario(self):
        User.objects.create_user("otro", "ana@test.com", "Clave-segura-123")
        r = self.client.post(reverse("accounts:registro"), {**self.DATOS, "email": "ANA@TEST.COM"})
        self.assertContains(r, "Ya existe una cuenta")
        self.assertEqual(User.objects.filter(email__iexact="ana@test.com").count(), 1)

    def test_si_falla_el_perfil_no_queda_usuario_ni_correo(self):
        datos = {**self.DATOS, "email": "fallo@test.com", "nro_documento": "9999999"}
        with patch("apps.accounts.services.Perfil.objects.create", side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                registrar_cliente(datos)
        self.assertFalse(User.objects.filter(username="fallo@test.com").exists())
        self.assertEqual(len(mail.outbox), 0)

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


class ReenvioActivacionTests(TestCase):
    GENERICA = "Si el correo pertenece a una cuenta pendiente de verificación"

    def setUp(self):
        cache.clear()

    def _crear(self, email, activo=False):
        return User.objects.create_user(username=email.lower(), email=email,
                                        password="Clave-segura-123", is_active=activo)

    def _reenviar(self, email):
        return self.client.post(reverse("accounts:reenviar_activacion"), {"email": email})

    def test_reenvia_a_cuenta_inactiva_y_el_enlace_la_activa(self):
        user = self._crear("Pendiente@Test.com")
        total = User.objects.count()
        r = self._reenviar("PENDIENTE@test.com")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.GENERICA)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(User.objects.count(), total)
        user.refresh_from_db()
        self.assertFalse(user.is_active)  # el reenvío no activa la cuenta
        enlace = re.search(r"http://\S+/cuentas/activar/\S+", mail.outbox[0].body).group(0)
        path = enlace.replace("http://localhost:8000", "")
        self.assertEqual(self.client.get(path).status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_no_reenvia_a_cuenta_activa(self):
        user = self._crear("Activa@Test.com", activo=True)
        r = self._reenviar("activa@test.com")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.GENERICA)
        self.assertEqual(len(mail.outbox), 0)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_respuesta_generica_para_correo_inexistente(self):
        total = User.objects.count()
        r = self._reenviar("nadie@test.com")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.GENERICA)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(User.objects.count(), total)

    def test_limita_solicitudes_excesivas(self):
        self._crear("Limite@Test.com")
        self.assertEqual(self._reenviar("limite@test.com").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        # Mismo correo con otra capitalización: la marca de caché es la misma.
        self.assertEqual(self._reenviar("LIMITE@TEST.COM").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
