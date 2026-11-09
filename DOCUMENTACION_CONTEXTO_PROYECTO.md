# Documento técnico de contexto — Estropical.com

> Documento de referencia elaborado a partir de una inspección directa del repositorio
> (código, migraciones, plantillas, configuración y pruebas). Describe el estado **real**
> del proyecto en la fecha de la auditoría. No sustituye al `README.md` ni al esquema de
> referencia `docs/estropical_schema.sql`; cuando existe una discrepancia se indica en la
> sección 14.

Fecha de auditoría: **9 de noviembre de 2026**  
Repositorio auditado: `estropical nuevo` (copia de trabajo local).

---

## 1. Información general del proyecto

### 1.1 Nombre y propósito

**Estropical.com — Tropical Tours Ltda.** es un sistema web académico de venta de viajes.
Su propósito es centralizar la oferta turística (destinos, hoteles, vuelos y paquetes) y
permitir que visitantes, clientes, administradores y proveedores interactúen con un catálogo
y un panel de gestión desde el navegador.

El repositorio implementa únicamente los **Sprints 1 y 2** del backlog académico. El
esquema de referencia `docs/estropical_schema.sql` describe los seis sprints, pero las
tablas, funciones, triggers y vistas de los Sprints 3 a 6 **no están implementados** en
Django.

### 1.2 Problema que busca resolver

La agencia necesita reemplazar la gestión dispersa de su oferta (hojas de cálculo,
documentos y comunicaciones manuales) por una aplicación única que:

- publique un catálogo consultable de destinos y paquetes;
- permita al personal administrativo mantener destinos, proveedores, hoteles, habitaciones,
  tarifas, vuelos y paquetes;
- permita a los proveedores cargar y consultar sus documentos sin exponerlos públicamente;
- gestione cuentas de clientes con verificación de correo, recuperación de contraseña,
  perfil y roles;
- conserve la disponibilidad cuando se modifican capacidades totales.

### 1.3 Objetivos funcionales identificables

1. Registro de clientes con verificación de correo electrónico y activación de cuenta.
2. Autenticación por correo o usuario, cierre de sesión seguro y recuperación de contraseña.
3. Gestión del perfil personal, cambio de contraseña y cambio de correo con confirmación.
4. Administración de usuarios: consulta, búsqueda, bloqueo/activación y asignación de rol.
5. Catálogo público de destinos con búsqueda y filtros por país y categoría.
6. Administración de destinos con borrado lógico.
7. Catálogo público de paquetes publicados y vigentes, con filtros validados.
8. Detalle de paquete y comparación de uno a tres paquetes.
9. Administración de paquetes con cuatro tipos de componentes: hoteles, vuelos, servicios
   y actividades.
10. Administración de proveedores y de sus documentos, con portal privado para el proveedor
    y revisión administrativa.
11. Administración de hoteles, tipos de habitación y tarifas por temporada.
12. Administración de vuelos.
13. Actualización de capacidades (habitaciones, asientos y cupos) conservando lo ocupado.

### 1.4 Usuarios y actores

| Actor | Identificación en el sistema | Interacción principal |
|---|---|---|
| Visitante anónimo | Sin sesión | Inicio, catálogos, detalle, comparador, registro, login y recuperación |
| Cliente | Usuario autenticado en el grupo `Cliente` | Todo lo público más su perfil y cambio de correo/contraseña |
| Administrador | Usuario en el grupo `Administrador` (o superusuario) | Todo lo público más el panel `/gestion/...` |
| Superusuario | `is_superuser=True` (y `is_staff=True`) | Panel de la aplicación y Django admin (`/admin/`) |
| Proveedor | Usuario autenticado vinculado por `Proveedor.usuario` | Portal `/proveedor/documentos/` con sus propios documentos |
| Sistema de correo | Configuración `EMAIL_URL` | Envío de enlaces de activación, recuperación y cambio de correo |

No existe un grupo `Proveedor` ni un modelo de empleado. El rol de proveedor se determina
exclusivamente por la relación uno a uno `Proveedor.usuario`.

### 1.5 Alcance funcional implementado actualmente

**Implementado:** Sprints 1 y 2 según el detalle de la sección 7, incluyendo el límite de
tres paquetes en el comparador y la validación de filtros del catálogo de paquetes.

**Parcialmente implementado:** CU-08, porque existen el modelo `DestinoFoto`, el catálogo,
el detalle y el CRUD de destinos, pero **no** hay formset de fotos en la interfaz propia; las
fotos solo se administran desde Django admin.

**No implementado:** CU-17 (confirmación de servicios con proveedores) y todo el alcance de
los Sprints 3 a 6 (reservas, pasajeros, pagos, facturación, reembolsos, reportes, reseñas,
notificaciones, promociones y configuración). El esquema SQL de referencia contiene esas
tablas, pero no existen modelos, migraciones, vistas, formularios ni pruebas en Django.

---

## 2. Tecnologías y herramientas

### 2.1 Lenguajes y frameworks

| Elemento | Versión declarada / verificada | Fuente |
|---|---|---|
| Python | 3.14.3 en el entorno virtual local; no hay versión fijada en el repositorio | `.venv` inspeccionado |
| Django | `>=5.2,<5.3`; instalado 5.2.19 | `requirements.txt`, entorno |
| PostgreSQL | 14+ según el esquema de referencia | `docs/estropical_schema.sql` |
| psycopg | `>=3.2`; instalado 3.3.8 | `requirements.txt`, entorno |
| django-environ | `>=0.11`; instalado 0.14.0 | `requirements.txt`, entorno |
| Pillow | `>=10.0`; instalado 13.0.0 | `requirements.txt`, entorno |
| Bootstrap | 5.3.3 (CDN) | `templates/base.html` |
| HTML/CSS/JavaScript | Plantillas Django, CSS propio y JavaScript vanilla | `templates/`, `static/` |

No se usa una API REST, un framework JavaScript (React/Vue), un motor de plantillas distinto
de Django ni un servicio de almacenamiento externo.

### 2.2 Base de datos

- Motor: **PostgreSQL**, configurado mediante `DATABASE_URL` (`django-environ`).
- No existe respaldo automático a SQLite en la configuración; sin `DATABASE_URL` válido la
  aplicación no arranca.
- Las pruebas también usan PostgreSQL por defecto (Django crea una base temporal), por lo
  que el usuario de base de datos necesita el privilegio `CREATEDB`.
- Todos los modelos declaran `db_table` explícito y usan `BigAutoField` como clave primaria.

### 2.3 Herramientas de desarrollo

- `manage.py` (Django).
- Migraciones de Django con datos sembrados en migraciones `RunPython`.
- Django admin para superusuarios.
- Servidor de desarrollo `runserver`.
- Git (repositorio local; no se auditó el historial remoto).
- No hay linter, formateador, typechecker ni pipeline CI configurado.

### 2.4 Arquitectura tecnológica general

Aplicación **monolítica Django** con patrón MVT (Modelo–Plantilla–Vista), renderizado en
servidor y sin API separada. El navegador solicita una URL; el `URLconf` selecciona la vista;
la vista aplica permisos, valida formularios, consulta modelos a través del ORM y renderiza
una plantilla Bootstrap. El correo se envía mediante el backend configurado (consola en
desarrollo). Los archivos públicos se sirven desde `media/` en desarrollo; los documentos de
proveedores se sirven únicamente por una vista autenticada.

---

## 3. Arquitectura y estructura del proyecto

### 3.1 Estructura de directorios representativa

```
estropical nuevo/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── AGENTS.md
├── config/
│   ├── settings/
│   │   ├── base.py          # configuración común, apps, middleware, correo, archivos
│   │   ├── dev.py           # DEBUG=True
│   │   └── prod.py          # DEBUG=False, HTTPS/HSTS/cookies seguras
│   ├── urls.py              # URLconf raíz y servido de media en DEBUG
│   ├── wsgi.py              # usa config.settings.prod por defecto
│   └── asgi.py              # usa config.settings.prod por defecto
├── apps/
│   ├── core/                # acceso, CRUD base, formularios base, disponibilidad, home
│   ├── accounts/            # User/Perfil, registro, login, perfil, usuarios y roles
│   ├── destinations/        # Pais, Categoria, Destino, DestinoFoto y catálogos
│   ├── suppliers/           # Proveedor, ProveedorDocumento, portal y revisión
│   ├── hotels/              # Hotel, TipoHabitacion, TarifaHabitacion
│   ├── flights/             # Vuelo
│   └── packages/            # Paquete, componentes, catálogo, comparador y gestión
├── templates/
│   ├── base.html
│   ├── 403.html / 404.html
│   ├── partials/            # navbar, mensajes, paginación, formulario
│   ├── core/                # home y CRUD genérico
│   ├── accounts/            # registro, login, perfil, usuarios, correos
│   ├── destinations/        # catálogo y detalle
│   ├── hotels/              # habitaciones y tarifas
│   ├── suppliers/           # documentos del proveedor y revisión
│   └── packages/            # catálogo, detalle, comparador y formulario de paquete
├── static/
│   ├── css/estropical.css
│   ├── js/main.js           # actualmente solo un TODO
│   └── img/
├── media/                    # archivos subidos (ignorados por Git salvo .gitkeep)
├── docs/
│   ├── estropical_schema.sql # esquema de referencia de los 6 sprints
│   └── estropical_er.drawio/.png
└── .venv/                    # entorno virtual local (no versionado)
```

Cada app contiene `models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`, `apps.py`,
`tests.py` y `migrations/`; `suppliers` añade `services.py` y `validators.py`, y `core`
añade `access.py`, `views_base.py`, `forms.py`, `disponibilidad.py` y `templatetags/`.
`packages` implementa su lógica en formularios y vistas; **no** tiene `services.py`.

### 3.2 Responsabilidad de cada aplicación

| App | Responsabilidad |
|---|---|
| `core` | Control de acceso (roles, decoradores y mixins), CRUD genérico del panel, mixins de Bootstrap, servicio de capacidad y página de inicio |
| `accounts` | Perfil, registro, activación, login/logout, recuperación y cambio de contraseña, cambio de correo, listado y administración de usuarios/roles |
| `destinations` | Países, categorías, destinos, fotos de destino, catálogo público y CRUD de destinos |
| `suppliers` | Proveedores, documentos privados, portal del proveedor, revisión administrativa y validación de archivos |
| `hotels` | Hoteles, tipos de habitación, tarifas por temporada, disponibilidad y CRUD anidado |
| `flights` | Vuelos, disponibilidad de asientos y CRUD |
| `packages` | Paquetes, sus cuatro tipos de componentes, catálogo, detalle, comparador y CRUD |

### 3.3 Separación de responsabilidades

- **Configuración:** `config/settings/` (común, desarrollo, producción) y `config/urls.py`.
- **Modelos:** `apps/*/models.py`, con reglas estructurales y restricciones de base de datos.
- **Formularios:** `apps/*/forms.py`; validaciones de entrada y estilos Bootstrap.
- **Vistas:** `apps/*/views.py`; vistas basadas en funciones y clases genéricas.
- **Lógica de negocio compartida:** `apps/core/disponibilidad.py`,
  `apps/accounts/services.py` y `apps/suppliers/services.py`.
- **Plantillas:** directorio raíz `templates/`, con herencia de `base.html` y parciales.
- **Pruebas:** `apps/*/tests.py`; no hay carpeta global de tests.

### 3.4 Middleware, context processors y componentes compartidos

**Middleware** (`config/settings/base.py`, en orden):

1. `SecurityMiddleware`
2. `SessionMiddleware`
3. `CommonMiddleware`
4. `CsrfViewMiddleware`
5. `AuthenticationMiddleware`
6. `LoginRequiredMiddleware` — toda vista exige sesión salvo que se marque como pública.
7. `MessageMiddleware`
8. `XFrameOptionsMiddleware`

**Context processor propio:** `apps.accounts.context_processors.roles` expone `es_admin`,
`es_cliente` y `proveedor_usuario` a todas las plantillas.

**Componentes compartidos:**

- `apps/core/access.py`: constantes `ROL_ADMIN`, `ROL_CLIENTE`, alias `public`,
  funciones `es_administrador`, `es_cliente`, `rol_de`, decoradores `admin_required`,
  `cliente_required` y mixins `AdminRequiredMixin`, `ClienteRequiredMixin`.
- `apps/core/views_base.py`: `AdminListView`, `AdminCreateView`, `AdminUpdateView`,
  `AdminSoftDeleteView`, `AdminCapacidadUpdateView`.
- `apps/core/forms.py`: `BootstrapFormMixin`, `BootstrapForm`, `BootstrapModelForm`,
  `CapacidadFormMixin`.
- `apps/core/disponibilidad.py`: `guardar_con_capacidad`, `unidades_ocupadas`,
  `CapacidadInvalida`, `CapacidadPorDebajoDeOcupado`.
- `apps/core/templatetags/core_extras.py`: filtro `valor_de` para listados genéricos.
- Plantillas parciales: `_form.html`, `_messages.html`, `_navbar.html`,
  `_pagination.html`.

### 3.5 Flujo general de una petición

1. El navegador solicita una URL.
2. `LoginRequiredMiddleware` comprueba la sesión salvo que la vista esté marcada con
   `@public`/`login_not_required` o envuelta como `public(...)`.
3. Si la vista exige un rol, `AdminRequiredMixin`/`admin_required` (o equivalentes)
   redirige a login a los anónimos y devuelve **403** a los autenticados sin permiso.
4. La vista construye formularios con `request.POST`/`request.FILES`, valida y guarda.
5. Los modelos aplican restricciones y, cuando corresponde, servicios transaccionales
   (`guardar_con_capacidad`, revisión de documentos, cambio de correo).
6. La vista renderiza una plantilla con el contexto; los mensajes se muestran mediante
   `_messages.html`. La respuesta vuelve al navegador.

---

## 4. Actores, roles y permisos

### 4.1 Tipos de usuario y grupos

| Tipo | Cómo se determina | Permisos efectivos |
|---|---|---|
| Anónimo | `request.user.is_authenticated == False` | Solo rutas públicas: inicio, catálogos, detalle, comparador, registro, login, recuperación y reenvío de verificación |
| Cliente | Grupo `Cliente` | Rutas públicas + perfil + cambio de correo/contraseña; **no** accede a `/gestion/...` (403) |
| Administrador | Grupo `Administrador` **o** `is_superuser` | Rutas públicas + perfil + todo el panel `/gestion/...` de la aplicación |
| Superusuario | `is_superuser=True` | Además del panel de la aplicación, Django admin `/admin/`; requiere `is_staff` para entrar al admin |
| Proveedor | `Proveedor.usuario == request.user` | Perfil + portal `/proveedor/documentos/` limitado a sus propios documentos |

Matices verificados:

- El grupo `Administrador` **no** concede acceso a Django admin: no establece `is_staff`.
  Los tests confirman que un administrador de la aplicación recibe redirección en `/admin/`.
