
import csv
from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from apps.destinations.models import (
    Pais,
    Categoria,
    Destino,
)
from apps.destinations.wikimedia import (
    buscar_fotografias,
    guardar_portada,
)


COLUMNAS = {
    "pais_codigo",
    "pais_nombre",
    "categoria",
    "nombre",
    "codigo_iata",
    "descripcion",
}


class Command(BaseCommand):
    help = (
        "Importa destinos desde CSV y busca fotografías "
        "en Wikimedia Commons."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            required=True,
            help="Ruta del CSV.",
        )
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Comprueba los datos sin guardarlos.",
        )
        parser.add_argument(
            "--actualizar",
            action="store_true",
            help="Actualiza destinos existentes.",
        )
        parser.add_argument(
            "--auto-fotos",
            action="store_true",
            help="Busca fotografías automáticamente.",
        )
        parser.add_argument(
            "--limite",
            type=int,
            default=0,
            help="Máximo de filas a procesar; 0 significa todas.",
        )

    def handle(self, *args, **options):
        ruta = Path(options["csv"]).resolve()

        if not ruta.is_file():
            raise CommandError(
                f"No existe el CSV: {ruta}"
            )

        try:
            with ruta.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as archivo:
                lector = csv.DictReader(archivo)

                if not lector.fieldnames:
                    raise CommandError("El CSV está vacío.")

                faltantes = COLUMNAS - set(lector.fieldnames)

                if faltantes:
                    raise CommandError(
                        "Faltan columnas: "
                        + ", ".join(sorted(faltantes))
                    )

                filas = list(lector)

        except UnicodeError as exc:
            raise CommandError(
                "El CSV debe estar guardado en UTF-8."
            ) from exc

        if options["limite"] < 0:
            raise CommandError(
                "El límite no puede ser negativo."
            )

        if options["limite"]:
            filas = filas[:options["limite"]]

        vistos = set()

        # Validación inicial antes de escribir en PostgreSQL.
        for numero, fila in enumerate(filas, start=2):
            if None in fila:
                raise CommandError(
                    f"Fila {numero}: revisa las comas del CSV."
                )

            for campo in COLUMNAS:
                fila[campo] = (
                    fila.get(campo) or ""
                ).strip()

            for campo in (
                "pais_codigo",
                "pais_nombre",
                "categoria",
                "nombre",
            ):
                if not fila[campo]:
                    raise CommandError(
                        f"Fila {numero}: falta {campo}."
                    )

            fila["pais_codigo"] = (
                fila["pais_codigo"].upper()
            )
            fila["codigo_iata"] = (
                fila["codigo_iata"].upper()
            )

            if (
                len(fila["pais_codigo"]) != 2
                or not fila["pais_codigo"].isalpha()
            ):
                raise CommandError(
                    f"Fila {numero}: país ISO inválido."
                )

            if fila["codigo_iata"] and (
                len(fila["codigo_iata"]) != 3
                or not fila["codigo_iata"].isalpha()
            ):
                raise CommandError(
                    f"Fila {numero}: IATA inválido."
                )

            if (
                len(fila["pais_nombre"]) > 80
                or len(fila["categoria"]) > 50
                or len(fila["nombre"]) > 100
            ):
                raise CommandError(
                    f"Fila {numero}: un nombre supera "
                    "la longitud permitida."
                )

            clave = (
                fila["pais_codigo"],
                fila["nombre"].casefold(),
            )

            if clave in vistos:
                raise CommandError(
                    f"Fila {numero}: destino duplicado "
                    "en el CSV."
                )

            vistos.add(clave)

        if options["simular"]:
            for fila in filas:
                self.stdout.write(
                    f"VALIDADO: {fila['nombre']} "
                    f"({fila['pais_nombre']})"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Simulación correcta: {len(filas)} filas. "
                    "No se guardó nada."
                )
            )
            return

        creados = 0
        actualizados = 0
        omitidos = 0
        con_foto = 0
        pendientes = []

        for fila in filas:
            nombre = fila["nombre"]

            try:
                with transaction.atomic():
                    pais, _ = Pais.objects.get_or_create(
                        codigo_iso=fila["pais_codigo"],
                        defaults={
                            "nombre": fila["pais_nombre"]
                        },
                    )

                    categoria, _ = (
                        Categoria.objects.get_or_create(
                            nombre=fila["categoria"]
                        )
                    )

                    destino = Destino.objects.filter(
                        pais=pais,
                        nombre__iexact=nombre,
                    ).first()

                    if destino:
                        if options["actualizar"]:
                            destino.categoria = categoria
                            destino.descripcion = (
                                fila["descripcion"]
                            )
                            destino.codigo_iata = (
                                fila["codigo_iata"] or None
                            )
                            destino.activo = True
                            destino.save()
                            actualizados += 1
                        else:
                            omitidos += 1
                    else:
                        destino = Destino.objects.create(
                            pais=pais,
                            categoria=categoria,
                            nombre=nombre,
                            codigo_iata=(
                                fila["codigo_iata"] or None
                            ),
                            descripcion=fila["descripcion"],
                            activo=True,
                        )
                        creados += 1

                self.stdout.write(f"OK: {nombre}")

            except Exception as exc:
                pendientes.append(
                    f"{nombre}: error de datos ({exc})"
                )
                self.stderr.write(
                    f"ERROR: {nombre}: {exc}"
                )
                continue

            if not options["auto_fotos"]:
                continue

            if destino.portada:
                continue

            try:
                fotos = buscar_fotografias(
                    destino.nombre,
                    destino.pais.nombre,
                    limite=5,
                )

                if not fotos:
                    pendientes.append(
                        f"{nombre}: sin fotografías compatibles"
                    )
                    continue

                # Primera fotografía como portada provisional.
                # Revisarla desde la administración.
                guardar_portada(
                    destino,
                    fotos[0],
                    reemplazar=False,
                )
                con_foto += 1

            except Exception as exc:
                pendientes.append(
                    f"{nombre}: fotografía pendiente ({exc})"
                )
                self.stderr.write(
                    f"FOTO PENDIENTE: {nombre}: {exc}"
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("IMPORTACIÓN FINALIZADA")
        )
        self.stdout.write(f"Creados: {creados}")
        self.stdout.write(f"Actualizados: {actualizados}")
        self.stdout.write(f"Omitidos: {omitidos}")
        self.stdout.write(f"Fotos asignadas: {con_foto}")
        self.stdout.write(
            f"Pendientes de revisión: {len(pendientes)}"
        )

        if pendientes:
            self.stdout.write("")
            self.stdout.write("REVISAR:")
            for pendiente in pendientes:
                self.stdout.write(f"- {pendiente}")
