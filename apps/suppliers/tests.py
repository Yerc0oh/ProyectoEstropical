import datetime as dt
import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.access import ROL_ADMIN, ROL_CLIENTE

from .models import Proveedor, ProveedorDocumento

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 40


class DocumentosProveedorBase(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(shutil.rmtree, self.media_root, True)
        self.addCleanup(self.media_override.disable)

        self.admin = User.objects.create_user(
            "admin@test.com", "admin@test.com", "Clave-segura-123")
        self.admin.groups.add(Group.objects.get(name=ROL_ADMIN))

        self.proveedor_user = User.objects.create_user(
            "proveedor@test.com", "proveedor@test.com", "Clave-segura-123")
        self.proveedor_user.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.proveedor = Proveedor.objects.create(
            razon_social="Hotelera SRL", nit="900", tipo=Proveedor.Tipo.HOTEL,
            usuario=self.proveedor_user)

        self.otro_user = User.objects.create_user(
            "otro@test.com", "otro@test.com", "Clave-segura-123")
        self.otro_user.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.otro_proveedor = Proveedor.objects.create(
            razon_social="Aerolínea SRL", nit="901", tipo=Proveedor.Tipo.AEROLINEA,
            usuario=self.otro_user)

        self.cliente = User.objects.create_user(
            "cliente@test.com", "cliente@test.com", "Clave-segura-123")
        self.cliente.groups.add(Group.objects.get(name=ROL_CLIENTE))

    # ------------------------------------------------------------- utilidades
    def _pdf(self, nombre="documento.pdf"):
        return SimpleUploadedFile(nombre, PDF, content_type="application/pdf")

    def _documento(self, proveedor=None, estado=ProveedorDocumento.Estado.PENDIENTE,
                   tipo="NIT", nombre="documento.pdf"):
        return ProveedorDocumento.objects.create(
            proveedor=proveedor or self.proveedor, tipo_documento=tipo,
            archivo=self._pdf(nombre), estado=estado)

    def _datos_carga(self, archivo=None, tipo="NIT"):
        return {
            "tipo_documento": tipo,
            "archivo": archivo or self._pdf(),
            "fecha_vencimiento": "2027-12-31",
        }

    def _url_carga(self):
        return reverse("suppliers:documento_cargar")

    def _url_lista(self):
        return reverse("suppliers:mis_documentos")

    def _url_descarga(self, documento):
        return reverse("suppliers:documento_archivo", args=[documento.pk])

    def _url_revisar(self, documento):
        return reverse("suppliers:gestion_documento_revisar", args=[documento.pk])


class CargaDocumentosTests(DocumentosProveedorBase):
    def test_proveedor_carga_pdf_valido(self):
        self.client.force_login(self.proveedor_user)
        r = self.client.post(self._url_carga(), self._datos_carga())
        self.assertEqual(r.status_code, 302)
        documento = ProveedorDocumento.objects.get(proveedor=self.proveedor)
        self.assertEqual(documento.estado, ProveedorDocumento.Estado.PENDIENTE)
        self.assertEqual(documento.tipo_documento, "NIT")
        self.assertEqual(documento.fecha_vencimiento, dt.date(2027, 12, 31))
        self.assertRegex(documento.archivo.name,
                         r"^proveedores/[0-9a-f]{32}\.pdf$")

    def test_nombre_original_peligroso_no_se_usa_en_la_ruta(self):
        self.client.force_login(self.proveedor_user)
        r = self.client.post(
            self._url_carga(),
            self._datos_carga(archivo=self._pdf("../../factura final.pdf")))
        self.assertEqual(r.status_code, 302)
        documento = ProveedorDocumento.objects.get(proveedor=self.proveedor)
        # Django elimina la ruta antes de validar y el modelo genera un nombre
        # aleatorio: ni "..", ni "/", ni el nombre original llegan al almacenamiento.
        self.assertRegex(documento.archivo.name,
                         r"^proveedores/[0-9a-f]{32}\.pdf$")
        self.assertNotIn("factura", documento.archivo.name)

    def test_extension_no_permitida_es_rechazada(self):
        self.client.force_login(self.proveedor_user)
        r = self.client.post(
            self._url_carga(),
            self._datos_carga(archivo=SimpleUploadedFile(
                "script.exe", PDF, content_type="application/pdf")))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Formato no permitido")
        self.assertFalse(ProveedorDocumento.objects.exists())

    def test_contenido_que_no_coincide_con_la_extension_es_rechazado(self):
        self.client.force_login(self.proveedor_user)
        r = self.client.post(
            self._url_carga(),
            self._datos_carga(archivo=SimpleUploadedFile(
                "falso.pdf", PNG, content_type="application/pdf")))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no corresponde a un PDF, JPG o PNG válido")
        self.assertFalse(ProveedorDocumento.objects.exists())

    def test_tipo_mime_declarado_incorrecto_es_rechazado(self):
        self.client.force_login(self.proveedor_user)
        r = self.client.post(
            self._url_carga(),
            self._datos_carga(archivo=SimpleUploadedFile(
                "documento.pdf", PDF, content_type="text/plain")))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "tipo MIME declarado no coincide")
        self.assertFalse(ProveedorDocumento.objects.exists())

    @override_settings(DOCUMENTO_PROVEEDOR_MAX_BYTES=100)
    def test_archivo_demasiado_grande_es_rechazado(self):
        self.client.force_login(self.proveedor_user)
        grande = SimpleUploadedFile(
            "grande.pdf", PDF + b"x" * 200, content_type="application/pdf")
        r = self.client.post(self._url_carga(), self._datos_carga(archivo=grande))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "supera el tamaño máximo")
        self.assertFalse(ProveedorDocumento.objects.exists())

    def test_archivo_vacio_es_rechazado(self):
        self.client.force_login(self.proveedor_user)
        r = self.client.post(
            self._url_carga(),
            self._datos_carga(archivo=SimpleUploadedFile(
                "vacio.pdf", b"", content_type="application/pdf")))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "El fichero enviado está vacío")
        self.assertFalse(ProveedorDocumento.objects.exists())