- Un superusuario es tratado como administrador por `es_administrador`, aunque no pertenezca
  al grupo. Si no tiene `Perfil`, `obtener_perfil` se lo crea con datos provisionales.
- Un usuario puede pertenecer a `Cliente` y estar vinculado a un proveedor; ambas cosas son
  independientes.
- No existe el rol "empleado" ni un grupo para proveedores.

### 4.2 Restricciones de acceso

- **Deny by default:** `LoginRequiredMiddleware` protege todas las vistas no marcadas como
  públicas.
- **Marcado de vistas públicas:** `@public` (alias de `login_not_required`) en funciones y
  `public(...)` al registrar vistas basadas en clases o funciones en `urls.py`.
- **Rol administrador:** `@admin_required` en funciones y `AdminRequiredMixin` en clases.
  Anónimo → redirección al login; autenticado sin rol → `PermissionDenied` (403).
- **Rol cliente:** `@cliente_required` y `ClienteRequiredMixin` existen, aunque en las rutas
  actuales el perfil solo exige autenticación (`@login_required`).
- **Propiedad de documentos:** el portal del proveedor comprueba `Proveedor.usuario`; la
  descarga compara `documento.proveedor.usuario_id` con el usuario y devuelve 404 a terceros.
- **Django admin:** solo superusuarios con `is_staff`.
- **Media privada:** en desarrollo, la ruta `^media/(?!proveedores/)` excluye expresamente
  `media/proveedores/`; esos archivos solo se sirven por `suppliers:documento_archivo`.

---

## 5. Módulos funcionales

### 5.1 `core`

- **Responsabilidad:** infraestructura compartida y portada.
- **Modelos:** ninguno.
- **Formularios:** mixins `BootstrapFormMixin`, `BootstrapModelForm`, `CapacidadFormMixin`.
- **Vistas:** `home` (pública); clases base administrativas sin modelo propio.
- **Rutas:** `/` (`core:home`).
- **Plantillas:** `core/home.html`, `core/crud_list.html`, `core/crud_form.html`,
  `core/crud_confirm_delete.html`, `base.html`, parciales.
- **Permisos:** `home` pública; las clases base se usan solo desde vistas administrativas.
- **Implementado:** control de acceso, CRUD genérico, estilos de formularios, servicio de
  capacidad y portada mínima con enlaces a catálogos. La portada tiene un `TODO` de contenido.
- **No implementado:** contenido destacado de la portada.

### 5.2 `accounts`

- **Responsabilidad:** identidad, cuentas, perfiles y roles.
- **Modelos:** `Perfil` (OneToOne con el `User` estándar de Django).
- **Relaciones:** `Perfil.usuario` → `auth.User`; `Perfil.nacionalidad` → `destinations.Pais`.
- **Formularios:** `LoginForm`, `RegistroForm`, `ReenviarActivacionForm`, `PerfilForm`,
  `CambioCorreoForm`, `CambiarPasswordForm`, `CambiarRolForm`.
- **Servicios:** `registrar_cliente`, `enviar_correo_activacion`, `solicitar_cambio_correo`,
  `confirmar_cambio_correo`, `obtener_perfil`.
- **Vistas y operaciones:**
  - registro, activación por enlace, reenvío de verificación;
  - login/logout (vistas nativas de Django con formulario propio);
  - recuperación de contraseña (vistas nativas);
  - perfil propio, cambio de correo con confirmación y cambio de contraseña;
  - listado/búsqueda de usuarios, bloqueo/activación y cambio de rol.
- **Rutas:** `/cuentas/...` (sección 9).
- **Plantillas:** `templates/accounts/` (registro, login, perfil, usuarios, recuperación,
  cambio de correo/contraseña y correos de texto).
- **Permisos:** registro/login/recuperación/activación públicas; perfil autenticado; gestión
  de usuarios solo administrador.
- **Implementado:** CU-01, CU-02, CU-03, CU-04, CU-05 y CU-06, con verificación de correo,
  tokens de un solo uso y pruebas de acceso.

### 5.3 `destinations`

- **Responsabilidad:** geografía turística y catálogo de destinos.
- **Modelos:** `Pais`, `Categoria`, `Destino`, `DestinoFoto`.
- **Relaciones:** `Destino.pais` y `Destino.categoria` (PROTECT); `DestinoFoto.destino`
  (CASCADE).
- **Formularios:** `DestinoForm`. No hay formulario/formset de fotos.
- **Vistas:** `CatalogoDestinosView`, `DetalleDestinoView`, `DestinoListaGestion`,
  `DestinoCrear`, `DestinoEditar`, `DestinoEliminar`.
- **Rutas:** `/destinos/`, `/destinos/<pk>/`, `/gestion/destinos/...`.
- **Plantillas:** `destinations/destino_list.html`, `destinations/destino_detail.html` y
  plantillas CRUD genéricas para la gestión.
- **Permisos:** catálogo y detalle públicos; gestión solo administrador.
- **Implementado:** CU-07 y la parte de CRUD de destinos de CU-08. El catálogo filtra por
  texto, país y categoría; el detalle muestra fotos y descripción.
- **Parcial:** la subida, ordenación y portada de fotos solo se puede hacer desde Django
  admin; no existe el formset de CU-08 en la interfaz propia. El detalle tiene un `TODO`
  para listar paquetes del destino.

### 5.4 `suppliers`

- **Responsabilidad:** proveedores y gestión documental privada.
- **Modelos:** `Proveedor`, `ProveedorDocumento`.
- **Relaciones:** `Proveedor.usuario` (OneToOne con `User`, SET_NULL);
  `ProveedorDocumento.proveedor` (CASCADE); `ProveedorDocumento.revisado_por` → `Perfil`
  (PROTECT).
- **Formularios:** `ProveedorForm`, `DocumentoProveedorForm`, `RevisionDocumentoForm`.
- **Servicios:** `revisar_documento` (transaccional y con bloqueo de fila).
- **Validadores:** `validar_archivo_documento`, `ruta_documento_proveedor`.
- **Vistas:** CRUD de proveedores; portal `mis_documentos`, `cargar_documento`,
  `nueva_version_documento`, `descargar_documento`; revisión `gestion_documentos`,
  `revisar_documento`.
- **Rutas:** `/proveedor/documentos/...` y `/gestion/proveedores/...`.
- **Plantillas:** `suppliers/mis_documentos.html`, `documento_form.html`,
  `gestion_documentos.html`, `documento_revisar.html`.
- **Permisos:** portal autenticado y vinculado a proveedor; revisión solo administrador;
  descarga solo propietario o administrador; gestión de proveedores solo administrador.
- **Implementado:** CU-13 completo (carga, consulta, descarga, revisión, rechazo con motivo,
  nueva versión e historial por filas). CU-17 **no** está implementado.

### 5.5 `hotels`

- **Responsabilidad:** hoteles, tipos de habitación, tarifas y disponibilidad de habitaciones.
- **Modelos:** `Hotel`, `TipoHabitacion`, `TarifaHabitacion`.
- **Relaciones:** `Hotel.proveedor` y `Hotel.destino` (PROTECT);
  `TipoHabitacion.hotel` (CASCADE); `TarifaHabitacion.tipo_habitacion` (CASCADE);
  `PaqueteHotel.tipo_habitacion` (PROTECT, desde `packages`).
- **Formularios:** `HotelForm`, `TipoHabitacionForm`, `TarifaHabitacionForm`.
- **Vistas:** CRUD de hoteles; tipos anidados por `hotel_pk`; tarifas anidadas por
  `hotel_pk`/`tipo_pk`.
- **Rutas:** `/gestion/hoteles/...`.
- **Plantillas:** `hotels/tipo_habitacion_list.html`, `tipo_habitacion_form.html`,
  `tipo_habitacion_confirm_delete.html`, `tarifa_list.html`, `tarifa_form.html`,
  `tarifa_confirm_delete.html`; hoteles usan las CRUD genéricas.
- **Permisos:** solo administrador.
- **Implementado:** CU-14 y la parte de CU-16 correspondiente a habitaciones. Incluye
  validación de solapamiento de tarifas y protección de tipos usados por paquetes.

### 5.6 `flights`

- **Responsabilidad:** vuelos y disponibilidad de asientos.
- **Modelos:** `Vuelo`.
- **Relaciones:** `Vuelo.proveedor` (PROTECT); `Vuelo.origen` y `Vuelo.destino` →
  `Destino` (PROTECT, `related_name` distintos); `PaqueteVuelo.vuelo` (PROTECT).
- **Formularios:** `VueloForm`.
- **Vistas:** `VueloLista`, `VueloCrear`, `VueloEditar`, `VueloEliminar` (cancelación
  lógica).
- **Rutas:** `/gestion/vuelos/...`.
- **Plantillas:** CRUD genéricas.
- **Permisos:** solo administrador.
- **Implementado:** CU-15 y la parte de CU-16 correspondiente a asientos.

### 5.7 `packages`

- **Responsabilidad:** paquetes turísticos, sus componentes, catálogo público, detalle,
  comparador y gestión.
- **Modelos:** `Paquete`, `PaqueteHotel`, `PaqueteVuelo`, `PaqueteServicio`,
  `PaqueteActividad`, `Servicio`.
- **Relaciones:** `Paquete.destino` (PROTECT); componentes con CASCADE hacia `Paquete` y
  PROTECT hacia hotel/vuelo/servicio; actividades CASCADE.
- **Formularios:** `FiltroCatalogoForm`, `PaqueteForm`, formularios de componentes,
  formsets inline (`PaqueteHotelInlineFormSet`, `PaqueteVueloInlineFormSet`,
  `PaqueteServicioInlineFormSet`, `PaqueteActividadInlineFormSet`).
- **Vistas:** `CatalogoPaquetesView`, `DetallePaqueteView`, `comparar_paquetes`,
  `PaqueteLista`, `PaqueteCrear`, `PaqueteEditar`, `PaqueteEliminar`.
- **Rutas:** `/paquetes/...` y `/gestion/paquetes/...`.
- **Plantillas:** `packages/paquete_list.html`, `paquete_detail.html`,
  `paquete_compare.html`, `paquete_form.html`, `_formset.html`.
- **Permisos:** catálogo, detalle y comparador públicos; gestión solo administrador.
- **Implementado:** CU-09 (catálogo y filtros validados), CU-10 (comparador limitado a tres),
  CU-11 (detalle) y CU-12 (gestión con cuatro formsets), más la parte de CU-16 de cupos.
- **No implementado:** reserva desde el detalle, PDF de itinerario y cualquier pago.

---

## 6. Modelo de datos

### 6.1 Convenciones generales

- Todos los modelos usan **`BigAutoField`** como clave primaria implícita (columna `id`,
  BIGINT).
- Las tablas se declaran en singular con `db_table` explícito y nombres en español
  `snake_case`.
- Los importes monetarios usan `DecimalField`: `max_digits=12, decimal_places=2` en
  `Paquete.precio_persona`; `max_digits=10, decimal_places=2` en tarifas y vuelos.
- Los estados fijos se modelan con `TextChoices` y `CharField`; no hay tablas de estados.
- El borrado de catálogos con historial es lógico (`activo=False`, `estado="archivado"` o
  `estado="cancelado"`), no físico.

### 6.2 Modelos de `accounts`

#### `Perfil` — tabla `perfil`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `usuario` | OneToOneField → `auth.User` | `on_delete=CASCADE`, `related_name="perfil"`, `db_column="usuario_id"` |
| `nombres` | CharField(80) | Obligatorio |
| `apellidos` | CharField(80) | Obligatorio |
| `tipo_documento` | CharField(10) | Choices: `CI`, `PASAPORTE`, `CE`; default `CI` |
| `nro_documento` | CharField(20) | Obligatorio |
| `fecha_nacimiento` | DateField | `null=True`, `blank=True` |
| `telefono` | CharField(20) | `blank=True` |
| `direccion` | CharField(200) | `blank=True` |
| `nacionalidad` | ForeignKey → `Pais` | `on_delete=PROTECT`, `null=True`, `blank=True`, `db_column="nacionalidad_id"` |
| `nit` | CharField(20) | `blank=True` |
| `razon_social` | CharField(150) | `blank=True` |
| `correo_pendiente` | EmailField | `null=True`, `blank=True`; correo en espera de confirmación |
| `correo_pendiente_nonce` | CharField(64) | `blank=True`, default `""`; invalida enlaces anteriores |
| `fecha_registro` | DateTimeField | `auto_now_add=True` |

Restricción: `UniqueConstraint(tipo_documento, nro_documento)` → `uq_perfil_documento`.
Propiedad: `nombre_completo`.

#### Modelo de usuario

No hay modelo de usuario propio. Se usa `django.contrib.auth.models.User` con correo en
`username` y en `email`. Los roles se representan con `auth.Group` (`Administrador`,
`Cliente`). El bloqueo de cuenta es `User.is_active=False`.

### 6.3 Modelos de `destinations`

#### `Pais` — tabla `pais`

`id` (PK), `codigo_iso` CharField(2) **unique**, `nombre` CharField(80) **unique**.
Ordering: `nombre`.

#### `Categoria` — tabla `categoria`

`id` (PK), `nombre` CharField(50) **unique**, `descripcion` CharField(200) `blank=True`.
Ordering: `nombre`.

#### `Destino` — tabla `destino`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `pais` | ForeignKey → `Pais` | `PROTECT`, `related_name="destinos"` |
| `categoria` | ForeignKey → `Categoria` | `PROTECT`, `related_name="destinos"` |
| `nombre` | CharField(100) | Obligatorio |
| `codigo_iata` | CharField(3) | **unique**, `null=True`, `blank=True` |
| `descripcion` | TextField | `blank=True` |
| `activo` | BooleanField | default `True`; el "borrado" lo desactiva |

Restricción: `UniqueConstraint(pais, nombre)` → `uq_destino_pais_nombre`.
Propiedades: `es_internacional` (país distinto de `BO`), `portada` (primera foto marcada como
portada o la primera foto).

#### `DestinoFoto` — tabla `destino_foto`

`id` (PK), `destino` ForeignKey → `Destino` (`CASCADE`, `related_name="fotos"`),
`archivo` ImageField (`upload_to="destinos/"`), `descripcion` CharField(200) `blank=True`,
`orden` SmallIntegerField default 0, `es_portada` BooleanField default `False`.
Restricción condicional: una sola portada por destino
(`UniqueConstraint(destino, condition=es_portada=True)` → `uq_destino_foto_portada`).
Ordering: `orden`, `id`.

### 6.4 Modelos de `suppliers`

