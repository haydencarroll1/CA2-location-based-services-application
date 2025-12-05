from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Amenity, Area, Route, Favorite

class AmenityGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Amenity
        geo_field = "location"
        fields = ("id", "name", "category", "description")

class AreaGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Area
        geo_field = "boundary"
        fields = ("id", "name")

class RouteGeoSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Route
        geo_field = "path"
        fields = ("id", "name")


class FavoriteSerializer(serializers.ModelSerializer):
    amenity = AmenityGeoSerializer(read_only=True)
    amenity_id = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(), source="amenity", write_only=True
    )
    amenity_pk = serializers.IntegerField(source="amenity.id", read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "amenity", "amenity_id", "amenity_pk", "created_at")
