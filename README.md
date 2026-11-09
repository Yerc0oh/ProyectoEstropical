
# Estropical.com · Tropical Tours Ltda.

Sistema web de gestión y venta de viajes desarrollado como proyecto académico.

El proyecto integra los avances de los Sprints 1 a 4:

- Sprint 1: acceso de usuarios, perfiles, roles y destinos.
- Sprint 2: paquetes turísticos, proveedores, hoteles, vuelos y disponibilidad.
- Sprint 3: reservas, clientes, confirmaciones, documentos e itinerarios.
- Sprint 4: pagos, cuotas, facturación académica, reembolsos y caja.

Los Sprints 5 y 6 corresponden a recomendaciones personalizadas, reportes, indicadores, notificaciones, atención al cliente y administración complementaria.

**Tecnologías:** Python, Django 5.2, PostgreSQL, Bootstrap 5 y plantillas HTML. El proyecto no utiliza una API separada.

## Puesta en marcha

### Windows / PowerShell

Desde la carpeta principal del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Editar `.env` y configurar `SECRET_KEY` y `DATABASE_URL` con los datos de PostgreSQL.

Crear la base de datos `estropical_db` mediante pgAdmin o PostgreSQL.

Después ejecutar:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Para el superusuario, utilizar un correo electrónico como nombre de usuario.

### Pruebas

```powershell
python manage.py check
python manage.py test
```

Las pruebas requieren una conexión a PostgreSQL y permisos para crear una base de datos de pruebas.

La cantidad total de pruebas y sus resultados deben verificarse después de integrar las ramas. Los Sprints 1 y 2 incluyen pruebas de autenticación, perfiles, paquetes, hoteles, vuelos, proveedores y disponibilidad. Los Sprints 3 y 4 incorporan pruebas de reservas, cupos, pagos, cuotas, facturas, conciliación y cierre de caja.

### Expiración de reservas

El proyecto incorpora el comando:

```powershell
python manage.py expirar_reservas
```

Permite procesar reservas pendientes que superaron el plazo de pago. Puede ejecutarse periódicamente mediante una tarea programada.

## Accesos y seguridad

| Tipo de usuario | Identificación | Funcionalidades |
|---|---|---|
| Visitante | Sin sesión | Inicio, catálogo de destinos y paquetes, registro, inicio de sesión y recuperación de contraseña |
| Cliente | Grupo `Cliente` | Perfil, reservas, itinerarios, pagos, estados de cuenta y facturas |
| Proveedor | Usuario vinculado a `Proveedor.usuario` | Perfil y gestión de sus documentos privados |
| Administrador | Grupo `Administrador` o superusuario | Gestión de usuarios, destinos, paquetes, proveedores, hoteles, vuelos, reservas, clientes, pagos, facturas, reembolsos y caja |

### Mecanismos de seguridad

- Autenticación mediante sesiones de Django.
- Cookies de sesión con protección `HttpOnly` y configuración de seguridad según el entorno.
- Protección CSRF en formularios.
- `LoginRequiredMiddleware` para restringir vistas privadas.
- Control de acceso mediante roles y permisos.
- Verificación de correo electrónico.
- Recuperación y cambio de contraseña.
- Cierre de sesión mediante solicitudes POST.
- Acceso restringido a documentos de proveedores.
- Acceso restringido a documentos de viaje.
- Uso de una pasarela simulada sin almacenamiento de datos de tarjetas.

En desarrollo, los correos electrónicos pueden visualizarse en la consola del servidor.

## Estructura del proyecto

```text
config/
  settings/
    base.py
    dev.py
    prod.py

apps/
  core/          Funcionalidades compartidas, permisos, CRUD y PDF
  accounts/      Usuarios, autenticación, perfiles y roles
  destinations/  Países, categorías, destinos y fotografías
  suppliers/     Proveedores y documentos
  hotels/        Hoteles, habitaciones y tarifas
  flights/       Vuelos y disponibilidad
  packages/      Paquetes turísticos, catálogo y comparación
  reservations/  Reservas, pasajeros, clientes, itinerarios y confirmaciones
  payments/      Pagos, cuotas, facturas, reembolsos y caja

templates/       Plantillas HTML
static/          Archivos CSS, JavaScript y recursos estáticos
media/           Archivos cargados
docs/            Documentación y esquema de base de datos
manage.py        Administración del proyecto Django
requirements.txt Dependencias
```

## Base de datos

El proyecto utiliza PostgreSQL y modelos Django con nombres de tablas definidos mediante `db_table`.

El archivo `docs/estropical_schema.sql` describe el esquema general previsto para los seis Sprints.

**No ejecutar manualmente el esquema SQL completo**, porque las tablas y los objetos de base de datos deben gestionarse mediante las migraciones de Django.

