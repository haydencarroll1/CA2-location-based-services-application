"""
Import route GeoJSON files into the database.
"""

import json
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import LineString
from django.core.management.base import BaseCommand, CommandError

from geo.models import Route


class Command(BaseCommand):
    help = "Import route GeoJSON files into the Route table."

    def add_arguments(self, parser):
        parser.add_argument(
            "paths",
            nargs="*",
            help="Optional paths to GeoJSON files. Defaults to geo/data/routes_*.geojson.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing Route records before import.",
        )

    def handle(self, *args, **options):
        base_dir = Path(settings.BASE_DIR)
        data_dir = base_dir / "geo" / "data"

        raw_paths = options["paths"]
        if raw_paths:
            files = []
            for raw in raw_paths:
                candidate = Path(raw)
                if not candidate.is_absolute():
                    candidate = base_dir / raw
                if not candidate.exists():
                    candidate = data_dir / raw
                if not candidate.exists():
                    raise CommandError(f"GeoJSON file not found: {raw}")
                files.append(candidate)
        else:
            files = sorted(data_dir.glob("routes_*.geojson"))

        if not files:
            raise CommandError("No GeoJSON files found to import.")

        if options["reset"]:
            deleted, _ = Route.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing routes."))

        imported = 0
        skipped = 0

        for geojson_path in files:
            with geojson_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            features = payload.get("features", [])
            if not features:
                self.stdout.write(self.style.WARNING(f"{geojson_path.name}: no features found."))
                continue

            for index, feature in enumerate(features, start=1):
                geometry = feature.get("geometry")
                if not geometry:
                    skipped += 1
                    continue

                properties = feature.get("properties") or {}
                base_name = (
                    properties.get("Name")
                    or properties.get("name")
                    or f"{geojson_path.stem.replace('_', ' ').title()} Feature {index}"
                )

                geom_type = geometry.get("type")
                coordinates = geometry.get("coordinates")
                if not coordinates:
                    skipped += 1
                    continue

                segments = []
                if geom_type == "LineString":
                    segments = [coordinates]
                elif geom_type == "MultiLineString":
                    segments = [coords for coords in coordinates if len(coords) >= 2]
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"{geojson_path.name} feature {index}: unsupported geometry {geom_type}, skipping."
                        )
                    )
                    skipped += 1
                    continue

                if not segments:
                    skipped += 1
                    continue

                for segment_idx, segment in enumerate(segments, start=1):
                    if len(segment) < 2:
                        skipped += 1
                        continue

                    try:
                        line = LineString(segment, srid=4326)
                    except TypeError as exc:
                        raise CommandError(
                            f"{geojson_path.name} feature {index} segment {segment_idx}: {exc}"
                        ) from exc

                    name = base_name
                    if len(segments) > 1:
                        name = f"{base_name} (Segment {segment_idx})"

                    route, created = Route.objects.update_or_create(
                        name=name,
                        defaults={"path": line},
                    )
                    imported += 1
                    action = "Created" if created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"{action} route: {name}"))

        if imported == 0:
            raise CommandError("No routes were imported.")

        summary = f"Imported or updated {imported} route segments"
        if skipped:
            summary += f"; skipped {skipped}."
        else:
            summary += "."
        self.stdout.write(self.style.SUCCESS(summary))