#### `Proveedor` — tabla `proveedor`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `razon_social` | CharField(150) | Obligatorio |
| `nit` | CharField(20) | **unique** |
| `tipo` | CharField(15) | Choices: `aerolinea`, `hotel`, `operador`, `transporte`, `otro` |
| `nombre_contacto` | CharField(100) | `blank=True` |
| `correo` | EmailField(120) | `blank=True` |
| `telefono` | CharField(20) | `blank=True` |
| `estado_validacion` | CharField(10) | Choices: `pendiente`, `validado`, `rechazado`; default `pendiente` |
| `activo` | BooleanField | default `True` |
| `usuario` | OneToOneField → `auth.User` | `on_delete=SET_NULL`, `null=True`, `blank=True`, `related_name="proveedor"` |

Ordering: `razon_social`.

#### `ProveedorDocumento` — tabla `proveedor_documento`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `proveedor` | ForeignKey → `Proveedor` | `CASCADE`, `related_name="documentos"` |
| `tipo_documento` | CharField(50) | Texto libre (NIT, licencia, contrato...) |
| `archivo` | FileField | `upload_to=ruta_documento_proveedor`, validador `validar_archivo_documento` |
| `fecha_vencimiento` | DateField | `null=True`, `blank=True` |
| `estado` | CharField(10) | Choices: `pendiente`, `aprobado`, `rechazado`; default `pendiente` |
| `observacion` | CharField(250) | `blank=True`; motivo/observación de revisión |
| `revisado_por` | ForeignKey → `accounts.Perfil` | `PROTECT`, `null=True`, `blank=True`, `db_column="revisado_por_id"` |
| `fecha_carga` | DateTimeField | `auto_now_add=True` |
| `fecha_revision` | DateTimeField | `null=True`, `blank=True` |

No existe una FK de versión anterior/siguiente: una "nueva versión" es una fila nueva con el
mismo proveedor y tipo de documento; el historial se obtiene listando las filas.

### 6.5 Modelos de `hotels`

#### `Hotel` — tabla `hotel`

`id` (PK); `proveedor` ForeignKey → `Proveedor` (`PROTECT`, `related_name="hoteles"`);
`destino` ForeignKey → `Destino` (`PROTECT`, `related_name="hoteles"`); `nombre`
CharField(120); `estrellas` SmallIntegerField; `direccion` CharField(200) `blank=True`;
`descripcion` TextField `blank=True`; `activo` BooleanField default `True`.
Restricción: `estrellas` entre 1 y 5 (`ck_hotel_estrellas`). Ordering: `nombre`.

#### `TipoHabitacion` — tabla `tipo_habitacion`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `hotel` | ForeignKey → `Hotel` | `CASCADE`, `related_name="tipos_habitacion"` |
| `nombre` | CharField(60) | Simple, Doble, Suite... |
| `capacidad` | SmallIntegerField | Personas por habitación |
| `habitaciones_total` | IntegerField | Capacidad total |
| `habitaciones_disponibles` | IntegerField | Disponibilidad actual |
| `descripcion` | CharField(250) | `blank=True` |

Restricciones: `UniqueConstraint(hotel, nombre)` → `uq_tipo_habitacion_hotel`;
`CheckConstraint(0 <= habitaciones_disponibles <= habitaciones_total)` →
`ck_habitaciones_disponibles`.
Propiedad: `habitaciones_ocupadas = total - disponibles`.

#### `TarifaHabitacion` — tabla `tarifa_habitacion`

`id` (PK); `tipo_habitacion` ForeignKey → `TipoHabitacion` (`CASCADE`,
`related_name="tarifas"`); `fecha_inicio` DateField; `fecha_fin` DateField;
`precio_noche` DecimalField(10,2).
Restricciones: `UniqueConstraint(tipo_habitacion, fecha_inicio)` → `uq_tarifa_inicio`;
`CheckConstraint(fecha_fin >= fecha_inicio)` → `ck_tarifa_fechas`.
El solapamiento de rangos se valida en el formulario, no con una restricción de exclusión
de PostgreSQL.

### 6.6 Modelo de `flights`

#### `Vuelo` — tabla `vuelo`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `proveedor` | ForeignKey → `Proveedor` | `PROTECT`, `related_name="vuelos"` |
| `numero_vuelo` | CharField(10) | Obligatorio |
| `origen` | ForeignKey → `Destino` | `PROTECT`, `related_name="vuelos_salida"` |
| `destino` | ForeignKey → `Destino` | `PROTECT`, `related_name="vuelos_llegada"` |
| `fecha_salida` | DateTimeField | Obligatorio |
| `fecha_llegada` | DateTimeField | Obligatorio |
| `asientos_total` | IntegerField | Capacidad total |
| `asientos_disponibles` | IntegerField | Disponibilidad actual |
| `precio_referencial` | DecimalField(10,2) | Precio de referencia |
| `estado` | CharField(12) | Choices: `programado`, `retrasado`, `cancelado`, `completado`; default `programado` |

Restricciones: `UniqueConstraint(numero_vuelo, fecha_salida)` → `uq_vuelo_numero_fecha`;
`origen != destino` → `ck_vuelo_origen_destino`; `fecha_llegada > fecha_salida` →
`ck_vuelo_fechas`; `0 <= asientos_disponibles <= asientos_total` → `ck_vuelo_asientos`.
Propiedad: `asientos_ocupados = total - disponibles`. Ordering: `fecha_salida`.

### 6.7 Modelos de `packages`

#### `Servicio` — tabla `servicio`

`id` (PK); `nombre` CharField(80) **unique**; `descripcion` CharField(200) `blank=True`.
Ordering: `nombre`.

#### `Paquete` — tabla `paquete`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigAutoField | PK |
| `destino` | ForeignKey → `Destino` | `PROTECT`, `related_name="paquetes"` |
| `nombre` | CharField(150) | Obligatorio |
| `descripcion` | TextField | `blank=True` |
| `condiciones` | TextField | `blank=True` |
| `fecha_salida` | DateField | Fecha concreta de la salida |
| `fecha_retorno` | DateField | Debe ser >= `fecha_salida` |
| `precio_persona` | DecimalField(12,2) | Debe ser > 0 |
| `cupos_total` | IntegerField | Capacidad total |
| `cupos_disponibles` | IntegerField | Disponibilidad actual |
| `venta_desde` | DateField | Inicio de vigencia de venta |
| `venta_hasta` | DateField | Fin de vigencia; debe ser <= `fecha_salida` |
| `estado` | CharField(10) | Choices: `borrador`, `publicado`, `archivado`; default `borrador` |

Restricciones:
`fecha_retorno >= fecha_salida` → `ck_paquete_fechas`;
`venta_desde <= venta_hasta <= fecha_salida` → `ck_paquete_venta`;
`0 <= cupos_disponibles <= cupos_total` → `ck_paquete_cupos`;
`precio_persona > 0` → `ck_paquete_precio`.
Ordering: `fecha_salida`.
En `save()`, si es una instancia nueva y `cupos_disponibles` es `None`, se iguala a
`cupos_total`.
Propiedades: `duracion_dias` (`fecha_retorno - fecha_salida + 1`), `cupos_ocupados`
(`total - disponibles`).

#### `PaqueteHotel` — tabla `paquete_hotel`

`id` (PK); `paquete` ForeignKey → `Paquete` (`CASCADE`); `tipo_habitacion` ForeignKey →
`TipoHabitacion` (`PROTECT`); `noches` SmallIntegerField.
`UniqueConstraint(paquete, tipo_habitacion)` → `uq_paquete_hotel`.

#### `PaqueteVuelo` — tabla `paquete_vuelo`

`id` (PK); `paquete` ForeignKey → `Paquete` (`CASCADE`); `vuelo` ForeignKey → `Vuelo`
(`PROTECT`); `tramo` CharField(10) con choices `ida`, `vuelta`, `interno` (default `ida`).
`UniqueConstraint(paquete, vuelo)` → `uq_paquete_vuelo`.

#### `PaqueteServicio` — tabla `paquete_servicio`

`id` (PK); `paquete` ForeignKey → `Paquete` (`CASCADE`); `servicio` ForeignKey → `Servicio`
(`PROTECT`); `detalle` CharField(200) `blank=True`.
`UniqueConstraint(paquete, servicio)` → `uq_paquete_servicio`.

#### `PaqueteActividad` — tabla `paquete_actividad`

`id` (PK); `paquete` ForeignKey → `Paquete` (`CASCADE`, `related_name="actividades"`);
`dia` SmallIntegerField; `orden` SmallIntegerField default 1; `hora_inicio` TimeField
`null=True`, `blank=True`; `titulo` CharField(120); `descripcion` CharField(300)
`blank=True`.
`UniqueConstraint(paquete, dia, orden)` → `uq_paquete_actividad`.
Ordering: `dia`, `orden`.

### 6.8 Relaciones globales del sistema

| Origen | Relación | Destino | Cardinalidad | `on_delete` |
|---|---|---|---|---|
| `Perfil.usuario` | OneToOne | `auth.User` | 1 Perfil ↔ 1 User | CASCADE |
| `Perfil.nacionalidad` | ForeignKey | `Pais` | N Perfiles → 1 País (opcional) | PROTECT |
| `Proveedor.usuario` | OneToOne | `auth.User` | 0..1 Proveedor ↔ 0..1 User (opcional) | SET_NULL |
| `ProveedorDocumento.proveedor` | ForeignKey | `Proveedor` | N Documentos → 1 Proveedor | CASCADE |
| `ProveedorDocumento.revisado_por` | ForeignKey | `Perfil` | N Documentos → 1 Perfil revisor (opcional) | PROTECT |
| `Destino.pais` | ForeignKey | `Pais` | N Destinos → 1 País | PROTECT |
| `Destino.categoria` | ForeignKey | `Categoria` | N Destinos → 1 Categoría | PROTECT |
| `DestinoFoto.destino` | ForeignKey | `Destino` | N Fotos → 1 Destino | CASCADE |
| `Hotel.proveedor` | ForeignKey | `Proveedor` | N Hoteles → 1 Proveedor | PROTECT |
| `Hotel.destino` | ForeignKey | `Destino` | N Hoteles → 1 Destino | PROTECT |
| `TipoHabitacion.hotel` | ForeignKey | `Hotel` | N Tipos → 1 Hotel | CASCADE |
| `TarifaHabitacion.tipo_habitacion` | ForeignKey | `TipoHabitacion` | N Tarifas → 1 Tipo | CASCADE |
| `Vuelo.proveedor` | ForeignKey | `Proveedor` | N Vuelos → 1 Proveedor | PROTECT |
| `Vuelo.origen` | ForeignKey | `Destino` | N Vuelos → 1 Destino de salida | PROTECT |
| `Vuelo.destino` | ForeignKey | `Destino` | N Vuelos → 1 Destino de llegada | PROTECT |
| `Paquete.destino` | ForeignKey | `Destino` | N Paquetes → 1 Destino | PROTECT |
| `PaqueteHotel.paquete` | ForeignKey | `Paquete` | N Componentes → 1 Paquete | CASCADE |
| `PaqueteHotel.tipo_habitacion` | ForeignKey | `TipoHabitacion` | N Componentes → 1 Tipo | PROTECT |
| `PaqueteVuelo.paquete` | ForeignKey | `Paquete` | N Componentes → 1 Paquete | CASCADE |
| `PaqueteVuelo.vuelo` | ForeignKey | `Vuelo` | N Componentes → 1 Vuelo | PROTECT |
| `PaqueteServicio.paquete` | ForeignKey | `Paquete` | N Componentes → 1 Paquete | CASCADE |
| `PaqueteServicio.servicio` | ForeignKey | `Servicio` | N Componentes → 1 Servicio | PROTECT |
| `PaqueteActividad.paquete` | ForeignKey | `Paquete` | N Actividades → 1 Paquete | CASCADE |

Relaciones muchos-a-muchos implementadas mediante tablas intermedias:

- `Paquete` ↔ `TipoHabitacion` a través de `PaqueteHotel` (M:N; único por pareja).
- `Paquete` ↔ `Vuelo` a través de `PaqueteVuelo` (M:N; único por pareja).
- `Paquete` ↔ `Servicio` a través de `PaqueteServicio` (M:N; único por pareja).

**Relaciones que NO existen** (no deben inventarse en un diagrama):

- No hay `Reserva`, `Pasajero`, `Pago`, `Factura`, `Promocion`, `Resena`, `Notificacion`,
  `ConsultaSoporte`, `ConfirmacionProveedor` ni `CierreCaja` como modelos Django.
- No hay relación directa entre `TarifaHabitacion` y `Paquete`; el precio del paquete es un
  campo independiente.
- No hay FK de versión entre documentos de proveedor.
- No hay relación entre `Hotel` y `Paquete` distinta de la que se establece a través de
  `TipoHabitacion` y `PaqueteHotel`.
- No hay modelo de empleado ni de rol distinto de los grupos de Django.
- No hay FK de `Perfil` a `Proveedor`; la vinculación es `Proveedor.usuario`.

### 6.9 Diagrama entidad-relación: resumen de entidades

Entidades con PK `id`: `perfil`, `pais`, `categoria`, `destino`, `destino_foto`,
`proveedor`, `proveedor_documento`, `hotel`, `tipo_habitacion`, `tarifa_habitacion`,
`vuelo`, `paquete`, `paquete_hotel`, `paquete_vuelo`, `paquete_servicio`,
`paquete_actividad`, `servicio`.

Entidades externas de Django que participan: `auth_user`, `auth_group`,
`auth_user_groups` (tablas gestionadas por Django).

---

## 7. Casos de uso y funcionalidades por sprint

### 7.1 Sprint 1

| CU | Nombre | Actor | Estado | Módulos/modelos |
|---|---|---|---|---|
| CU-01 | Registro y activación de cuenta | Visitante | Implementado | `accounts`; `User`, `Perfil`, `Group` |
| CU-02 | Inicio de sesión | Visitante/Usuario | Implementado | `accounts`; `User` |
| CU-03 | Recuperación de contraseña | Visitante | Implementado | `accounts`; vistas nativas de Django |
| CU-04 | Cierre de sesión | Usuario autenticado | Implementado | `accounts`; `LogoutView` |
| CU-05 | Gestión de perfil, correo y contraseña | Cliente/Administrador | Implementado | `accounts`; `Perfil`, `User` |
| CU-06 | Gestión de usuarios y roles | Administrador | Implementado | `accounts`; `User`, `Group`, `Perfil` |
| CU-07 | Catálogo de destinos | Visitante | Implementado | `destinations`; `Destino`, `Pais`, `Categoria` |
| CU-08 | Gestión de destinos y fotos | Administrador | Parcial | `destinations`; `Destino`, `DestinoFoto` |

**CU-01 — Registro y activación**
- *Actor:* visitante.
- *Objetivo:* crear una cuenta de cliente verificada.
- *Precondiciones:* no tener sesión iniciada; correo y documento no registrados.
- *Flujo principal:* completar `RegistroForm` → validar correo/documento/contraseñas →
  crear `User` inactivo, `Perfil` y rol `Cliente` en una transacción → enviar correo con
  enlace `uidb64`/token → el usuario abre el enlace → `is_active=True` → iniciar sesión.