class ConsultaYAccesoTests(DocumentosProveedorBase):
    def test_admin_asigna_usuario_al_proveedor_y_este_accede_al_portal(self):
        user = User.objects.create_user(
            "nuevo@test.com", "nuevo@test.com", "Clave-segura-123")
        user.groups.add(Group.objects.get(name=ROL_CLIENTE))
        self.client.force_login(self.admin)
        r = self.client.post(reverse("suppliers:gestion_crear"), {
            "razon_social": "Operadora Nueva", "nit": "902", "tipo": "operador",
            "nombre_contacto": "", "correo": "", "telefono": "",
            "usuario": user.pk, "estado_validacion": "pendiente", "activo": "on",
        })
        self.assertEqual(r.status_code, 302)
        proveedor = Proveedor.objects.get(nit="902")
        self.assertEqual(proveedor.usuario, user)
        self.client.force_login(user)
        self.assertEqual(self.client.get(self._url_lista()).status_code, 200)

    def test_proveedor_consulta_sus_documentos_y_estado(self):
        self._documento(tipo="Licencia de funcionamiento")
        self.client.force_login(self.proveedor_user)
        r = self.client.get(self._url_lista())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Licencia de funcionamiento")
        self.assertContains(r, "Pendiente")

    def test_proveedor_no_ve_documentos_de_otro_proveedor(self):
        self._documento(proveedor=self.otro_proveedor, tipo="Contrato ajeno")
        self.client.force_login(self.proveedor_user)
        r = self.client.get(self._url_lista())
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Contrato ajeno")

    def test_proveedor_no_descarga_documento_ajeno(self):
        ajeno = self._documento(proveedor=self.otro_proveedor)
        self.client.force_login(self.proveedor_user)
        self.assertEqual(self.client.get(self._url_descarga(ajeno)).status_code, 404)

    def test_proveedor_descarga_su_propio_documento(self):
        propio = self._documento()
        self.client.force_login(self.proveedor_user)
        r = self.client.get(self._url_descarga(propio))
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertEqual(b"".join(r.streaming_content), PDF)

    def test_administrador_descarga_cualquier_documento(self):
        documento = self._documento()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self._url_descarga(documento)).status_code, 200)

    def test_anonimo_es_redirigido_al_login(self):
        documento = self._documento()
        r = self.client.get(self._url_lista())
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r["Location"])
        r = self.client.get(self._url_descarga(documento))
        self.assertEqual(r.status_code, 302)

    def test_usuario_sin_proveedor_no_accede_al_portal(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(self._url_lista()).status_code, 403)
        self.assertEqual(self.client.get(self._url_carga()).status_code, 403)

    def test_acceso_directo_a_la_carpeta_media_no_expone_documentos(self):
        documento = self._documento()
        self.client.force_login(self.proveedor_user)
        r = self.client.get(f"/media/{documento.archivo.name}")
        self.assertEqual(r.status_code, 404)


