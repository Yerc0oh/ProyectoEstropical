# AGENTS.md

Django 5.2 monolith (PostgreSQL, server-rendered templates, Bootstrap 5). Academic project
covering Sprints 1–2 only; reservations/payments (Sprint 3+) do not exist yet.

## Setup

- Windows/PowerShell, from repo root:
  `py -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt`
- Copy `.env.example` to `.env`. `SECRET_KEY` is required (no default) and
  `DATABASE_URL` must point to PostgreSQL (`postgres://user:pass@localhost:5432/estropical_db`).
  There is no SQLite fallback.
- `python manage.py migrate` also runs data migrations that create groups `Administrador`
  and `Cliente` and seed countries/categories. Do not delete these migrations.
- `createsuperuser` should use an email as the username; login treats the username as an email.
- `manage.py` always uses `config.settings.dev` (it sets the env var before Django loads).
  `wsgi.py`/`asgi.py` default to `config.settings.prod`, which requires real `ALLOWED_HOSTS`,
  HTTPS, and secure cookies.

## Commands

- Run: `python manage.py runserver`
- All tests: `python manage.py test` — 17 tests; they need a reachable PostgreSQL server
  (Django creates a test database, so the DB user needs `CREATEDB`).
- One test: `python manage.py test apps.accounts.tests.AccesoPorRolTests.test_cliente_no_accede_a_gestion`
- Config check: `python manage.py check`
- No linter, formatter, or typecheck is configured. Do not mass-reformat files.

## Access control (easiest thing to break)

- `LoginRequiredMiddleware` makes **every** view private by default. Public views must be
  marked with `@public` (alias for `login_not_required`) or wrapped as `public(View)` in `urls.py`.
- Admin-only views use `AdminRequiredMixin` or `@admin_required`. Anonymous users are
  redirected to login; authenticated users without the role get **403**, not a redirect.
- Roles are Django `auth.Group`s named exactly `Administrador` / `Cliente`. Use `ROL_ADMIN`
  and `ROL_CLIENTE` from `apps/core/access.py`; never hardcode role strings.
- The `Administrador` group is not Django staff: `/admin/` remains superuser-only.
- Every app defines an `app_name`; reverse with namespaces (`core:home`, `packages:catalogo`).
- Logout is POST-only; tests assert GET returns 405.
- URL layout: public catalogs `/destinos/`, `/paquetes/`; management `/gestion/...`;
  accounts `/cuentas/...`.

## Architecture and conventions

- Code lives in `apps/<domain>/` (`accounts`, `destinations`, `suppliers`, `hotels`,
  `flights`, `packages`) with models/forms/views/urls/admin/tests/migrations per app.
  `apps/core` holds shared access control, generic CRUD views, and Bootstrap form mixins.
- Management screens should extend `AdminListView`, `AdminCreateView`, `AdminUpdateView`,
  or `AdminSoftDeleteView` from `apps/core/views_base.py` and define `titulo`, `columnas`,
  `url_crear`, `url_editar`, `url_eliminar`, `url_listado`.
- "Delete" is logical: catalogs set `activo=False`; `Paquete` becomes `estado="archivado"`;
  `Vuelo` becomes `estado="cancelado"`. Never hard-delete referenced rows.
- Models and fields use Spanish snake_case. Every model sets an explicit singular `db_table`
  matching `docs/estropical_schema.sql` (BIGINT PK, amounts `NUMERIC(12,2)` in BOB, fixed
  states as `TextChoices` strings rather than lookup tables).
- `docs/estropical_schema.sql` describes all 6 sprints, but only Sprints 1–2 tables are
  implemented. Do not execute that SQL manually: it conflicts with Django migrations.
  Functions, triggers, and views are intentionally pending.
- `Paquete` represents one concrete departure date; `cupos_disponibles` is independent of
  hotel-room and flight-seat inventory. Do not assume real reservation logic exists.
- Business logic belongs in each app's `services.py` (see `apps/accounts/services.py`);
  forms use `BootstrapFormMixin` / `BootstrapModelForm`; templates are under root `templates/`.

## Before claiming work is done

- Run `python manage.py check` and `python manage.py test`; after model changes run
  `makemigrations` and inspect the generated migration (some migrations contain seed data).
- README lists pending features and the code has `TODO` markers (CU-08, CU-12–CU-17).
  Do not mark those complete without implementing them.