- *Resultado:* cuenta activa con perfil y rol.
- *Módulos/modelos:* `accounts`, `User`, `Perfil`, `Group`.

**CU-02 — Inicio de sesión**
- *Actor:* visitante o usuario registrado.
- *Objetivo:* abrir una sesión autenticada.
- *Precondiciones:* cuenta existente y activa.
- *Flujo principal:* introducir correo o usuario y contraseña → `LoginForm` resuelve el
  identificador sin distinguir mayúsculas → `AuthenticationForm` valida credenciales y
  estado activo → redirección a `next` o al inicio.
- *Resultado:* sesión iniciada; cookie de sesión.
- *Módulos/modelos:* `accounts`, `User`.

**CU-03 — Recuperación de contraseña**
- *Actor:* visitante.
- *Objetivo:* establecer una nueva contraseña sin conocer la anterior.
- *Precondiciones:* disponer de acceso al correo registrado.
- *Flujo principal:* solicitar recuperación → Django envía enlace con token → abrir enlace →
  introducir nueva contraseña sujeta a validadores → confirmar.
- *Resultado:* contraseña actualizada; el enlace caduca a los 3 días por configuración.
- *Módulos/modelos:* `accounts`; vistas nativas `PasswordReset*`.

**CU-04 — Cierre de sesión**
- *Actor:* usuario autenticado.
- *Objetivo:* finalizar la sesión.
- *Flujo principal:* enviar POST al logout (el GET devuelve 405) → Django invalida la sesión.
- *Resultado:* usuario anónimo; redirección al inicio.

**CU-05 — Gestión de perfil**
- *Actor:* cliente o administrador autenticado.
- *Objetivo:* mantener los datos personales y la seguridad de la cuenta.
- *Flujo principal:* abrir `/cuentas/perfil/` → editar datos → guardar; desde allí puede
  cambiar correo (con confirmación) o contraseña (con contraseña actual y validadores).
- *Resultado:* perfil actualizado; correo o contraseña cambiados solo tras validación.
- *Módulos/modelos:* `accounts`; `Perfil`, `User`.

**CU-06 — Gestión de usuarios**
- *Actor:* administrador.
- *Objetivo:* consultar cuentas, bloquear/activar y asignar roles.
- *Flujo principal:* listar/buscar usuarios → elegir bloquear/activar o rol → POST con CSRF.
- *Resultado:* `is_active` o grupo modificado; no puede bloquearse ni cambiarse el rol a sí
  mismo.
- *Módulos/modelos:* `accounts`; `User`, `Group`, `Perfil`.

**CU-07 — Catálogo de destinos**
- *Actor:* visitante.
- *Objetivo:* explorar destinos activos.
- *Flujo principal:* listar destinos activos → filtrar por texto, país o categoría → abrir
  detalle con fotos y descripción.
- *Resultado:* destinos coincidentes y detalle visible.
- *Módulos/modelos:* `destinations`; `Destino`, `Pais`, `Categoria`, `DestinoFoto`.

**CU-08 — Gestión de destinos y fotos (parcial)**
- *Actor:* administrador.
- *Objetivo:* mantener destinos y su material fotográfico.
- *Flujo principal implementado:* CRUD de destinos con formulario; eliminar desactiva.
- *Parte no implementada:* formset para subir, ordenar y elegir portada desde la interfaz
  propia. `DestinoFoto` existe y está registrado en Django admin.
- *Resultado:* destinos gestionados; fotos administrables solo desde Django admin.
- *Módulos/modelos:* `destinations`; `Destino`, `DestinoFoto`.

### 7.2 Sprint 2

| CU | Nombre | Actor | Estado | Módulos/modelos |
|---|---|---|---|---|
| CU-09 | Catálogo y filtros de paquetes | Visitante | Implementado | `packages`; `Paquete`, `Destino` |
| CU-10 | Comparador de paquetes | Visitante | Implementado | `packages`; `Paquete` |
| CU-11 | Detalle de paquete | Visitante | Implementado | `packages`; `Paquete` y componentes |
| CU-12 | Gestión de paquetes y componentes | Administrador | Implementado | `packages`; `Paquete`, componentes |
| CU-13 | Documentos de proveedores | Proveedor/Administrador | Implementado | `suppliers`; `Proveedor`, `ProveedorDocumento` |
| CU-14 | Hoteles, habitaciones y tarifas | Administrador | Implementado | `hotels`; `Hotel`, `TipoHabitacion`, `TarifaHabitacion` |
| CU-15 | Gestión de vuelos | Administrador | Implementado | `flights`; `Vuelo` |
| CU-16 | Gestión de disponibilidad | Administrador | Implementado | `core`, `hotels`, `flights`, `packages` |

**CU-09 — Catálogo y filtros de paquetes**
- *Actor:* visitante.
- *Objetivo:* encontrar paquetes publicados y vigentes.
- *Precondiciones:* el paquete está `publicado`, la fecha actual está dentro de
  `venta_desde`..`venta_hasta` y se muestra en el catálogo.
- *Flujo principal:* abrir `/paquetes/` → aplicar búsqueda y filtros de destino, precio mínimo,
  precio máximo, salida desde y salida hasta → `FiltroCatalogoForm` valida → se consulta el
  ORM. Si algún filtro es inválido, se ignoran todos los filtros y se muestra un aviso.
- *Resultado:* listado filtrado o listado completo con errores visibles; nunca HTTP 500 por
  parámetros manipulados.
- *Módulos/modelos:* `packages`; `Paquete`, `Destino`.

**CU-10 — Comparador de paquetes**
- *Actor:* visitante.
- *Objetivo:* comparar hasta tres paquetes.
- *Precondiciones:* existen paquetes publicados y vigentes.
- *Flujo principal:* marcar casillas en el catálogo (JavaScript impide la cuarta y conserva
  selecciones en `sessionStorage`) → enviar `ids` al comparador → el servidor deduplica,
  rechaza identificadores no numéricos y rechaza más de tres → consulta paquetes publicados.
- *Resultado:* tabla comparativa con uno, dos o tres paquetes; mensaje claro si se supera el
  límite o hay identificadores inválidos.
- *Módulos/modelos:* `packages`; `Paquete`, servicios del paquete.

**CU-11 — Detalle de paquete**
- *Actor:* visitante.
- *Objetivo:* consultar la información completa de un paquete publicado.
- *Precondiciones:* el paquete está publicado y vigente.
- *Flujo principal:* abrir `/paquetes/<pk>/` → mostrar destino, fechas, precio, cupos,
  descripción, servicios, itinerario y condiciones.
- *Resultado:* ficha informativa; no hay botón de reserva implementado.
- *Módulos/modelos:* `packages`; `Paquete`, `PaqueteServicio`, `PaqueteActividad`.

**CU-12 — Gestión de paquetes y componentes**
- *Actor:* administrador.
- *Objetivo:* crear, editar y archivar paquetes con hoteles, vuelos, servicios y actividades.
- *Precondiciones:* existen destinos, tipos de habitación, vuelos y servicios según lo que se
  quiera asociar.
- *Flujo principal:* abrir formulario → completar datos y cuatro formsets → validar todos →
  guardar en una transacción → recalcular cupos si se editó el total; eliminar componentes
  marcando `DELETE`; archivar el paquete si se "elimina".
- *Resultado:* paquete y componentes persistidos sin registros parciales.
- *Módulos/modelos:* `packages`; `Paquete`, `PaqueteHotel`, `PaqueteVuelo`,
  `PaqueteServicio`, `PaqueteActividad`.

**CU-13 — Documentos de proveedores**
- *Actor:* proveedor (carga/consulta) y administrador (revisión).
- *Objetivo:* validar la documentación de los proveedores y mantenerla privada.
- *Precondiciones:* el usuario está vinculado a un `Proveedor`; para revisar, es
  administrador.
- *Flujo principal:* el proveedor carga PDF/JPG/PNG → validación de tamaño, extensión,
  firma y nombre → queda pendiente → el administrador aprueba o rechaza con motivo → el
  proveedor consulta el estado y puede cargar una nueva versión tras la revisión.
- *Resultado:* documento con estado y revisor; archivo accesible solo por propietario o
  administrador.
- *Módulos/modelos:* `suppliers`; `Proveedor`, `ProveedorDocumento`, `Perfil`.

**CU-14 — Hoteles, habitaciones y tarifas**
- *Actor:* administrador.
- *Objetivo:* mantener la oferta hotelera y sus precios por temporada.
- *Precondiciones:* existe un proveedor y un destino para el hotel.
- *Flujo principal:* CRUD de hotel → gestionar tipos de habitación → definir tarifas con
  rango de fechas y precio → validar solapamientos y fechas.
- *Resultado:* hotel con tipos y tarifas; no se elimina un tipo referenciado por un paquete.
- *Módulos/modelos:* `hotels`; `Hotel`, `TipoHabitacion`, `TarifaHabitacion`.

**CU-15 — Gestión de vuelos**
- *Actor:* administrador.
- *Objetivo:* mantener vuelos y su disponibilidad.
- *Precondiciones:* existen proveedor y destinos.
- *Flujo principal:* CRUD de vuelo → validar fechas, origen distinto de destino y asientos →
  "eliminar" marca el vuelo como cancelado.
- *Resultado:* vuelo disponible para asignarlo a paquetes.
- *Módulos/modelos:* `flights`; `Vuelo`.

**CU-16 — Gestión de disponibilidad**
- *Actor:* administrador.
- *Objetivo:* cambiar capacidades totales sin perder lo ya ocupado.
- *Precondiciones:* recurso existente (tipo de habitación, vuelo o paquete).
- *Flujo principal:* editar solo el total → el formulario calcula lo ocupado como
  `total - disponible` → `guardar_con_capacidad` relee la fila con bloqueo, valida que el
  nuevo total no sea menor que lo ocupado y recalcula la disponibilidad → guardar.
- *Resultado:* nuevo total y disponibilidad coherente; error comprensible ante una carrera.
- *Módulos/modelos:* `core/disponibilidad`, `hotels`, `flights`, `packages`;
  `TipoHabitacion`, `Vuelo`, `Paquete`.

### 7.3 Sprint 3 y posteriores

**No implementado en este repositorio.** El esquema de referencia define lo siguiente, pero
no existen modelos, migraciones, rutas, formularios, plantillas ni pruebas en Django:

| Elemento del esquema | Sprint/CU de referencia | Estado |
|---|---|---|
| `confirmacion_proveedor` (CU-17) | Sprint 3 | No implementado; depende de `Reserva` |
| `reserva` | Sprint 3 (CU-18 a CU-25) | No implementado |
| `pasajero` | Sprint 3 | No implementado |
| `documento_viaje` | Sprint 3 (CU-24) | No implementado |
| `promocion` | Sprint 6 (CU-50) | No implementado |
| `cierre_caja`, `cuota`, `pago`, `reembolso`, `factura`, `pago_proveedor` | Sprint 4 (CU-26 a CU-37) | No implementado |
| `consulta_soporte`, `resena`, `notificacion`, `parametro_sistema` | Sprints 5 y 6 | No implementado |
| Funciones `fn_ajustar_cupos`, `fn_penalidad_cancelacion`, `fn_cerrar_caja` | Sprints 3–4 | No implementado |
| Trigger `trg_reserva_cupos` | Sprint 3 | No implementado |
| Vistas `v_saldo_reserva`, `v_reporte_ventas` | Sprints 4–5 | No implementado |

Dependencias técnicas existentes que permitirán conectar el Sprint 3: `Perfil` (cliente),
`Paquete` (con cupos), `TipoHabitacion` y `Vuelo` (con disponibilidad), `Proveedor` y
`ProveedorDocumento`, y el servicio `guardar_con_capacidad` como antecedente de control de
capacidad. **CU-17 no debe describirse como implementado.**

---

## 8. Flujos funcionales importantes

### 8.1 Registro y activación de usuario

1. El visitante entra en `/cuentas/registro/` y completa nombres, apellidos, correo, tipo y
   número de documento, teléfono opcional y contraseña repetida.
2. `RegistroForm` normaliza el correo a minúsculas y rechaza correos ya usados (comparando
   `username` y `email` sin distinguir mayúsculas) y documentos duplicados.
3. `password_validation.validate_password` aplica los validadores configurados (longitud
   mínima 8, similitud con datos del usuario, contraseña común y numérica).
4. `registrar_cliente` abre una transacción y crea: `User` con `username=email`,
   `email=email`, `is_active=False`; `Perfil`; y lo añade al grupo `Cliente`.
5. Al confirmar la transacción (`transaction.on_commit`) se envía un correo con enlace
   `uidb64` y token de activación.
6. El usuario abre el enlace; `activar` valida el token, marca `is_active=True` y redirige
   al login. El token incluye `is_active`, por lo que deja de ser válido tras el primer uso.
7. Si el enlace falla o caduca, se muestra `accounts/activacion_fallida.html` con estado 400.

### 8.2 Inicio de sesión

1. El usuario entra en `/cuentas/ingresar/`.
2. `LoginForm.clean` busca un usuario por `username` o `email` sin distinguir mayúsculas y
   reemplaza el identificador por el `username` real.
3. `AuthenticationForm` comprueba credenciales y que la cuenta esté activa.
4. Si es correcto, se crea la sesión y se redirige a `next` o a `core:home`; si la cuenta
   está inactiva/bloqueada, se muestra el mensaje correspondiente sin iniciar sesión.

### 8.3 Recuperación y cambio de contraseña

**Recuperación (olvidé mi contraseña):** formulario de correo → Django genera token y envía
el enlace → el usuario abre el enlace → formulario de nueva contraseña → validadores →
confirmación → enlace marcado como usado.

**Cambio con sesión iniciada:** `/cuentas/perfil/contrasena/` usa `PasswordChangeView`:
exige contraseña actual, valida la nueva con los validadores, la guarda y conserva la sesión
mediante `update_session_auth_hash()`.

### 8.4 Cambio y confirmación de correo

1. El usuario autenticado entra en `/cuentas/perfil/correo/`.
2. `CambioCorreoForm` valida que el correo no sea el actual y que no pertenezca a otra
   cuenta (sin revelar a quién pertenece).
3. `solicitar_cambio_correo` bloquea el perfil, guarda `correo_pendiente`, genera un nonce
   nuevo y envía el enlace al **nuevo** correo. El `email`/`username` actuales no cambian.
4. El usuario abre el enlace; `confirmar_cambio_correo` exige que la sesión corresponda al
   mismo usuario y valida el token.
5. Si el token es válido, el correo pendiente no está ocupado y no hay error de integridad,
   se actualizan `email` y `username` en una transacción y se limpia el pendiente/nonce.
6. Cualquier enlace anterior queda invalidado por el nonce. Token inválido, caducado, ya
   usado o correo ocupado devuelve la plantilla de error con estado 400.

