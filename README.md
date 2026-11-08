# Estropical.com · Tropical Tours Ltda.

Sistema web de venta de viajes (proyecto académico). **Este esqueleto cubre los Sprints 1 y 2.**
Stack: Django 5.2 · PostgreSQL · Bootstrap 5 · plantillas HTML (sin API separada).

## Puesta en marcha

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # editar SECRET_KEY y DATABASE_URL
createdb estropical_db                                 # o desde pgAdmin
python manage.py migrate                               # crea tablas + roles + países/categorías base
python manage.py createsuperuser                       # usar un correo como nombre de usuario
python manage.py runserver
```

Pruebas: `python manage.py test` (180 pruebas de acceso por rol, registro, recuperación, reenvío de verificación, perfil, cambio de correo, cambio de contraseña, paquetes, filtros del catálogo, hoteles, vuelos, disponibilidad, documentos de proveedores y gestión).

## Accesos y seguridad

| Visitante | Cómo se identifica | Qué puede hacer |
|---|---|---|
| Sin cuenta | sin sesión | Inicio, catálogo de destinos y paquetes (ver/filtrar/comparar), registro, login, recuperar contraseña |
| Cliente | grupo `Cliente` | Todo lo anterior + su perfil (y, en el Sprint 3, reservas y pagos) |
| Proveedor | usuario vinculado en `Proveedor.usuario` | Su perfil + `/proveedor/documentos/` (cargar, consultar y descargar solo sus documentos) |
| Administrador | grupo `Administrador` o superusuario | Todo lo anterior + panel `/gestion/...` (usuarios, destinos, paquetes, proveedores, documentos, hoteles, vuelos) |

* **Token de sesión:** al iniciar sesión Django emite una cookie de sesión firmada
  (`HttpOnly`, `SameSite=Lax`, caduca a las 8 h; `Secure` en producción) más token CSRF en cada formulario.
* **Deny by default:** `LoginRequiredMiddleware` exige sesión en TODAS las vistas. Una vista es
  pública solo si se envuelve con `public(...)` (ver `apps/core/access.py` y los `urls.py`).
  Si olvidas marcar una vista, queda protegida, no expuesta.
* **Roles:** `AdminRequiredMixin` / `ClienteRequiredMixin` (clases) y `@admin_required` /
  `@cliente_required` (funciones). Anónimo → redirige al login; con sesión pero sin el rol → 403.
* Verificación de correo al registrarse (cuenta inactiva hasta abrir el enlace, de un solo uso),
  recuperación de contraseña, cierre de sesión solo por POST.
* `/admin/` (Django admin) queda solo para superusuarios: usuarios, grupos, logs y errores.
* **Documentos de proveedores:** son privados. Solo el proveedor propietario o un
  administrador pueden descargarlos mediante una vista autenticada; la carpeta
  `/media/proveedores/` queda excluida del servido público de archivos.
* En desarrollo los correos se imprimen en la consola del servidor.

## Estructura

```
config/settings/{base,dev,prod}.py   configuración por entorno (variables en .env)
apps/core/          access.py (roles), formularios y vistas CRUD base, home
apps/accounts/      Perfil, registro, login, recuperación, perfil, usuarios y roles   (S1 CU-01..06)
apps/destinations/  Pais, Categoria, Destino, DestinoFoto, catálogo y gestión          (S1 CU-07, 08)
apps/suppliers/     Proveedor, ProveedorDocumento, portal y revisión de docs     (S2 CU-13)
apps/hotels/        Hotel, TipoHabitacion, TarifaHabitacion                   (S2 CU-14, CU-16)
apps/flights/       Vuelo                                                     (S2 CU-15, CU-16)
apps/packages/      Paquete y sus relaciones, catálogo, detalle, comparar, gestión (S2 CU-09..12, CU-16)
templates/ static/ media/            plantillas, CSS/JS, archivos subidos
docs/               estropical_schema.sql (esquema completo, S1-S6), diagrama ER (.drawio/.png)
```

Los modelos usan `db_table` y nombres de columna del `docs/estropical_schema.sql`. Las migraciones de
Django crean las tablas de los Sprints 1 y 2; las funciones, triggers y vistas del esquema
(`trg_reserva_cupos`, `fn_penalidad_cancelacion`, `fn_cerrar_caja`, vistas) se agregarán en el
Sprint 3 y 4 con migraciones `RunSQL`.

## Pendiente por completar (buscar `TODO` en el código)

- CU-08: formset de fotos del destino (subir, ordenar, elegir portada).
- CU-17: confirmar servicios con proveedores (depende de reservas → Sprint 3).
- Portada (`core/home.html`), diseño final.
- Producción: SMTP real, `ALLOWED_HOSTS`, servir solo `/media/` público, límite de intentos de login.
