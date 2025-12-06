from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError

from .models import Amenity, Area, Route, Favorite
from .serializers import AmenityGeoSerializer, AreaGeoSerializer, RouteGeoSerializer, FavoriteSerializer

# ---- CRUD ----
class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenityGeoSerializer
    permission_classes = [AllowAny]

class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaGeoSerializer
    permission_classes = [AllowAny]

class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteGeoSerializer
    permission_classes = [AllowAny]


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related("amenity")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# ---- Spatial queries ----
class NearestAmenities(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # grab lat lng from url params and convert to floats
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
        except (TypeError, ValueError):
            raise ValidationError("Query params 'lat' and 'lng' are required floats.")

        # optional area filter
        area = None
        area_id = request.query_params.get("area_id")
        if area_id:
            try:
                area = Area.objects.get(pk=area_id)
            except Area.DoesNotExist:
                raise ValidationError("Area not found.")
        
        # get the limit param or default to 10 results
        limit_param = request.query_params.get("limit", "10")
        try:
            limit = int(limit_param)
        except (TypeError, ValueError):
            raise ValidationError("Query param 'limit' must be a positive integer.")
        if limit <= 0:
            raise ValidationError("Query param 'limit' must be greater than zero.")
        
        # cap at 100 to avoid performance issues
        limit = min(limit, 100)
        
        # create point from coords and annotate each amenity with distance from that point
        origin = Point(lng, lat, srid=4326)
        qs = Amenity.objects.all()
        if area:
            qs = qs.filter(location__within=area.boundary)
        qs = qs.annotate(distance=Distance("location", origin)).order_by("distance")[:limit]
        
        serializer = AmenityGeoSerializer(qs, many=True)
        return Response(serializer.data)

class AmenitiesWithinArea(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # get the area id from params
        area_id = request.query_params.get("area_id")
        if not area_id:
            raise ValidationError("Query param 'area_id' is required.")
        
        # fetch the area polygon from db
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            raise ValidationError("Area not found.")
        
        # use postgis within lookup to find all amenities inside the polygon
        qs = Amenity.objects.filter(location__within=area.boundary)
        serializer = AmenityGeoSerializer(qs, many=True)
        return Response(serializer.data)

class RoutesIntersectingArea(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # get area id from query params
        area_id = request.query_params.get("area_id")
        if not area_id:
            raise ValidationError("Query param 'area_id' is required.")
        
        # fetch the area polygon
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            raise ValidationError("Area not found.")
        
        # find all routes that cross or touch the area boundary using postgis intersects
        qs = Route.objects.filter(path__intersects=area.boundary)
        serializer = RouteGeoSerializer(qs, many=True)
        return Response(serializer.data)

class AmenitiesWithinRadius(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # parse lat lng and radius from params with km defaulting to 1
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
            km = float(request.query_params.get("km", "1.0"))
        except (TypeError, ValueError):
            raise ValidationError("Params 'lat','lng','km' are required floats.")

        if km <= 0:
            raise ValidationError("Param 'km' must be greater than zero.")

        # optional area filter
        area = None
        area_id = request.query_params.get("area_id")
        if area_id:
            try:
                area = Area.objects.get(pk=area_id)
            except Area.DoesNotExist:
                raise ValidationError("Area not found.")
        
        # create point and filter amenities within distance using postgis
        origin = Point(lng, lat, srid=4326)
        qs = Amenity.objects.all()
        if area:
            qs = qs.filter(location__within=area.boundary)
        qs = qs.annotate(distance=Distance("location", origin)).filter(location__distance_lte=(origin, D(km=km))).order_by("distance")
        serializer = AmenityGeoSerializer(qs, many=True)
        return Response(serializer.data)

class RoutesWithinRadius(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # get center point and search radius from url params
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
            km = float(request.query_params.get("km", "1.0"))
        except (TypeError, ValueError):
            raise ValidationError("Params 'lat','lng','km' are required floats.")
        
        # find all routes within the specified distance from center point
        origin = Point(lng, lat, srid=4326)
        qs = Route.objects.filter(path__distance_lte=(origin, D(km=km)))
        serializer = RouteGeoSerializer(qs, many=True)
        return Response(serializer.data)
