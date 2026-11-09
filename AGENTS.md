
# AGENTS.md

Django 5.2 monolith (PostgreSQL, server-rendered templates, Bootstrap 5).
Academic project integrating Sprints 1-4:
- Sprints 1-2: accounts, destinations, suppliers, hotels, flights and packages.
- Sprint 3: reservations and itineraries (`apps/reservations`).
- Sprint 4: payments and invoicing (`apps/payments`).
- Sprints 5-6: pending development.

## Setup

- Windows/PowerShell, from repo root:
  `py -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt`
- Copy `.env.example` to `.env`. `SECRET_KEY` is required (no default) and `DATABASE_URL` must point to PostgreSQL (`postgres://user:pass@localhost:5432/estropical_db`).
  There is no SQLite fallback.
- `python manage.py migrate` also runs data migrations that create groups `Administrador` and `Cliente` and seed countries/categories. Do not delete these migrations.
- `createsuperuser` should use an email as the username; login treats the username as an email.
- `manage.py` uses `config.settings.dev`.
  `wsgi.py`/`asgi.py` default to `config.settings.prod`, which requires real `ALLOWED_HOSTS`, HTTPS, and secure cookies.

## Commands

- Run: `python manage.py runserver`
- All tests: `python manage.py test`. The total number of tests must be verified after integration.
  Tests require a reachable PostgreSQL server. Django creates a test database, so the DB user needs `CREATEDB`.
- One test: `python manage.py test apps.accounts.tests.AccesoPorRolTests.test_cliente_no_accede_a_gestion`
- Config check: `python manage.py check`
- No linter, formatter, or typecheck is configured. Do not mass-reformat files.

## Access control

- `LoginRequiredMiddleware` makes every view private by default. Public views must be marked with `@public` (alias for `login_not_required`) or wrapped as `public(View)` in `urls.py`.
- Admin-only views use `AdminRequiredMixin` or `@admin_required`. Anonymous users are redirected to login; authenticated users without the role get 403.
- Roles are Django `auth.Group`s named exactly `Administrador` / `Cliente`. Use `ROL_ADMIN` and `ROL_CLIENTE` from `apps/core/access.py`.
- The `Administrador` group is not Django staff: `/admin/` remains superuser-only.
- Every app defines an `app_name`; reverse with namespaces (`core:home`, `packages:catalogo`).
- Logout is POST-only; tests assert GET returns 405.
- URL layout: public catalogs `/destinos/`, `/paquetes/`; management `/gestion/...`; accounts `/cuentas/...`; supplier portal `/proveedor/documentos/`.
- Supplier documents are private: `Proveedor.usuario` links the owning account, and files are only served through `suppliers:documento_archivo`. Never expose `media/proveedores/` directly.

## Architecture and conventions

- Code lives in `apps/<domain>/` with models/forms/views/urls/admin/tests/migrations per app.
- Main applications: accounts, destinations, suppliers, hotels, flights, packages, reservations and payments.
- `apps/core` holds shared access control, generic CRUD views, Bootstrap form mixins and PDF utilities.
- Management screens should extend `AdminListView`, `AdminCreateView`, `AdminUpdateView`, or `AdminSoftDeleteView` from `apps/core/views_base.py` when appropriate.
- "Delete" is logical: catalogs set `activo=False`; `Paquete` becomes `estado="archivado"`; `Vuelo` becomes `estado="cancelado"`. Never hard-delete referenced rows.
- Models and fields use Spanish snake_case. Every model sets an explicit singular `db_table` matching `docs/estropical_schema.sql`.
- Amounts are stored in BOB and states use `TextChoices` where applicable.
- `docs/estropical_schema.sql` describes all six sprints. Do not execute that SQL manually: database objects must be managed through Django migrations.
- Sprints 1-4 include reservation and payment models, plus promotion and system parameter models.
- The Sprint 3 and 4 migrations define database functions, triggers and views, including `trg_reserva_cupos`, `fn_penalidad_cancelacion`, `fn_cerrar_caja` and `v_saldo_reserva`.
- `Paquete` represents a concrete departure date.
- Capacity updates for hotels, flights and packages use `apps/core/disponibilidad.py` for administrative changes.
- Reservation-related capacity changes are handled by the database trigger. Never decrement `cupos_disponibles` again in Python.
- The interaction between administrative capacity updates and reservation triggers must be tested after integration.
- `Reserva.subtotal/total` and `CierreCaja.saldo` are `GeneratedField`s: refresh the instance after saving before reading them.
- Online payments use `payments.services.pasarela_simulada`; card data is never stored.
- Business logic belongs in each app's `services.py` where applicable.
- Forms use `BootstrapFormMixin` / `BootstrapModelForm`; templates are under root `templates/`.

## Before claiming work is done

- Run `python manage.py check` and `python manage.py test`.
- After model changes, inspect generated migrations before applying them.
- Verify that merged migrations and database triggers work correctly with PostgreSQL.
- Check permissions, navigation, URL names and interactions between applications.
- Review the README and existing TODO markers. Do not mark pending features as completed without implementation and testing.
- Do not modify or overwrite teammates' branches while integrating the project.
- Sprints 5 and 6 must be developed without removing functionality from Sprints 1-4.
