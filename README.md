# Estropical.com · Tropical Tours Ltda.

Sistema web de venta de viajes (proyecto académico). **Cubre los Sprints 1 a 4** (acceso y destinos, catálogo y proveedores, reservas e itinerarios, pagos y facturación).
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

Pruebas: `python manage.py test` (17 pruebas de los Sprints 1-2 + 27 de los Sprints 3-4: reservas, cupos, cupones,
cancelación con penalidad, pagos, cuotas, facturas, conciliación y cierre de caja). Necesitan PostgreSQL.

Tareas programadas (opcional): `python manage.py expirar_reservas` cada hora marca como expiradas las reservas
pendientes sin pago y libera sus cupos (también se ejecuta solo al listar reservas o intentar pagar).

## Accesos y seguridad

| Visitante | Cómo se identifica | Qué puede hacer |
|---|---|---|
| Sin cuenta | sin sesión | Inicio, catálogo de destinos y paquetes (ver/filtrar/comparar), registro, login, recuperar contraseña |
| Cliente | grupo `Cliente` | Todo lo anterior + su perfil, reservar, sus reservas, pagos, estado de cuenta, facturas e itinerarios |
| Administrador | grupo `Administrador` o superusuario | Todo lo anterior + panel `/gestion/...` (usuarios, destinos, paquetes, proveedores, hoteles, vuelos, reservas, clientes, caja, facturas, reembolsos). Cumple también el papel de cajero |

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
apps/reservations/  Reserva, Pasajero, DocumentoViaje, ConfirmacionProveedor,
                    Promocion, ParametroSistema; itinerario PDF                       (S2 CU-17, S3 CU-18..25)
apps/payments/      Cuota, Pago, Reembolso, Factura, PagoProveedor, CierreCaja,
                    SaldoReserva (vista v_saldo_reserva)                              (S4 CU-26..37)
apps/core/pdf.py    generador de PDF sin librerías externas (itinerarios, comprobantes, facturas)
templates/ static/ media/            plantillas, CSS/JS, archivos subidos
docs/               estropical_schema.sql (esquema completo, S1-S6), diagrama ER (.drawio/.png)
```

Los modelos usan `db_table` y nombres de columna del `docs/estropical_schema.sql`. Las funciones, el trigger y
la vista del esquema que necesitan los Sprints 3 y 4 se crean con migraciones `RunSQL` (no ejecutar el .sql a mano):

| Objeto SQL | Migración | Uso |
|---|---|---|
| `trg_reserva_cupos` / `fn_ajustar_cupos()` | `reservations/0002` | descuenta y devuelve cupos y asientos al reservar, modificar, cancelar o expirar (evita sobreventa) |
| `fn_penalidad_cancelacion(reserva)` | `payments/0002` | % de penalidad según días a la salida y monto a reembolsar (CU-21) |
| `fn_cerrar_caja(fecha, perfil)` | `payments/0002` | consolida ingresos y egresos del día (CU-37) |
| `v_saldo_reserva` | `payments/0002` | estado de cuenta y cuentas por cobrar (CU-29, CU-35) |

Notas de los Sprints 3 y 4:
* `promocion` y `parametro_sistema` (Sprint 6 en el esquema) se crean ya en `apps/reservations` porque los cupones
  (CU-18) y la penalidad (CU-21) los necesitan. Los cupones se crean por ahora desde Django admin; la pantalla de
  gestión completa es el CU-50 del Sprint 6. Los % de penalidad, las horas para pagar y el máximo de cuotas se
  cambian en Django admin → Parámetros del sistema.
* Los pagos en línea usan una **pasarela simulada** (no hay cobro real ni se guardan datos de tarjeta, RNF-05).
  Tarjeta de prueba aprobada `4111 1111 1111 1111`, rechazada `4000 0000 0000 0002`; QR siempre se aprueba.
* Las facturas son documentos PDF académicos (no facturación electrónica del SIN, fuera del alcance).
* Conciliación (CU-34): se sube un CSV `referencia,monto` y se compara con `referencia_transaccion` o el N° de comprobante.
* Los documentos de viaje se descargan por una vista con control de acceso, con nombres de archivo aleatorios.
* Si `python manage.py makemigrations --check` detecta diferencias en `reservations` o `payments`, generar la
  migración (solo serán ajustes de formato; las tablas ya coinciden con el esquema).

## Pendiente por completar (buscar `TODO` en el código)

- CU-08: formset de fotos del destino (subir, ordenar, elegir portada).
- CU-12: formsets para asignar hoteles, vuelos, servicios y actividades a un paquete.
- CU-13: carga y validación de documentos del proveedor.
- CU-14: gestión de tipos de habitación y tarifas por hotel.
- CU-16: actualizar disponibilidad (habitaciones, asientos, cupos).
- Portada (`core/home.html`), diseño final, validar filtros del catálogo, reenvío del correo de verificación.
- Producción: SMTP real, `ALLOWED_HOSTS`, servir `/media/`, límite de intentos de login.
