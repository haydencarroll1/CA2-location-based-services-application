"""
Django management command to import amenities from OpenStreetMap into the database.

This command fetches amenities from the Overpass API for each Area polygon stored
in the database, then creates Amenity records tagged with source_ref to avoid duplicates.

Usage:
    python manage.py import_osm_amenities                    # Import for all areas
    python manage.py import_osm_amenities --area "Drumcondra" # Import for specific area
    python manage.py import_osm_amenities --reset            # Clear OSM data and reimport
    python manage.py import_osm_amenities --dry-run          # Preview without saving
"""

import time
import urllib.request
import urllib.parse
import json

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from geo.models import Amenity, Area


class Command(BaseCommand):
    help = "Import amenities from OpenStreetMap Overpass API for each Area in the database."

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    TIMEOUT = 30
    DELAY_BETWEEN_REQUESTS = 2  # seconds - be nice to the API

    # Map OSM tags to our categories
    CATEGORY_MAPPING = {
        # Cafés / food / drink
        "cafe": "cafe",
        "restaurant": "cafe",
        "fast_food": "cafe",
        "ice_cream": "cafe",
        "pub": "cafe",
        "bar": "cafe",
        # Shops
        "convenience": "shop",
        "supermarket": "shop",
        "department_store": "shop",
        "mall": "shop",
        "marketplace": "shop",
        # Gyms
        "fitness_centre": "gym",
        "gym": "gym",
        # ATMs / Banks
        "atm": "atm",
        "bank": "atm",
        # Parks
        "park": "park",
        "garden": "park",
        "recreation_ground": "park",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--area",
            type=str,
            help="Import only for a specific area name",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing OSM-sourced amenities before import",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be imported without saving",
        )

    def handle(self, *args, **options):
        area_name = options.get("area")
        reset = options.get("reset")
        dry_run = options.get("dry_run")

        # Get areas to process
        if area_name:
            areas = Area.objects.filter(name__icontains=area_name)
            if not areas.exists():
                self.stderr.write(self.style.ERROR(f"No area found matching '{area_name}'"))
                return
        else:
            areas = Area.objects.all()

        if not areas.exists():
            self.stderr.write(self.style.ERROR("No areas in database. Load areas first."))
            return

        self.stdout.write(f"Found {areas.count()} area(s) to process")

        # Reset if requested
        if reset and not dry_run:
            deleted, _ = Amenity.objects.filter(source_ref__startswith="osm_").delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing OSM amenities"))

        total_created = 0
        total_skipped = 0

        for area in areas:
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(f"Processing area: {area.name}")
            
            try:
                created, skipped = self.import_for_area(area, dry_run)
                total_created += created
                total_skipped += skipped
                self.stdout.write(
                    self.style.SUCCESS(f"  → Created: {created}, Skipped (duplicates): {skipped}")
                )
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  → Error: {e}"))

            # Be nice to the Overpass API
            if area != list(areas)[-1]:
                self.stdout.write(f"  Waiting {self.DELAY_BETWEEN_REQUESTS}s before next request...")
                time.sleep(self.DELAY_BETWEEN_REQUESTS)

        self.stdout.write(f"\n{'='*50}")
        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(f"TOTAL: {action} {total_created} amenities, skipped {total_skipped} duplicates")
        )

    def import_for_area(self, area, dry_run=False):
        """Fetch and import amenities for a single area."""
        # Get bounding box from area polygon
        bbox = area.boundary.extent  # (minx, miny, maxx, maxy) = (west, south, east, north)
        west, south, east, north = bbox

        # Build Overpass query
        query = self.build_overpass_query(south, west, north, east)
        
        # Fetch from Overpass
        self.stdout.write(f"  Fetching from Overpass API...")
        elements = self.fetch_overpass(query)
        self.stdout.write(f"  Received {len(elements)} elements")

        created = 0
        skipped = 0

        for el in elements:
            result = self.process_element(el, area, dry_run)
            if result == "created":
                created += 1
            elif result == "skipped":
                skipped += 1

        return created, skipped

    def build_overpass_query(self, south, west, north, east):
        """Build Overpass QL query for the bounding box."""
        bbox = f"{south},{west},{north},{east}"
        
        # Query for all our amenity types
        query = f"""
[out:json][timeout:{self.TIMEOUT}];
(
  // Cafes, restaurants, food
  node["amenity"~"cafe|restaurant|fast_food|ice_cream|pub|bar"]({bbox});
  way["amenity"~"cafe|restaurant|fast_food|ice_cream|pub|bar"]({bbox});
  
  // Shops
  node["shop"~"convenience|supermarket|department_store|mall"]({bbox});
  way["shop"~"convenience|supermarket|department_store|mall"]({bbox});
  node["amenity"="marketplace"]({bbox});
  
  // Gyms
  node["amenity"~"fitness_centre|gym"]({bbox});
  way["amenity"~"fitness_centre|gym"]({bbox});
  node["sport"="fitness"]({bbox});
  way["sport"="fitness"]({bbox});
  
  // ATMs and Banks
  node["amenity"~"atm|bank"]({bbox});
  
  // Parks
  node["leisure"~"park|garden|recreation_ground"]({bbox});
  way["leisure"~"park|garden|recreation_ground"]({bbox});
);
out center 500;
"""
        return query

    def fetch_overpass(self, query):
        """Send query to Overpass API and return elements."""
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        
        req = urllib.request.Request(
            self.OVERPASS_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        with urllib.request.urlopen(req, timeout=self.TIMEOUT + 10) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        return result.get("elements", [])

    def process_element(self, el, area, dry_run=False):
        """Process a single OSM element and create an Amenity if valid."""
        # Get coordinates
        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            # For ways/relations, use the center point
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        
        if lat is None or lon is None:
            return None

        # Create point and check if it's actually within the area polygon
        point = Point(lon, lat, srid=4326)
        if not area.boundary.contains(point):
            return None  # Point is in bbox but not in actual polygon

        tags = el.get("tags", {})
        
        # Determine category
        category = self.get_category(tags)
        if not category:
            return None

        # Get name
        name = tags.get("name", "").strip()
        if not name:
            # Skip unnamed amenities
            return None

        # Build source reference
        osm_id = el.get("id")
        source_ref = f"osm_{el.get('type', 'node')}_{osm_id}"

        # Check for duplicate
        if Amenity.objects.filter(source_ref=source_ref).exists():
            return "skipped"

        # Build description from available tags
        description_parts = []
        if tags.get("cuisine"):
            description_parts.append(f"Cuisine: {tags['cuisine']}")
        if tags.get("opening_hours"):
            description_parts.append(f"Hours: {tags['opening_hours']}")
        if tags.get("phone"):
            description_parts.append(f"Phone: {tags['phone']}")
        if tags.get("website"):
            description_parts.append(f"Website: {tags['website']}")
        if tags.get("operator"):
            description_parts.append(f"Operator: {tags['operator']}")
        if tags.get("addr:street"):
            addr = tags.get("addr:street")
            if tags.get("addr:housenumber"):
                addr = f"{tags['addr:housenumber']} {addr}"
            description_parts.append(f"Address: {addr}")
        
        description = " | ".join(description_parts) if description_parts else ""

        if dry_run:
            self.stdout.write(f"    [DRY-RUN] Would create: {name} ({category})")
            return "created"

        # Create the amenity
        Amenity.objects.create(
            name=name[:120],  # Truncate to field max length
            category=category,
            location=point,
            description=description[:500] if description else "",  # Truncate
            source_ref=source_ref,
        )
        return "created"

    def get_category(self, tags):
        """Determine our category from OSM tags."""
        # Check amenity tag
        amenity = tags.get("amenity", "")
        if amenity in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[amenity]

        # Check shop tag
        shop = tags.get("shop", "")
        if shop in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[shop]

        # Check leisure tag
        leisure = tags.get("leisure", "")
        if leisure in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[leisure]

        # Check sport tag
        sport = tags.get("sport", "")
        if sport == "fitness":
            return "gym"

        return None