### 8.5 Gestión de perfil

1. Cualquier usuario autenticado abre `/cuentas/perfil/`.
2. `obtener_perfil` devuelve su `Perfil` o lo crea si no existe (caso de superusuarios).
3. `PerfilForm` permite editar nombres, apellidos, documento, nacimiento, contacto,
   nacionalidad y datos fiscales. La fecha de nacimiento no puede ser futura y el documento
   no puede duplicar el de otro perfil.
4. La vista no acepta un id de usuario: siempre opera sobre `request.user`.
5. Si el perfil es provisional (`nro_documento` con formato `USR-<pk>`), la plantilla avisa
   al usuario para que complete sus datos.

### 8.6 Creación y edición de paquetes con componentes

1. El administrador abre `/gestion/paquetes/nuevo/` o `/gestion/paquetes/<pk>/editar/`.
2. Completa los datos del paquete (`PaqueteForm`): destino, nombre, descripción,
   condiciones, fechas, precio, cupos, vigencia y estado.
3. Completa los cuatro formsets inline: hoteles (tipo de habitación y noches), vuelos
   (vuelo y tramo), servicios (servicio y detalle) y actividades (día, orden, hora, título,
   descripción).
4. `PaqueteComponentesMixin.form_valid` valida el formulario y **todos** los formsets antes
   de guardar. Si alguno falla, vuelve a renderizar sin persistir nada.
5. Si todo es válido, abre una transacción: guarda el paquete, reasigna la FK de cada
   componente a la instancia definitiva y guarda los formsets. Los componentes marcados con
   `DELETE` se eliminan.
6. En el alta, `cupos_disponibles` se iguala a `cupos_total`. En la edición, el total se
   actualiza mediante `guardar_con_capacidad`, conservando los cupos ocupados.
7. "Eliminar" un paquete no borra la fila: cambia `estado` a `archivado`.

### 8.7 Gestión de habitaciones y tarifas

1. Desde `/gestion/hoteles/` el administrador abre las habitaciones de un hotel
   (`/gestion/hoteles/<hotel_pk>/habitaciones/`).
2. `TipoHabitacionForm` asocia siempre el hotel de la URL (no se acepta otro por POST),
   valida capacidad >= 1, total >= 1 y nombre único dentro del hotel.
3. En el alta, `habitaciones_disponibles = habitaciones_total`. En la edición, el total se
   recalcula con `guardar_con_capacidad` conservando `habitaciones_ocupadas`.
4. Desde la lista de tipos se accede a las tarifas
   (`/gestion/hoteles/<hotel_pk>/habitaciones/<tipo_pk>/tarifas/`).
5. `TarifaHabitacionForm` valida precio > 0, `fecha_fin >= fecha_inicio` y que no exista
   otra tarifa del mismo tipo que se solape con el rango.
6. Eliminar un tipo con tarifas elimina las tarifas en cascada; si el tipo está asignado a
   un paquete, la operación se bloquea y se muestra un mensaje.

### 8.8 Carga y revisión de documentos de proveedores

1. Un administrador crea/edita un `Proveedor` y le asigna un `usuario` activo.
2. Ese usuario entra a `/proveedor/documentos/`; `_proveedor_del_usuario` obtiene su
   proveedor y devuelve 403 si no está vinculado.
3. Para cargar, usa `/proveedor/documentos/nuevo/`: elige tipo, archivo y vencimiento.
4. `DocumentoProveedorForm` y los validadores comprueban nombre seguro, extensión permitida
   (`.pdf`, `.jpg`, `.jpeg`, `.png`), tamaño máximo (5 MB por defecto), archivo no vacío,
   firma real (magic bytes) y coincidencia con el MIME declarado. La ruta final se genera con
   UUID, sin usar el nombre original.
5. El documento se guarda como `pendiente` y asociado al proveedor.
6. El administrador consulta la cola en `/gestion/proveedores/documentos/`, filtra por estado
   y abre la revisión.
7. `revisar_documento` bloquea la fila, exige estado `pendiente`, acepta `aprobar` o
   `rechazar` y, al rechazar, exige motivo. Guarda estado, observación, revisor y fecha.
8. Un documento ya revisado no se puede volver a revisar. El proveedor puede cargar una
   nueva versión solo si la anterior ya no está pendiente; la versión anterior se conserva.
9. La descarga (`/proveedor/documentos/<pk>/archivo/`) solo la permite el propietario o un
   administrador; a terceros se les devuelve 404.

### 8.9 Actualización de disponibilidad

1. El administrador edita un tipo de habitación, un vuelo o un paquete.
2. El formulario **no** expone el campo de disponibilidad; solo el total.
3. `CapacidadFormMixin.preparar_capacidad` calcula y muestra lo ocupado actual
   (`total - disponible`).
4. Al guardar, el formulario valida que el total no sea negativo y no sea menor que lo
   ocupado.
5. `guardar_con_capacidad` abre una transacción, relee la fila con `select_for_update`, vuelve
   a calcular lo ocupado con el valor persistido, valida y fija
   `disponible = nuevo_total - ocupado`, y guarda.
6. Si otra transacción ocupó unidades entre la validación y el guardado, se lanza
   `CapacidadPorDebajoDeOcupado` y la vista muestra un error de formulario en lugar de un 500.
7. En PostgreSQL el bloqueo de fila serializa las actualizaciones; en SQLite el bloqueo es un
   no-op, aunque el recálculo usa el valor persistido.

### 8.10 Búsqueda, filtrado y comparación de paquetes

1. El visitante abre `/paquetes/`.
2. `_publicados()` filtra `estado="publicado"`, `venta_desde <= hoy <= venta_hasta`, ordena
   por `fecha_salida` y precarga destino/país.
3. `FiltroCatalogoForm` valida búsqueda, destino, precio mínimo/máximo y rango de salidas.
   Los precios negativos o mal formados, las fechas inválidas, un destino inexistente y los
   rangos incoherentes se rechazan.
4. Si el formulario es inválido, la vista ignora **todos** los filtros y muestra el catálogo
   completo con un aviso; no se ejecuta ninguna consulta con datos sin validar.
5. Si es válido, aplica los filtros al queryset.
6. Para comparar, el usuario marca hasta tres casillas. El JavaScript impide marcar una
   cuarta, muestra un aviso y conserva las selecciones en `sessionStorage` al cambiar de
   página o de filtros.
7. Al enviar, la URL contiene `ids` repetidos. El servidor convierte cada valor a entero,
   rechaza valores no numéricos o negativos, deduplica y rechaza más de tres identificadores
   únicos. Solo compara paquetes publicados y vigentes; los inexistentes o no publicados se
   omiten.
8. La pantalla de comparación muestra destino, salida, duración, precio y servicios de cada
   paquete.

---

## 9. Rutas y endpoints

Convenciones: `público` = sin sesión; `autenticado` = cualquier usuario con sesión;
`admin` = grupo `Administrador` o superusuario. Las rutas de formularios aceptan GET para
mostrar y POST para procesar salvo que se indique otra cosa.

### 9.1 Núcleo

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/` | `core:home` | core | `home` | GET | Público | Portada con enlaces a catálogos |

### 9.2 Cuentas

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/cuentas/registro/` | `accounts:registro` | accounts | `registro` | GET, POST | Público | Alta de cliente |
| `/cuentas/activar/<uidb64>/<token>/` | `accounts:activar` | accounts | `activar` | GET (enlace) | Público | Activar cuenta |
| `/cuentas/reenviar-verificacion/` | `accounts:reenviar_activacion` | accounts | `reenviar_activacion` | GET, POST | Público | Reenviar correo de activación |
| `/cuentas/ingresar/` | `accounts:login` | accounts | `LoginView` + `LoginForm` | GET, POST | Público | Iniciar sesión |
| `/cuentas/salir/` | `accounts:logout` | accounts | `LogoutView` | POST | Autenticado | Cerrar sesión |
| `/cuentas/recuperar/` | `accounts:password_reset` | accounts | `PasswordResetView` | GET, POST | Público | Solicitar recuperación |
| `/cuentas/recuperar/enviado/` | `accounts:password_reset_done` | accounts | `PasswordResetDoneView` | GET | Público | Confirmación de envío |
| `/cuentas/recuperar/<uidb64>/<token>/` | `accounts:password_reset_confirm` | accounts | `PasswordResetConfirmView` | GET, POST | Público | Definir nueva contraseña |
| `/cuentas/recuperar/listo/` | `accounts:password_reset_complete` | accounts | `PasswordResetCompleteView` | GET | Público | Confirmación final |
| `/cuentas/perfil/` | `accounts:perfil` | accounts | `perfil` | GET, POST | Autenticado | Editar perfil propio |
| `/cuentas/perfil/correo/` | `accounts:cambio_correo` | accounts | `cambio_correo` | GET, POST | Autenticado | Solicitar cambio de correo |
| `/cuentas/perfil/correo/confirmar/<uidb64>/<token>/` | `accounts:confirmar_cambio_correo` | accounts | `confirmar_cambio_correo` | GET (enlace) | Autenticado (mismo usuario) | Confirmar cambio |
| `/cuentas/perfil/contrasena/` | `accounts:cambiar_password` | accounts | `CambiarPasswordView` | GET, POST | Autenticado | Cambiar contraseña |
| `/cuentas/gestion/usuarios/` | `accounts:usuarios` | accounts | `usuarios` | GET | Admin | Listar/buscar usuarios |
| `/cuentas/gestion/usuarios/<pk>/activo/` | `accounts:usuario_activo` | accounts | `usuario_alternar_activo` | POST | Admin | Bloquear/activar |
| `/cuentas/gestion/usuarios/<pk>/rol/` | `accounts:usuario_rol` | accounts | `usuario_cambiar_rol` | POST | Admin | Asignar rol |

### 9.3 Destinos

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/destinos/` | `destinations:catalogo` | destinations | `CatalogoDestinosView` | GET | Público | Catálogo de destinos activos |
| `/destinos/<pk>/` | `destinations:detalle` | destinations | `DetalleDestinoView` | GET | Público | Detalle del destino |
| `/gestion/destinos/` | `destinations:gestion_lista` | destinations | `DestinoListaGestion` | GET | Admin | Listado de destinos |
| `/gestion/destinos/nuevo/` | `destinations:gestion_crear` | destinations | `DestinoCrear` | GET, POST | Admin | Crear destino |
| `/gestion/destinos/<pk>/editar/` | `destinations:gestion_editar` | destinations | `DestinoEditar` | GET, POST | Admin | Editar destino |
| `/gestion/destinos/<pk>/eliminar/` | `destinations:gestion_eliminar` | destinations | `DestinoEliminar` | GET, POST | Admin | Desactivar destino |

### 9.4 Proveedores y documentos

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/proveedor/documentos/` | `suppliers:mis_documentos` | suppliers | `mis_documentos` | GET | Autenticado vinculado a proveedor | Ver documentos propios |
| `/proveedor/documentos/nuevo/` | `suppliers:documento_cargar` | suppliers | `cargar_documento` | GET, POST | Proveedor | Cargar documento |
| `/proveedor/documentos/<pk>/nueva-version/` | `suppliers:documento_nueva_version` | suppliers | `nueva_version_documento` | GET, POST | Proveedor propietario | Cargar nueva versión |
| `/proveedor/documentos/<pk>/archivo/` | `suppliers:documento_archivo` | suppliers | `descargar_documento` | GET | Propietario o admin | Descargar archivo privado |
| `/gestion/proveedores/documentos/` | `suppliers:gestion_documentos` | suppliers | `gestion_documentos` | GET | Admin | Cola de documentos |
| `/gestion/proveedores/<proveedor_pk>/documentos/` | `suppliers:gestion_documentos_proveedor` | suppliers | `gestion_documentos` | GET | Admin | Documentos de un proveedor |
| `/gestion/proveedores/documentos/<pk>/revisar/` | `suppliers:gestion_documento_revisar` | suppliers | `revisar_documento` | GET, POST | Admin | Aprobar/rechazar |
| `/gestion/proveedores/` | `suppliers:gestion_lista` | suppliers | `ProveedorLista` | GET | Admin | Listado de proveedores |
| `/gestion/proveedores/nuevo/` | `suppliers:gestion_crear` | suppliers | `ProveedorCrear` | GET, POST | Admin | Crear proveedor |
| `/gestion/proveedores/<pk>/editar/` | `suppliers:gestion_editar` | suppliers | `ProveedorEditar` | GET, POST | Admin | Editar proveedor |
| `/gestion/proveedores/<pk>/eliminar/` | `suppliers:gestion_eliminar` | suppliers | `ProveedorEliminar` | GET, POST | Admin | Desactivar proveedor |

### 9.5 Hoteles, habitaciones y tarifas

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/gestion/hoteles/` | `hotels:gestion_lista` | hotels | `HotelLista` | GET | Admin | Listado de hoteles |
| `/gestion/hoteles/nuevo/` | `hotels:gestion_crear` | hotels | `HotelCrear` | GET, POST | Admin | Crear hotel |
| `/gestion/hoteles/<pk>/editar/` | `hotels:gestion_editar` | hotels | `HotelEditar` | GET, POST | Admin | Editar hotel |
| `/gestion/hoteles/<pk>/eliminar/` | `hotels:gestion_eliminar` | hotels | `HotelEliminar` | GET, POST | Admin | Desactivar hotel |
| `/gestion/hoteles/<hotel_pk>/habitaciones/` | `hotels:gestion_habitaciones` | hotels | `TipoHabitacionLista` | GET | Admin | Tipos del hotel |
| `/gestion/hoteles/<hotel_pk>/habitaciones/nuevo/` | `hotels:gestion_habitacion_crear` | hotels | `TipoHabitacionCrear` | GET, POST | Admin | Crear tipo |
| `/gestion/hoteles/<hotel_pk>/habitaciones/<pk>/editar/` | `hotels:gestion_habitacion_editar` | hotels | `TipoHabitacionEditar` | GET, POST | Admin | Editar tipo |
| `/gestion/hoteles/<hotel_pk>/habitaciones/<pk>/eliminar/` | `hotels:gestion_habitacion_eliminar` | hotels | `TipoHabitacionEliminar` | GET, POST | Admin | Eliminar tipo |
| `/gestion/hoteles/<hotel_pk>/habitaciones/<tipo_pk>/tarifas/` | `hotels:gestion_tarifas` | hotels | `TarifaHabitacionLista` | GET | Admin | Tarifas del tipo |
| `/gestion/hoteles/<hotel_pk>/habitaciones/<tipo_pk>/tarifas/nuevo/` | `hotels:gestion_tarifa_crear` | hotels | `TarifaHabitacionCrear` | GET, POST | Admin | Crear tarifa |
| `/gestion/hoteles/<hotel_pk>/habitaciones/<tipo_pk>/tarifas/<pk>/editar/` | `hotels:gestion_tarifa_editar` | hotels | `TarifaHabitacionEditar` | GET, POST | Admin | Editar tarifa |
| `/gestion/hoteles/<hotel_pk>/habitaciones/<tipo_pk>/tarifas/<pk>/eliminar/` | `hotels:gestion_tarifa_eliminar` | hotels | `TarifaHabitacionEliminar` | GET, POST | Admin | Eliminar tarifa |

### 9.6 Vuelos

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/gestion/vuelos/` | `flights:gestion_lista` | flights | `VueloLista` | GET | Admin | Listado de vuelos |
| `/gestion/vuelos/nuevo/` | `flights:gestion_crear` | flights | `VueloCrear` | GET, POST | Admin | Crear vuelo |
| `/gestion/vuelos/<pk>/editar/` | `flights:gestion_editar` | flights | `VueloEditar` | GET, POST | Admin | Editar vuelo |
| `/gestion/vuelos/<pk>/eliminar/` | `flights:gestion_eliminar` | flights | `VueloEliminar` | GET, POST | Admin | Cancelar vuelo |

