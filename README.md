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

Pruebas: `python manage.py test` (35 pruebas de acceso por rol, registro, recuperación, reenvío de verificación, perfil y gestión).

## Accesos y seguridad

| Visitante | Cómo se identifica | Qué puede hacer |
|---|---|---|
| Sin cuenta | sin sesión | Inicio, catálogo de destinos y paquetes (ver/filtrar/comparar), registro, login, recuperar contraseña |
| Cliente | grupo `Cliente` | Todo lo anterior + su perfil (y, en el Sprint 3, reservas y pagos) |
| Administrador | grupo `Administrador` o superusuario | Todo lo anterior + panel `/gestion/...` (usuarios, destinos, paquetes, proveedores, hoteles, vuelos) |

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
* En desarrollo los correos se imprimen en la consola del servidor.

## Estructura

```
config/settings/{base,dev,prod}.py   configuración por entorno (variables en .env)
apps/core/          access.py (roles), formularios y vistas CRUD base, home
apps/accounts/      Perfil, registro, login, recuperación, perfil, usuarios y roles   (S1 CU-01..06)
apps/destinations/  Pais, Categoria, Destino, DestinoFoto, catálogo y gestión          (S1 CU-07, 08)
apps/suppliers/     Proveedor, ProveedorDocumento                                      (S2 CU-13)
apps/hotels/        Hotel, TipoHabitacion, TarifaHabitacion                            (S2 CU-14)
apps/flights/       Vuelo                                                              (S2 CU-15)
apps/packages/      Paquete y sus relaciones, catálogo, detalle, comparar, gestión     (S2 CU-09..12)
templates/ static/ media/            plantillas, CSS/JS, archivos subidos
docs/               estropical_schema.sql (esquema completo, S1-S6), diagrama ER (.drawio/.png)
```

Los modelos usan `db_table` y nombres de columna del `docs/estropical_schema.sql`. Las migraciones de
Django crean las tablas de los Sprints 1 y 2; las funciones, triggers y vistas del esquema
(`trg_reserva_cupos`, `fn_penalidad_cancelacion`, `fn_cerrar_caja`, vistas) se agregarán en el
Sprint 3 y 4 con migraciones `RunSQL`.

## Pendiente por completar (buscar `TODO` en el código)

- CU-08: formset de fotos del destino (subir, ordenar, elegir portada).
- CU-12: formsets para asignar hoteles, vuelos, servicios y actividades a un paquete.
- CU-13: carga y validación de documentos del proveedor.
- CU-14: gestión de tipos de habitación y tarifas por hotel.
- CU-16: actualizar disponibilidad (habitaciones, asientos, cupos).
- CU-17: confirmar servicios con proveedores (depende de reservas → Sprint 3).
- Portada (`core/home.html`), diseño final, validar filtros del catálogo.
- Producción: SMTP real, `ALLOWED_HOSTS`, servir `/media/`, límite de intentos de login.