class RevisionDocumentosTests(DocumentosProveedorBase):
    def test_admin_aprueba_y_registra_revisor_y_fecha(self):
        documento = self._documento()
        self.client.force_login(self.admin)
        r = self.client.post(self._url_revisar(documento), {
            "decision": "aprobar", "motivo": "Documento legible."})
        self.assertEqual(r.status_code, 302)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, ProveedorDocumento.Estado.APROBADO)
        self.assertEqual(documento.revisado_por.usuario, self.admin)
        self.assertIsNotNone(documento.fecha_revision)
        self.assertEqual(documento.observacion, "Documento legible.")

    def test_admin_rechaza_con_motivo(self):
        documento = self._documento()
        self.client.force_login(self.admin)
        r = self.client.post(self._url_revisar(documento), {
            "decision": "rechazar", "motivo": "El NIT no coincide."})
        self.assertEqual(r.status_code, 302)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, ProveedorDocumento.Estado.RECHAZADO)
        self.assertEqual(documento.observacion, "El NIT no coincide.")
        self.assertEqual(documento.revisado_por.usuario, self.admin)
        self.assertIsNotNone(documento.fecha_revision)

    def test_rechazo_sin_motivo_no_modifica_el_documento(self):
        documento = self._documento()
        self.client.force_login(self.admin)
        r = self.client.post(self._url_revisar(documento), {
            "decision": "rechazar", "motivo": ""})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Debes indicar el motivo del rechazo")
        documento.refresh_from_db()
        self.assertEqual(documento.estado, ProveedorDocumento.Estado.PENDIENTE)
        self.assertIsNone(documento.revisado_por)
        self.assertIsNone(documento.fecha_revision)

    def test_cliente_no_puede_revisar(self):
        documento = self._documento()
        self.client.force_login(self.cliente)
        r = self.client.post(self._url_revisar(documento), {
            "decision": "aprobar", "motivo": ""})
        self.assertEqual(r.status_code, 403)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, ProveedorDocumento.Estado.PENDIENTE)

    def test_proveedor_tampoco_puede_revisar_su_documento(self):
        documento = self._documento()
        self.client.force_login(self.proveedor_user)
        r = self.client.post(self._url_revisar(documento), {
            "decision": "aprobar", "motivo": ""})
        self.assertEqual(r.status_code, 403)

    def test_documento_ya_revisado_no_se_puede_volver_a_revisar(self):
        documento = self._documento()
        self.client.force_login(self.admin)
        self.client.post(self._url_revisar(documento), {
            "decision": "aprobar", "motivo": ""})
        documento.refresh_from_db()
        fecha_original = documento.fecha_revision

        r = self.client.post(self._url_revisar(documento), {
            "decision": "rechazar", "motivo": "Cambio de opinión."}, follow=True)
        self.assertContains(r, "ya fue revisado")
        documento.refresh_from_db()
        self.assertEqual(documento.estado, ProveedorDocumento.Estado.APROBADO)
        self.assertEqual(documento.fecha_revision, fecha_original)
        self.assertEqual(documento.observacion, "")

    def test_pagina_de_revision_oculta_el_formulario_si_ya_fue_revisado(self):
        documento = self._documento(estado=ProveedorDocumento.Estado.APROBADO)
        self.client.force_login(self.admin)
        r = self.client.get(self._url_revisar(documento))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "ya fue revisado")
        self.assertNotContains(r, "Registrar revisión")

    def test_admin_consulta_cola_y_filtra_por_estado(self):
        self._documento(tipo="Pendiente uno")
        self._documento(tipo="Aprobado uno",
                        estado=ProveedorDocumento.Estado.APROBADO)
        self.client.force_login(self.admin)
        r = self.client.get(reverse("suppliers:gestion_documentos"))
        self.assertContains(r, "Pendiente uno")
        self.assertContains(r, "Aprobado uno")
        r = self.client.get(reverse("suppliers:gestion_documentos"),
                            {"estado": "aprobado"})
        self.assertNotContains(r, "Pendiente uno")
        self.assertContains(r, "Aprobado uno")

    def test_admin_consulta_documentos_de_un_proveedor(self):
        self._documento(tipo="Propio")
        self._documento(proveedor=self.otro_proveedor, tipo="Ajeno")
        self.client.force_login(self.admin)
        r = self.client.get(reverse("suppliers:gestion_documentos_proveedor",
                                    args=[self.proveedor.pk]))
        self.assertContains(r, "Propio")
        self.assertNotContains(r, "Ajeno")