### 9.7 Paquetes

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/paquetes/` | `packages:catalogo` | packages | `CatalogoPaquetesView` | GET | Público | Catálogo y filtros |
| `/paquetes/comparar/` | `packages:comparar` | packages | `comparar_paquetes` | GET | Público | Comparar 1–3 paquetes |
| `/paquetes/<pk>/` | `packages:detalle` | packages | `DetallePaqueteView` | GET | Público | Detalle del paquete |
| `/gestion/paquetes/` | `packages:gestion_lista` | packages | `PaqueteLista` | GET | Admin | Listado de paquetes |
| `/gestion/paquetes/nuevo/` | `packages:gestion_crear` | packages | `PaqueteCrear` | GET, POST | Admin | Crear paquete y componentes |
| `/gestion/paquetes/<pk>/editar/` | `packages:gestion_editar` | packages | `PaqueteEditar` | GET, POST | Admin | Editar paquete y componentes |
| `/gestion/paquetes/<pk>/eliminar/` | `packages:gestion_eliminar` | packages | `PaqueteEliminar` | GET, POST | Admin | Archivar paquete |

### 9.8 Django admin

| URL | Nombre | App | Vista | Métodos | Permisos | Función |
|---|---|---|---|---|---|---|
| `/admin/` | `admin:index` | django.contrib.admin | AdminSite | GET, POST | Superusuario con `is_staff` | Administración técnica de usuarios, grupos, logs y modelos registrados |

### 9.9 Notas sobre rutas

- El cierre de sesión es **solo POST**; un GET devuelve 405.
- Las rutas de activación y confirmación de correo se consumen mediante enlaces GET.
- Las rutas `gestion/...` no están bajo el prefijo `/admin/`; son la interfaz propia del
  proyecto y usan el grupo `Administrador`, no `is_staff`.
- No existen rutas de reservas, pagos ni API.
- Las rutas `public(...)` están marcadas explícitamente; el resto queda protegido por el
  middleware.

---

## 10. Formularios, validaciones y reglas de negocio

### 10.1 Validaciones de usuarios y cuentas

| Validación | Dónde | Comportamiento |
|---|---|---|
| Correo no duplicado | `RegistroForm.clean_email` | Compara `username` y `email` sin distinguir mayúsculas |
| Documento no duplicado | `RegistroForm.clean`, `PerfilForm.clean` | Restricción de modelo + mensaje comprensible |
| Contraseñas coinciden | `RegistroForm.clean` | Error en `password2` |
| Contraseña robusta | `validate_password` | Validadores de Django (mínimo 8, común, numérica, similitud) |
| Fecha de nacimiento no futura | `PerfilForm.clean_fecha_nacimiento` | Compara con `timezone.localdate()` |
| Login por correo o usuario | `LoginForm.clean` | Resolución sin distinguir mayúsculas |
| Cuenta activa | `AuthenticationForm` | Usuario inactivo no inicia sesión |
| No bloquearse a sí mismo | `usuario_alternar_activo` | Comprueba `user == request.user` |
| No cambiar su propio rol | `usuario_cambiar_rol` | Comprueba `user == request.user` |
| Rol válido | `CambiarRolForm` | Choices `Cliente`/`Administrador` |
| Correo nuevo disponible | `CambioCorreoForm.clean_email` | Excluye al propio usuario; no revela propietario |
| Token de activación válido | `activar` | `ActivationTokenGenerator`, un solo uso |
| Token de cambio de correo | `EmailChangeTokenGenerator` | Vincula usuario, correo actual, pendiente y nonce; caducidad propia |
| Cambio de correo solo en sesión propia | `confirmar_cambio_correo` | Compara `user.pk` con `request.user.pk` |

### 10.2 Validaciones de documentos

| Validación | Dónde | Comportamiento |
|---|---|---|
| Tipo de documento obligatorio | `DocumentoProveedorForm.clean_tipo_documento` | Rechaza cadenas vacías |
| Nombre seguro | `validar_archivo_documento` | Rechaza vacío, `\x00`, `/`, `\`, `..` |
| Extensión permitida | `validar_archivo_documento` | Solo PDF, JPG, JPEG, PNG |
| Archivo no vacío | `validar_archivo_documento` | `size` > 0 |
| Tamaño máximo | `validar_archivo_documento` | `DOCUMENTO_PROVEEDOR_MAX_BYTES` (5 MB por defecto) |
| Firma real | `validar_archivo_documento` | Magic bytes PDF/JPEG/PNG |
| MIME declarado coherente | `validar_archivo_documento` | Debe coincidir con la firma o ser `application/octet-stream` |
| Ruta segura | `ruta_documento_proveedor` | UUID + extensión validada; ignora el nombre original |
| Rechazo con motivo | `RevisionDocumentoForm.clean` y servicio | Motivo obligatorio al rechazar |
| Una sola revisión | `revisar_documento` | Solo desde estado `pendiente`; bloqueo de fila |
| Nueva versión solo tras revisión | `nueva_version_documento` | Bloquea si el documento está pendiente |
| Propiedad del documento | `descargar_documento` | Propietario o administrador; 404 para terceros |

### 10.3 Validaciones de fechas

| Regla | Nivel | Detalle |
|---|---|---|
| Nacimiento no futuro | Formulario | `PerfilForm` |
| `fecha_fin >= fecha_inicio` | Formulario y base de datos | `TarifaHabitacionForm` + `ck_tarifa_fechas` |
| Sin solapamiento de tarifas | Formulario | Consulta rangos del mismo tipo; no hay restricción de exclusión en BD |
| `fecha_llegada > fecha_salida` | Base de datos | `ck_vuelo_fechas` |
| `fecha_retorno >= fecha_salida` | Base de datos | `ck_paquete_fechas` |
| `venta_desde <= venta_hasta <= fecha_salida` | Base de datos | `ck_paquete_venta` |
| Filtros de catálogo válidos | Formulario | `FiltroCatalogoForm`; fechas inexistentes o mal formadas se rechazan |
| Rango de salidas coherente | Formulario | `salida_desde <= salida_hasta` |

### 10.4 Validaciones de precios y tarifas

| Regla | Nivel | Detalle |
|---|---|---|
| Precio de paquete > 0 | Base de datos | `ck_paquete_precio`; `DecimalField(12,2)` |
| Precio de tarifa > 0 | Formulario | `TarifaHabitacionForm.clean`; el campo no tiene CHECK en BD |
| Precio mínimo/máximo del catálogo >= 0 | Formulario | `DecimalField(min_value=0)` |
| Precio mínimo <= máximo | Formulario | `FiltroCatalogoForm.clean` |
| Formato decimal válido | Formulario | `DecimalField` con `max_digits=12`, `decimal_places=2` |
| Precio referencial de vuelo | Modelo | `DecimalField(10,2)`, sin validación explícita de positividad |

### 10.5 Validaciones de disponibilidad y capacidad

| Regla | Nivel | Detalle |
|---|---|---|
| Disponibilidad entre 0 y total | Base de datos | `ck_habitaciones_disponibles`, `ck_vuelo_asientos`, `ck_paquete_cupos` |
| Total no negativo | Formulario y servicio | `CapacidadFormMixin`, `guardar_con_capacidad` |
| Total no menor que lo ocupado | Formulario y servicio | Mensaje comprensible; comprobación con fila bloqueada |
| La disponibilidad no se edita directamente | Formulario | El campo no se expone; se recalcula |
| Alta: disponible = total | Formulario | `save()` de cada formulario |
| Edición: conservar ocupados | Servicio | `guardar_con_capacidad` |
| Carrera de concurrencia | Servicio/vista | `select_for_update` + excepción traducida a error de formulario |

### 10.6 Validaciones de componentes de paquetes

| Regla | Nivel | Detalle |
|---|---|---|
| Al menos 1 noche | Formulario | `PaqueteHotelForm.clean_noches` |
| Día de actividad >= 1 | Formulario | `PaqueteActividadForm.clean_dia` |
| Sin hotel repetido en el paquete | Modelo/formset | `uq_paquete_hotel` + mensaje del formset |
| Sin vuelo repetido en el paquete | Modelo/formset | `uq_paquete_vuelo` |
| Sin servicio repetido en el paquete | Modelo/formset | `uq_paquete_servicio` |
| Sin actividad repetida por día/orden | Modelo/formset | `uq_paquete_actividad` |
| Componentes válidos antes de guardar | Vista | Todos los formsets se validan; transacción atómica |

### 10.7 Restricciones de acceso

| Regla | Implementación |
|---|---|
| Toda vista exige sesión salvo públicas | `LoginRequiredMiddleware` + `@public`/`public(...)` |
| Administrador para gestión | `AdminRequiredMixin` / `@admin_required` |
| Anónimo redirigido, autenticado sin rol 403 | Mixins y decoradores de `core/access.py` |
| Proveedor solo sus documentos | `_proveedor_del_usuario` y comprobación de propiedad |
| Django admin solo superusuario/staff | Configuración nativa de Django |
| Media de proveedores no pública | Exclusión en `config/urls.py` y vista autenticada |

### 10.8 Restricciones de base de datos (resumen)

| Modelo | Restricción | Nombre |
|---|---|---|
| `Perfil` | UNIQUE (`tipo_documento`, `nro_documento`) | `uq_perfil_documento` |
| `Pais` | UNIQUE `codigo_iso`, UNIQUE `nombre` | — |
| `Categoria` | UNIQUE `nombre` | — |
| `Destino` | UNIQUE (`pais`, `nombre`); UNIQUE `codigo_iata` | `uq_destino_pais_nombre` |
| `DestinoFoto` | Una portada por destino (condicional) | `uq_destino_foto_portada` |
| `Proveedor` | UNIQUE `nit` | — |
| `Hotel` | CHECK estrellas 1–5 | `ck_hotel_estrellas` |
| `TipoHabitacion` | UNIQUE (`hotel`, `nombre`); CHECK disponibilidad | `uq_tipo_habitacion_hotel`, `ck_habitaciones_disponibles` |
| `TarifaHabitacion` | UNIQUE (`tipo_habitacion`, `fecha_inicio`); CHECK fechas | `uq_tarifa_inicio`, `ck_tarifa_fechas` |
| `Vuelo` | UNIQUE (`numero_vuelo`, `fecha_salida`); CHECK origen≠destino, fechas, asientos | `uq_vuelo_numero_fecha`, `ck_vuelo_origen_destino`, `ck_vuelo_fechas`, `ck_vuelo_asientos` |
| `Paquete` | CHECK fechas, venta, cupos y precio | `ck_paquete_fechas`, `ck_paquete_venta`, `ck_paquete_cupos`, `ck_paquete_precio` |
| `PaqueteHotel` | UNIQUE (`paquete`, `tipo_habitacion`) | `uq_paquete_hotel` |
| `PaqueteVuelo` | UNIQUE (`paquete`, `vuelo`) | `uq_paquete_vuelo` |
| `PaqueteServicio` | UNIQUE (`paquete`, `servicio`) | `uq_paquete_servicio` |
| `PaqueteActividad` | UNIQUE (`paquete`, `dia`, `orden`) | `uq_paquete_actividad` |

---

## 11. Seguridad

### 11.1 Autenticación y autorización

- Autenticación con el sistema nativo de Django (`AuthenticationMiddleware`, sesiones y
  `AuthenticationForm` adaptado).
- El correo se usa como `username`; el login acepta correo o usuario sin distinguir
  mayúsculas.
- Cuentas nuevas nacen inactivas y solo se activan mediante el enlace de verificación.
- El bloqueo de cuenta es `is_active=False`; un usuario bloqueado no puede iniciar sesión.
- Roles mediante grupos `Administrador` y `Cliente`; el acceso a la gestión se resuelve con
  `AdminRequiredMixin`/`@admin_required`, que distingue anónimo (redirección) de autenticado
  sin permiso (403).
- El portal del proveedor se autoriza por la relación `Proveedor.usuario`, no por un grupo.
- Django admin queda restringido a superusuarios con `is_staff`.

### 11.2 CSRF

- `CsrfViewMiddleware` está activo.
- Todos los formularios propios incluyen `{% csrf_token %}`.
- El cierre de sesión es POST y los cambios de estado administrativo
  (`usuario_activo`, `usuario_rol`) usan `@require_POST`.

### 11.3 Gestión de contraseñas

- Hash nativo de Django (no se configura un `PASSWORD_HASHERS` alternativo).
- Validadores: similitud con atributos del usuario, longitud mínima 8, contraseña común y
  contraseña completamente numérica.
- `PasswordChangeView` exige la contraseña actual y conserva la sesión con
  `update_session_auth_hash()`.
- Recuperación mediante `PasswordResetView` y token nativo; `PASSWORD_RESET_TIMEOUT` es de
  3 días.
- No hay límite de intentos fallidos de login (existe un `TODO` explícito).

### 11.4 Tokens de activación y cambio de correo

- **Activación:** `ActivationTokenGenerator` hereda de `PasswordResetTokenGenerator` e
  incluye `is_active` en el hash; al activar la cuenta el token deja de ser válido.
- **Cambio de correo:** `EmailChangeTokenGenerator` incluye usuario, correo actual, correo
  pendiente y nonce. Cada solicitud renueva el nonce e invalida enlaces anteriores.
- El cambio de correo exige que la sesión pertenezca al mismo usuario y solo se aplica si el
  token es válido y el correo no está ocupado.
- Los errores de integridad se capturan y no dejan `email`/`username` inconsistentes.
- La caducidad del cambio de correo es `EMAIL_CHANGE_TIMEOUT` (24 horas por defecto); la
  activación/recuperación usa `PASSWORD_RESET_TIMEOUT` (3 días).

### 11.5 Protección de archivos privados

- Los documentos de proveedores se guardan bajo `media/proveedores/`.
- En desarrollo, la ruta pública de `media/` excluye expresamente `proveedores/`.
- La única vía de descarga es `suppliers:documento_archivo`, autenticada y con comprobación
  de propiedad o rol administrador.
- A terceros se devuelve 404 para no revelar la existencia del documento.
- La respuesta de descarga añade `X-Content-Type-Options: nosniff` y usa `FileResponse`
  como adjunto.

### 11.6 Validación de cargas

- Lista blanca de extensiones: PDF, JPG, JPEG y PNG.
- Verificación de la firma real del archivo (magic bytes), no solo del `content_type`.
- Límite de tamaño configurable (5 MB por defecto).
- Rechazo de nombres con separadores o `..`; la ruta final se genera con UUID y descarta el
  nombre original.
- El archivo debe existir y no estar vacío.

### 11.7 Protección de operaciones administrativas

- Las vistas `gestion/...` exigen rol administrador o superusuario.
- Los formularios de gestión incluyen CSRF y validan en servidor.
- No se confía en parámetros de URL para la pertenencia: los recursos anidados se filtran
  por el hotel/tipo de la URL (`get_queryset`), y los documentos por proveedor propietario.
- Las eliminaciones de catálogos son lógicas para no romper referencias.

### 11.8 Otras medidas verificables

- `SECRET_KEY` es obligatoria por variable de entorno; no tiene valor por defecto en el
  código.
- `DEBUG` se lee del entorno, pero `dev.py` fuerza `True` y `prod.py` fuerza `False`.
- En producción: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
  `SECURE_HSTS_SECONDS` (30 días), `SECURE_HSTS_INCLUDE_SUBDOMAINS` y
  `SECURE_CONTENT_TYPE_NOSNIFF`.
- Cookies de sesión `HttpOnly` y `SameSite=Lax`; duración de 8 horas.
- `ALLOWED_HOSTS` se lee de entorno y por defecto está vacío.
- No se exponen claves ni tokens en las plantillas; los enlaces contienen `uidb64` y token,
  no contraseñas.
- Throttling del reenvío de activación mediante `cache.add` con una ventana de 60 segundos.
- Django admin registra modelos, pero los campos de revisión de documentos son de solo
  lectura para no saltarse el flujo de CU-13.

**Carencias de seguridad conocidas:** no hay límite de intentos de login, no hay CSP, no hay
rate limiting general, el throttling de reenvío usa la caché local por proceso y la
publicación de estáticos/media en producción está pendiente.

---

## 12. Pruebas y estado de verificación

### 12.1 Ejecución

```bash
python manage.py test
python manage.py test apps.packages
python manage.py test apps.accounts.tests.AccesoPorRolTests.test_cliente_no_accede_a_gestion
```

Las pruebas usan el mismo motor configurado en `DATABASE_URL`. Django crea una base de datos
de prueba, por lo que el usuario de PostgreSQL necesita `CREATEDB`. No hay linter,
formateador ni typechecker configurado.

### 12.2 Organización de los tests

| App | Clases de prueba | Áreas cubiertas |
|---|---|---|
| `accounts` | `AccesoPorRolTests`, `PerfilTests`, `CambioCorreoTests`, `CambioPasswordTests`, `LoginSuperuserTests`, `RegistroTests`, `ReenvioActivacionTests` | Acceso por rol, perfil, cambio de correo, contraseña, superusuario, registro, reenvío |
| `destinations` | Sin archivo `tests.py` propio | Catálogo cubierto indirectamente por pruebas de acceso y de paquetes |
| `suppliers` | `CargaDocumentosTests`, `ConsultaYAccesoTests`, `RevisionDocumentosTests`, `HistorialDeVersionesTests` | Validación de archivos, privacidad, revisión y versiones |
| `hotels` | `TipoHabitacionGestionTests`, `DisponibilidadHabitacionesTests`, `TarifaHabitacionGestionTests`, `IntegracionConPaquetesTests` | Habitaciones, disponibilidad, tarifas e integración |
| `flights` | `DisponibilidadVuelosTests`, `AccesoVuelosTests` | Vuelos, disponibilidad y acceso |
| `packages` | `GestionPaquetesTests`, `DisponibilidadPaquetesTests`, `GestionYCatalogoTests`, `CatalogoFiltrosTests`, `ComparadorPaquetesTests` | Componentes, cupos, catálogo, filtros, comparador y accesos |

### 12.3 Funcionalidades cubiertas por pruebas automatizadas

- Acceso público, redirección al login, 403 para clientes en gestión y 405 en logout GET.
- Registro completo con verificación de correo, duplicados y transacción fallida.
- Recuperación de contraseña, reenvío con throttling y login por correo/usuario.
- Perfil propio, fecha futura, documento duplicado y perfil provisional de superusuario.
- Cambio de correo con token válido, caducado, usado, solicitud posterior y error de
  integridad.
- Cambio de contraseña con validadores y conservación de sesión.
- CRUD de destinos y eliminación lógica.
- Carga de documentos con extensión, contenido, MIME, tamaño y nombre peligrosos.
- Acceso a documentos propios/ajenos, revisión única, rechazo con motivo e historial.
- Tipos de habitación, tarifas, solapamientos, disponibilidad y protección de referencias.
- Vuelos, disponibilidad, cancelación lógica y acceso.
- Paquetes con los cuatro componentes, componentes inválidos/duplicados, edición y borrado.
- Catálogo publicado, filtros válidos, parámetros inválidos y ausencia de HTTP 500.
- Comparador con uno, dos y tres paquetes, cuarto rechazado, duplicados, inexistentes,
  no publicados y límite por URL.

### 12.4 Resultado de la verificación durante esta auditoría

| Comando | Resultado |
|---|---|
| `python manage.py check` | System check identified no issues (0 silenced) |
| `python manage.py test` (suite completa) | **192 pruebas ejecutadas, todas OK**, en 117,5 s |
| Base de datos usada en la ejecución | SQLite temporal mediante `DATABASE_URL` (el usuario PostgreSQL local no disponía de `CREATEDB` en este entorno) |

La ejecución anterior es la realizada durante la auditoría. No se presentan resultados de
ejecuciones antiguas como si fueran actuales. La suite con SQLite valida la lógica, pero no
reproduce el comportamiento real de bloqueos de fila de PostgreSQL; las pruebas específicas
de concurrencia usan el ORM y pasan en SQLite porque el recálculo se apoya en el valor
persistido.

### 12.5 Pruebas manuales y limitaciones del entorno

- No se realizó una verificación manual exhaustiva en navegador durante esta auditoría; la
  interacción JavaScript del comparador y los formularios dinámicos de formsets no está
  cubierta por pruebas automatizadas de navegador.
- No hay pruebas E2E, de accesibilidad, de rendimiento ni de carga.
- La suite no se ejecutó contra PostgreSQL en esta auditoría por la limitación de
  `CREATEDB`; se usó SQLite temporal.
- `apps/destinations` no tiene `tests.py` propio; parte de su comportamiento se cubre en
  pruebas de acceso y de paquetes.

---

## 13. Configuración e instalación

### 13.1 Requisitos previos

- Python compatible con Django 5.2 (el entorno local usa 3.14.3; el repositorio no fija una
  versión mínima de Python).
- PostgreSQL 14 o superior (según el esquema de referencia) con una base creada.
- Usuario de PostgreSQL con permisos para crear bases de datos si se van a ejecutar tests.
- Git y terminal (PowerShell en Windows, bash en Linux/macOS).

### 13.2 Instalación de dependencias

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt` declara: Django 5.2.x, `psycopg[binary]`, `django-environ` y Pillow.