### Funciones, triggers y vistas

| Objeto | Migración | Funcionalidad |
|---|---|---|
| `trg_reserva_cupos` y `fn_ajustar_cupos()` | `reservations/0002` | Control de cupos y asientos al reservar, modificar o cancelar |
| `fn_penalidad_cancelacion` | `payments/0002` | Cálculo de penalidades de cancelación |
| `fn_cerrar_caja` | `payments/0002` | Consolidación de movimientos de caja |
| `v_saldo_reserva` | `payments/0002` | Consulta de saldos y cuentas por cobrar |

Las actualizaciones administrativas de disponibilidad y los ajustes realizados por los triggers de reservas deben comprobarse conjuntamente después de la integración.

## Funcionalidades de los Sprints 3 y 4

### Reservas

- Registro y consulta de reservas.
- Modificación y cancelación de reservas.
- Gestión de clientes y pasajeros.
- Confirmaciones de proveedores.
- Documentos de viaje.
- Generación de itinerarios.
- Procesamiento de reservas expiradas.

### Pagos y facturación

- Pagos mediante una pasarela simulada.
- Pagos en ventanilla.
- Gestión de cuotas.
- Estados de cuenta.
- Facturas académicas en PDF.
- Reembolsos.
- Conciliación de pagos.
- Cuentas por cobrar.
- Pagos a proveedores.
- Cierre de caja.

Las facturas generadas no representan facturación electrónica oficial del Servicio de Impuestos Nacionales.

### Promociones y parámetros

Los modelos `Promocion` y `ParametroSistema` se incorporaron anticipadamente en `apps/reservations` porque son utilizados por las reservas y los pagos.

La administración completa de promociones y cupones corresponde al CU-50 del Sprint 6.

Los parámetros de penalización, plazos de pago y cuotas pueden gestionarse mediante Django admin según la implementación existente.

### Pasarela de pagos simulada

El sistema no realiza cobros bancarios reales ni almacena datos de tarjetas.

Los números de prueba documentados por el módulo son:

- Tarjeta aprobada: `4111 1111 1111 1111`
- Tarjeta rechazada: `4000 0000 0000 0002`

Los pagos QR también son simulados.

### Conciliación

La conciliación permite comparar referencias y montos registrados con un archivo CSV que utiliza las columnas:

```csv
referencia,monto
```

## Funcionalidades pendientes y verificaciones

La integración de las ramas no garantiza por sí sola que todas las funcionalidades estén completas o sean compatibles.

Se debe verificar:

- CU-08: gestión de fotografías de destinos.
- CU-12: asociación de servicios, hoteles, vuelos y actividades a paquetes.
- CU-13: carga, validación y revisión de documentos de proveedores.
- CU-14: gestión de tipos de habitación y tarifas.
- CU-16: actualización de disponibilidad.
- CU-17: confirmación de servicios con proveedores.
- Compatibilidad entre las migraciones y los modelos de los cuatro Sprints.
- Funcionamiento de rutas, permisos y menús.
- Pruebas automatizadas de Django.
- Diseño final de la página principal.
- Configuración de producción: SMTP, `ALLOWED_HOSTS`, HTTPS y acceso seguro a archivos.

Los puntos anteriores son verificaciones pendientes, no afirmaciones de que las funcionalidades estén ausentes.

## Sprints 5 y 6

### Sprint 5: personalización, inteligencia artificial y reportes

- CU-38: gestionar preferencias de viaje.
- CU-39: generar recomendaciones personalizadas con inteligencia artificial.
- CU-40: generar reportes de ventas en PDF y Excel.
- CU-41: generar reportes de reservas y proveedores.
- CU-42: generar reportes de facturación y pagos.
- CU-43: consultar indicadores mediante un dashboard.
- CU-44: gestionar notificaciones.

### Sprint 6: atención al cliente y administración

- CU-45: enviar solicitudes de soporte.
- CU-46: gestionar solicitudes de soporte.
- CU-47: registrar valoraciones y reseñas.
- CU-48: moderar reseñas.
- CU-49: gestionar destinos favoritos.
- CU-50: gestionar promociones y cupones.
- CU-51: consultar registros de auditoría.
- CU-52: administrar parámetros del sistema y respaldos.

Estas funcionalidades se desarrollarán sobre los módulos integrados, reutilizando los modelos existentes y evitando duplicar tablas o alterar las funciones implementadas por los demás integrantes.

## Consideraciones

El sistema es un proyecto académico. No incluye emisión real de boletos, cobros bancarios reales, facturación electrónica oficial ni conexión en tiempo real con sistemas externos de aerolíneas y hoteles.

Antes de considerar finalizada la integración, se deben ejecutar las comprobaciones de Django y revisar los resultados de las pruebas.
