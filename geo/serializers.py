from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Amenity, Area, Route

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