### 13.3 Variables de entorno

Copiar `.env.example` a `.env` y completar los valores. **No se documentan valores secretos
reales.**

| Variable | Obligatoria | Uso |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | No para `manage.py` (fuerza `dev`) | Módulo de configuración; `wsgi.py`/`asgi.py` usan `prod` por defecto |
| `SECRET_KEY` | Sí | Clave criptográfica de Django; no tiene valor por defecto |
| `DEBUG` | Sí (con default `False` en `base.py`) | Modo depuración; `dev.py` fuerza `True` |
| `ALLOWED_HOSTS` | Recomendada; vacía por defecto | Lista separada por comas |
| `DATABASE_URL` | Sí | URL de PostgreSQL, por ejemplo `postgres://usuario:clave@host:5432/base` |
| `EMAIL_URL` | No (default `consolemail://`) | Backend de correo |
| `DEFAULT_FROM_EMAIL` | No | Remitente por defecto |
| `SITE_URL` | No (default `http://localhost:8000`) | Base para construir enlaces en correos |
| `EMAIL_CHANGE_TIMEOUT` | No (default 86400 s) | Caducidad del enlace de cambio de correo |
| `DOCUMENTO_PROVEEDOR_MAX_BYTES` | No (default 5 MB) | Tamaño máximo de documentos |

### 13.4 PostgreSQL y migraciones

1. Crear la base (por ejemplo `estropical_db`) y asegurar que `DATABASE_URL` apunta a ella.
2. Ejecutar:

```bash
python manage.py migrate
```

Las migraciones crean las tablas y ejecutan datos iniciales:

- `accounts.0002_roles_iniciales`: crea los grupos `Administrador` y `Cliente`.
- `destinations.0002_datos_iniciales`: crea países (`BO`, `PE`, `BR`, `AR`, `CL`, `US`,
  `ES`) y categorías (`Playa`, `Aventura`, `Cultural`, `Naturaleza`, `Ciudad`).
- `accounts.0003...`: añade los campos de correo pendiente y nonce.
- `suppliers.0002...`: añade `Proveedor.usuario` y la validación/ruta de archivos.

No se debe ejecutar `docs/estropical_schema.sql` manualmente: contiene tablas y objetos de
todos los sprints y entraría en conflicto con las migraciones de Django.

### 13.5 Superusuario y ejecución

```bash
python manage.py createsuperuser   # usar un correo como nombre de usuario
python manage.py runserver
```

`manage.py` establece `DJANGO_SETTINGS_MODULE=config.settings.dev` antes de cargar Django.
`config/wsgi.py` y `config/asgi.py` usan `config.settings.prod` por defecto.

### 13.6 Correo

- En desarrollo, `EMAIL_URL=consolemail://` imprime los correos en la consola del servidor.
- Para producción se debe configurar un backend SMTP real en `EMAIL_URL` y un remitente
  válido en `DEFAULT_FROM_EMAIL`; el repositorio no incluye credenciales.
- Los enlaces se construyen con `SITE_URL`; debe ser la URL pública correcta en producción.

### 13.7 Archivos estáticos y multimedia

- `STATIC_URL = "static/"`, `STATICFILES_DIRS = [BASE_DIR / "static"]`,
  `STATIC_ROOT = BASE_DIR / "staticfiles"`.
- `MEDIA_URL = "media/"`, `MEDIA_ROOT = BASE_DIR / "media"`.
- En desarrollo, `config/urls.py` sirve `media/` solo con `DEBUG=True` y excluye
  `media/proveedores/`.
- Para producción se debe ejecutar `collectstatic` y servir estáticos/media desde el
  servidor web o un storage externo, manteniendo `media/proveedores/` fuera del acceso
  público.

### 13.8 Consideraciones para producción

- Definir `ALLOWED_HOSTS` reales.
- Usar una `SECRET_KEY` larga y aleatoria, fuera del repositorio.
- Mantener `DEBUG=False` y HTTPS (redirección, HSTS y cookies seguras ya configuradas).
- Configurar SMTP real.
- Servir estáticos y media con nginx u otro servidor, con exclusión de documentos privados.
- Revisar el límite de intentos de login y la caché compartida para throttling.
- Ejecutar las pruebas contra PostgreSQL antes de desplegar.

---

## 14. Limitaciones y trabajo pendiente

### 14.1 Errores o riesgos detectados (no corregidos en esta auditoría)

1. **Filtros del catálogo de destinos sin validar:** `CatalogoDestinosView` usa directamente
   `request.GET["pais"]` y `request.GET["categoria"]` en `filter(pais_id=...)` /
   `filter(categoria_id=...)`. Un valor no numérico manipulado (`?pais=abc`) puede provocar
   un `ValueError` y un HTTP 500. No se corrigió porque esta tarea solo permite crear este
   documento.
2. **Discrepancia de conteo de pruebas:** `README.md` y `AGENTS.md` indican 180 pruebas;
   durante esta auditoría la suite ejecutó **192** (incluye las 12 del comparador). Los
   documentos no se modificaron.
3. **Discrepancia sobre FK de perfil:** `docs/estropical_schema.sql` comenta que
   `perfil.usuario_id` se guarda "sin FK", pero el modelo Django
   `OneToOneField(settings.AUTH_USER_MODEL)` crea una clave foránea real en la base.
4. **Documentación del esquema vs implementación:** el SQL describe seis sprints; solo los
   Sprints 1 y 2 están implementados. No debe interpretarse como estado actual.
5. **CU-08 incompleto:** `DestinoFoto` y su administración existen, pero no el formset de
   carga/orden/portada en la interfaz propia.
6. **Sin plantilla 500 personalizada:** existen `403.html` y `404.html`, pero no `500.html`.
7. **`core/home.html` es provisional:** contiene un `TODO` de contenido y solo enlaces a los
   catálogos.
8. **`static/js/main.js` es un `TODO`:** la interacción del comparador y de los formsets está
   en scripts inline de sus plantillas, no en un archivo JS central.

### 14.2 Limitaciones funcionales conocidas

- No existen reservas, pagos, facturación, reembolsos, cupones, promociones, reseñas,
  soporte ni notificaciones.
- El detalle de paquete no permite reservar.
- No se genera PDF de itinerario.
- No hay cálculo automático del precio del paquete a partir de hoteles, vuelos y tarifas; el
  precio es un campo manual.
- La disponibilidad no se descuenta automáticamente al vender: no hay tabla de reservas ni
  trigger; la ocupación se deriva de `total - disponible`.
- El comparador no incluye todos los campos de los componentes; muestra destino, salida,
  duración, precio y servicios.
- Las fotos de destino solo se gestionan desde Django admin.
- La portada no muestra contenido destacado.
- No hay API ni integración con pasarelas de pago.
- No hay edición masiva ni importación/exportación de datos.

### 14.3 Concurrencia, almacenamiento, seguridad y escalabilidad

- **Concurrencia:** `guardar_con_capacidad` usa `select_for_update` y transacción para
  conservar la ocupación; en SQLite el bloqueo no es real. El solapamiento de tarifas se
  valida en formulario, no con una restricción de exclusión de PostgreSQL, por lo que dos
  altas simultáneas podrían solaparse.
- **Almacenamiento:** los archivos se guardan en el sistema de archivos local (`media/`); no
  hay almacenamiento externo, cuotas por proveedor ni antivirus.
- **Seguridad:** falta limitación de intentos de login, CSP, rate limiting general y una
  caché compartida para throttling. La publicación de media privada depende de la
  configuración del servidor en producción.
