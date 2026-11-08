"""python manage.py expirar_reservas  -> programarlo cada hora (cron / Programador de tareas)."""
from django.core.management.base import BaseCommand

from apps.reservations.services import expirar_reservas_vencidas


class Command(BaseCommand):
    help = "Marca como expiradas las reservas pendientes sin pago cuyo plazo venció (libera cupos)."

    def handle(self, *args, **options):
        n = expirar_reservas_vencidas()
        self.stdout.write(self.style.SUCCESS(f"{n} reserva(s) expirada(s)."))