class HistorialDeVersionesTests(DocumentosProveedorBase):
    def test_nueva_version_conserva_el_historial_y_la_revision_anterior(self):
        original = self._documento(tipo="Licencia")
        self.client.force_login(self.admin)
        self.client.post(self._url_revisar(original), {
            "decision": "aprobar", "motivo": "Vigente."})
        original.refresh_from_db()
        fecha_original = original.fecha_revision
        self.client.logout()

        self.client.force_login(self.proveedor_user)
        r = self.client.get(reverse("suppliers:documento_nueva_version",
                                    args=[original.pk]))
        self.assertContains(r, "Nueva versión")
        r = self.client.post(
            reverse("suppliers:documento_nueva_version", args=[original.pk]),
            self._datos_carga(tipo="Licencia"))
        self.assertEqual(r.status_code, 302)

        original.refresh_from_db()
        self.assertEqual(original.estado, ProveedorDocumento.Estado.APROBADO)
        self.assertEqual(original.fecha_revision, fecha_original)
        self.assertEqual(original.observacion, "Vigente.")
        self.assertEqual(self.proveedor.documentos.count(), 2)
        nueva = self.proveedor.documentos.exclude(pk=original.pk).get()
        self.assertEqual(nueva.estado, ProveedorDocumento.Estado.PENDIENTE)
        self.assertEqual(nueva.tipo_documento, "Licencia")

    def test_no_se_permite_nueva_version_de_un_documento_pendiente(self):
        original = self._documento()
        self.client.force_login(self.proveedor_user)
        r = self.client.post(
            reverse("suppliers:documento_nueva_version", args=[original.pk]),
            self._datos_carga(), follow=True)
        self.assertContains(r, "todavía está pendiente")
        self.assertEqual(self.proveedor.documentos.count(), 1)

    def test_no_se_puede_crear_version_de_documento_ajeno(self):
        ajeno = self._documento(proveedor=self.otro_proveedor,
                                estado=ProveedorDocumento.Estado.APROBADO)
        self.client.force_login(self.proveedor_user)
        r = self.client.get(reverse("suppliers:documento_nueva_version",
                                    args=[ajeno.pk]))
        self.assertEqual(r.status_code, 404)
