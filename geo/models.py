from django.contrib.gis.db import models
from django.conf import settings

class Area(models.Model):
    name = models.CharField(max_length=100, unique=True)
    boundary = models.PolygonField(srid=4326)

    def __str__(self):
        return self.name


class Route(models.Model):
    name = models.CharField(max_length=100, unique=True)
    path = models.LineStringField(srid=4326)

    def __str__(self):
        return self.name


class Amenity(models.Model):
    CATEGORIES = [
        ("cafe", "Cafe"),
        ("gym", "Gym"),
        ("atm", "ATM"),
        ("park", "Park"),
        ("shop", "Shop"),
    ]
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    location = models.PointField(srid=4326)
    description = models.TextField(blank=True, default="")
    source_ref = models.CharField(max_length=64, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.category})"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "amenity")

    def __str__(self):
        return f"{self.user} → {self.amenity}"