- **Escalabilidad:** monolito sin colas, sin tareas asíncronas, sin caché de consultas y sin
  paginación configurada en todas las tablas (las listas genéricas paginan a 20; la lista de
  usuarios limita a 200; documentos y tarifas no paginan).
- **Correo:** el backend de consola no es apto para producción; no hay reintentos ni cola.

### 14.4 Dependencias para el Sprint 3

- `Reserva`, `Pasajero`, `DocumentoViaje` y `ConfirmacionProveedor` deben crearse como
  modelos y migraciones.
- El trigger `trg_reserva_cupos` y las funciones `fn_ajustar_cupos`,
  `fn_penalidad_cancelacion` y `fn_cerrar_caja` están definidos solo en el esquema SQL de
  referencia; deben implementarse con migraciones `RunSQL` o lógica de servicio.
- Las vistas `v_saldo_reserva` y `v_reporte_ventas` tampoco existen en Django.
- CU-17 requiere `Reserva` y la relación con `Proveedor`; no debe implementarse antes.
- Los pagos y la facturación del Sprint 4 dependen de `Reserva` y `Perfil`.
- El detalle de paquete necesitará un flujo de reserva y validación de cupos/disponibilidad
  real.

### 14.5 Mejoras futuras (fuera del alcance actual)

- Completar CU-08 con un formset de fotos y selección de portada.
- Añadir validación de filtros también al catálogo de destinos.
- Implementar pruebas E2E de navegador para el comparador y los formsets.
- Configurar SMTP, almacenamiento externo, CSP, rate limiting y caché compartida.
- Añadir paginación a las listas que hoy no la tienen.
- Incorporar reporting, promociones, reseñas y notificaciones de los sprints posteriores.
- Unificar la lógica de paquetes en un `services.py` si el proyecto sigue creciendo.

---

## 15. Guía para elaboración de diagramas

> Esta sección solo proporciona información estructurada; no genera los diagramas.

### 15.1 Diagrama de clases

Clases candidatas y atributos/métodos principales:

| Clase | Atributos clave | Métodos/propiedades |
|---|---|---|
| `User` (Django) | `username`, `email`, `password`, `is_active`, `is_staff`, `is_superuser` | Autenticación, grupos |
| `Group` (Django) | `name` | Roles `Administrador`, `Cliente` |
| `Perfil` | `nombres`, `apellidos`, `tipo_documento`, `nro_documento`, `fecha_nacimiento`, `telefono`, `direccion`, `nit`, `razon_social`, `correo_pendiente`, `correo_pendiente_nonce`, `fecha_registro` | `nombre_completo` |
| `Pais` | `codigo_iso`, `nombre` | — |
| `Categoria` | `nombre`, `descripcion` | — |
| `Destino` | `nombre`, `codigo_iata`, `descripcion`, `activo` | `es_internacional`, `portada` |
| `DestinoFoto` | `archivo`, `descripcion`, `orden`, `es_portada` | — |
| `Proveedor` | `razon_social`, `nit`, `tipo`, `nombre_contacto`, `correo`, `telefono`, `estado_validacion`, `activo` | — |
| `ProveedorDocumento` | `tipo_documento`, `archivo`, `fecha_vencimiento`, `estado`, `observacion`, `fecha_carga`, `fecha_revision` | — |
| `Hotel` | `nombre`, `estrellas`, `direccion`, `descripcion`, `activo` | — |
| `TipoHabitacion` | `nombre`, `capacidad`, `habitaciones_total`, `habitaciones_disponibles`, `descripcion` | `habitaciones_ocupadas` |
| `TarifaHabitacion` | `fecha_inicio`, `fecha_fin`, `precio_noche` | — |
| `Vuelo` | `numero_vuelo`, `fecha_salida`, `fecha_llegada`, `asientos_total`, `asientos_disponibles`, `precio_referencial`, `estado` | `asientos_ocupados` |
| `Servicio` | `nombre`, `descripcion` | — |
| `Paquete` | `nombre`, `descripcion`, `condiciones`, `fecha_salida`, `fecha_retorno`, `precio_persona`, `cupos_total`, `cupos_disponibles`, `venta_desde`, `venta_hasta`, `estado` | `duracion_dias`, `cupos_ocupados` |
| `PaqueteHotel` | `noches` | — |
| `PaqueteVuelo` | `tramo` | — |
| `PaqueteServicio` | `detalle` | — |
| `PaqueteActividad` | `dia`, `orden`, `hora_inicio`, `titulo`, `descripcion` | — |

Relaciones para el diagrama de clases: usar las cardinalidades de la sección 6.8. Marcar
`User` y `Group` como clases externas de Django. No incluir clases de reservas, pagos ni
confirmaciones porque no existen como modelos.

### 15.2 Diagrama entidad-relación

Entidades y claves:

| Entidad | PK | FK principales |
|---|---|---|
| `perfil` | `id` | `usuario_id` → `auth_user`, `nacionalidad_id` → `pais` |
| `pais` | `id` | — |
| `categoria` | `id` | — |
| `destino` | `id` | `pais_id`, `categoria_id` |
| `destino_foto` | `id` | `destino_id` |
| `proveedor` | `id` | `usuario_id` → `auth_user` |
| `proveedor_documento` | `id` | `proveedor_id`, `revisado_por_id` → `perfil` |
| `hotel` | `id` | `proveedor_id`, `destino_id` |
| `tipo_habitacion` | `id` | `hotel_id` |
| `tarifa_habitacion` | `id` | `tipo_habitacion_id` |
| `vuelo` | `id` | `proveedor_id`, `origen_id` → `destino`, `destino_id` → `destino` |
| `servicio` | `id` | — |
| `paquete` | `id` | `destino_id` |
| `paquete_hotel` | `id` | `paquete_id`, `tipo_habitacion_id` |
| `paquete_vuelo` | `id` | `paquete_id`, `vuelo_id` |
| `paquete_servicio` | `id` | `paquete_id`, `servicio_id` |
| `paquete_actividad` | `id` | `paquete_id` |

Cardinalidades globales:

- País 1—N Destino; Categoría 1—N Destino; Destino 1—N DestinoFoto.
- Destino 1—N Hotel; Destino 1—N Vuelo (como origen y como llegada).
- Proveedor 1—N Hotel; Proveedor 1—N Vuelo; Proveedor 1—N Documento.
- Usuario 1—1 Perfil; Usuario 0..1—0..1 Proveedor.
- Perfil 1—N Documento revisado.
- Hotel 1—N TipoHabitacion; TipoHabitacion 1—N TarifaHabitacion.
- Paquete M—N TipoHabitacion; Paquete M—N Vuelo; Paquete M—N Servicio.
- Paquete 1—N PaqueteActividad.
- Las tablas puente tienen PK propia y restricción única por pareja.

Para el ER físico, incluir las restricciones de la sección 10.8. No dibujar relaciones
inexistentes (reserva, pago, promoción, etc.).

### 15.3 Diagrama general de casos de uso

**Actores:** Visitante, Cliente, Administrador, Superusuario, Proveedor.

**Casos implementados por actor:**

- **Visitante:** registrarse, iniciar sesión, recuperar contraseña, ver catálogo de destinos,
  ver detalle de destino, ver catálogo de paquetes, filtrar paquetes, ver detalle de paquete,
  comparar paquetes (1–3).
- **Cliente:** todo lo del visitante + gestionar perfil, cambiar correo, cambiar contraseña,
  cerrar sesión.
- **Administrador:** todo lo público + gestionar usuarios/roles, gestionar destinos,
  gestionar proveedores, revisar documentos, gestionar hoteles, gestionar habitaciones,
  gestionar tarifas, gestionar vuelos, gestionar paquetes y componentes, actualizar
  disponibilidad, cerrar sesión.
- **Superusuario:** todo lo del administrador + acceder a Django admin.
- **Proveedor:** iniciar sesión, ver sus documentos, cargar documento, descargar sus
  documentos, cargar nueva versión, cerrar sesión.

**Parciales:** gestionar fotos de destino (solo Django admin).

**Pendientes (no dibujar como implementados):** confirmar servicios con proveedores
(CU-17), reservar paquete, registrar pasajeros, cargar documentos de viaje, cancelar reserva,
pagar, facturar, generar reportes, gestionar promociones, reseñas, soporte y notificaciones.

### 15.4 Diagramas de actividad

Procesos recomendados y nodos principales:

1. **Registro/activación:** inicio → formulario → validar datos → decisión (válido) →
   crear usuario/perfil/rol → enviar correo → abrir enlace → validar token → activar →
   login. Rama inválida: mostrar errores.
2. **Login:** inicio → credenciales → resolver usuario → validar → decisión (activo y
   correcto) → crear sesión → redirigir; rama falsa: mensaje de error.
3. **Recuperación/cambio de contraseña:** solicitar → enviar enlace → abrir → validar token
   → nueva contraseña → validadores → guardar/confirmar.
4. **Cambio de correo:** solicitar → validar disponibilidad → guardar pendiente + nonce →
   enviar al nuevo correo → abrir enlace → comprobar sesión y token → decisión → actualizar
   email/username o mostrar error.
5. **Perfil:** abrir → obtener/crear perfil → editar → validar → guardar → mensaje.
6. **Paquete con componentes:** abrir formulario → completar datos → validar paquete y
   cuatro formsets → decisión (todo válido) → transacción → guardar paquete/componentes →
   recalcular cupos → redirigir; rama inválida: volver al formulario sin guardar.
7. **Habitaciones/tarifas:** seleccionar hotel → crear/editar tipo → validar capacidad →
   guardar; seleccionar tipo → crear tarifa → validar fechas/precio/solapamiento → guardar.
8. **Documentos:** proveedor carga → validar archivo → guardar pendiente; administrador
   revisa → decisión aprobar/rechazar → registrar revisor/fecha; proveedor consulta.
9. **Disponibilidad:** editar total → calcular ocupado → validar total → bloquear fila →
   recalcular disponible → guardar; rama de conflicto: error de formulario.
10. **Catálogo/comparador:** abrir catálogo → validar filtros → decisión (válidos) → aplicar
    filtros o ignorar; seleccionar paquetes → límite 3 → enviar ids → validar/deduplicar →
    consultar publicados → mostrar comparación.

### 15.5 Diagramas de secuencia

Interacciones recomendadas:

- **Registro:** Visitante → `RegistroForm` → `registrar_cliente` → `User`/`Perfil`/`Group` →
  `send_mail` → respuesta.
- **Activación:** Visitante → `activar` → `ActivationTokenGenerator` → `User` → login.
- **Login:** Visitante → `LoginForm` → `AuthenticationForm` → `User` → sesión.
- **Cambio de correo:** Usuario → `CambioCorreoForm` → `solicitar_cambio_correo` →
  `Perfil` → correo; luego Usuario → `confirmar_cambio_correo` → token/servicio → `User`.
- **Paquete:** Administrador → `PaqueteForm` + formsets → `PaqueteComponentesMixin` →
  `transaction.atomic` → `Paquete`/componentes → `guardar_con_capacidad`.
- **Documento:** Proveedor → `DocumentoProveedorForm` → `validar_archivo_documento` →
  `ProveedorDocumento`; Administrador → `revisar_documento` → `select_for_update` →
  `ProveedorDocumento`.
- **Disponibilidad:** Administrador → formulario → `guardar_con_capacidad` →
  `select_for_update` → modelo → base de datos.
- **Catálogo:** Visitante → `CatalogoPaquetesView` → `FiltroCatalogoForm` → ORM →
  plantilla.
- **Comparador:** Visitante → catálogo (JS de límite) → `comparar_paquetes` →
  validación/deduplicación → ORM → plantilla.

### 15.6 Diagrama de arquitectura

Componentes y dependencias:

- **Navegador** (HTML/Bootstrap/JS) → **Django URLconf**.
- **Middleware** (seguridad, sesión, CSRF, autenticación, login requerido, mensajes).
- **Aplicaciones Django**: `core` (transversal), `accounts`, `destinations`, `suppliers`,
  `hotels`, `flights`, `packages`.
- **Capa de presentación:** plantillas Django + Bootstrap + CSS/JS.
- **Capa de aplicación:** vistas y formularios; servicios en `accounts`, `suppliers` y
  `core/disponibilidad`.
- **Capa de datos:** ORM de Django → **PostgreSQL**.
- **Archivos:** `media/` local; documentos privados servidos por vista autenticada.
- **Correo:** backend configurable (consola en desarrollo).
- **Administración:** Django admin para superusuarios.

Dependencias principales: `packages` → `destinations`, `hotels`, `flights`, `suppliers`;
`hotels`/`flights` → `suppliers` y `destinations`; `accounts` → `destinations` (nacionalidad);
`core` es transversal y no depende de las apps funcionales; todas las apps funcionales usan
`core.access` y `core.views_base` (excepto las públicas, que usan `core.access.public`).

---

## Anexo A. Archivos inspeccionados

- Configuración: `manage.py`, `requirements.txt`, `.env.example`, `.gitignore`,
  `config/settings/{base,dev,prod}.py`, `config/urls.py`, `config/wsgi.py`,
  `config/asgi.py`.
- Documentación existente: `README.md`, `AGENTS.md`, `docs/estropical_schema.sql`.
- Apps: todos los `models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`, `apps.py`,
  `tests.py` de `accounts`, `core`, `destinations`, `suppliers`, `hotels`, `flights` y
  `packages`; `accounts/services.py`, `accounts/tokens.py`,
  `accounts/context_processors.py`, `core/access.py`, `core/views_base.py`,
  `core/forms.py`, `core/disponibilidad.py`, `core/templatetags/core_extras.py`,
  `suppliers/services.py`, `suppliers/validators.py`.
- Migraciones: `accounts/0002`, `accounts/0003`, `destinations/0002`,
  `suppliers/0002` y migraciones iniciales por app.
- Plantillas: `base.html`, `403.html`, `404.html`, parciales y plantillas de `core`,
  `accounts`, `destinations`, `hotels`, `suppliers` y `packages`.
- Estáticos: `static/css/estropical.css`, `static/js/main.js`.
- Pruebas: suite completa ejecutada con `manage.py test`.

## Anexo B. Información que no pudo verificarse

- No se verificó el contenido del archivo `.env` real (solo se inspeccionó `.env.example`);
  por seguridad no se documentan valores.
- No se verificó el historial de Git ni ramas remotas.
- No se ejecutó la aplicación en un navegador real ni se probó la interacción JavaScript
  manualmente.
- No se ejecutó la suite contra PostgreSQL en esta auditoría por falta de `CREATEDB` en el
  usuario local; se usó SQLite temporal.
- No se verificó el contenido del diagrama `docs/estropical_er.drawio`/`.png` más allá de su
  existencia.
- No se verificó el comportamiento de un servidor SMTP real ni de un servidor web de
  producción.
- No se verificó el esquema SQL contra una base PostgreSQL real.



