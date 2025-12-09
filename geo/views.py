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

# basic crud stuff for the api
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

# spatial query endpoints for map interactions
class NearestAmenities(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # get lat/lng from url
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
        except (TypeError, ValueError):
            raise ValidationError("Query params 'lat' and 'lng' are required floats.")

        # can also filter by area if needed
        area = None
        area_id = request.query_params.get("area_id")
        if area_id:
            try:
                area = Area.objects.get(pk=area_id)
            except Area.DoesNotExist:
                raise ValidationError("Area not found.")
        
        # how many results to return
        limit_param = request.query_params.get("limit", "10")
        try:
            limit = int(limit_param)
        except (TypeError, ValueError):
            raise ValidationError("Query param 'limit' must be a positive integer.")
        if limit <= 0:
            raise ValidationError("Query param 'limit' must be greater than zero.")
        
        # dont let them ask for too many or itll be slow
        limit = min(limit, 100)
        
        # make a point and use postgis to calc distances
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
        # grab area id
        area_id = request.query_params.get("area_id")
        if not area_id:
            raise ValidationError("Query param 'area_id' is required.")
        
        # get the area polygon
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            raise ValidationError("Area not found.")
        
        # postgis within query - finds points inside polygon
        qs = Amenity.objects.filter(location__within=area.boundary)
        serializer = AmenityGeoSerializer(qs, many=True)
        return Response(serializer.data)

class RoutesIntersectingArea(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # get area from params
        area_id = request.query_params.get("area_id")
        if not area_id:
            raise ValidationError("Query param 'area_id' is required.")
        
        # load area
        try:
            area = Area.objects.get(pk=area_id)
        except Area.DoesNotExist:
            raise ValidationError("Area not found.")
        
        # postgis intersects - routes that cross area
        qs = Route.objects.filter(path__intersects=area.boundary)
        serializer = RouteGeoSerializer(qs, many=True)
        return Response(serializer.data)

class AmenitiesWithinRadius(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # get coords and radius, default 1km
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
            km = float(request.query_params.get("km", "1.0"))
        except (TypeError, ValueError):
            raise ValidationError("Params 'lat','lng','km' are required floats.")

        if km <= 0:
            raise ValidationError("Param 'km' must be greater than zero.")

        # can also filter by area if needed
        area = None
        area_id = request.query_params.get("area_id")
        if area_id:
            try:
                area = Area.objects.get(pk=area_id)
            except Area.DoesNotExist:
                raise ValidationError("Area not found.")
        
        # use postgis distance filter
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
        # get lat/lng and km from params
        try:
            lat = float(request.query_params.get("lat"))
            lng = float(request.query_params.get("lng"))
            km = float(request.query_params.get("km", "1.0"))
        except (TypeError, ValueError):
            raise ValidationError("Params 'lat','lng','km' are required floats.")
        
        # same as above but for routes
        origin = Point(lng, lat, srid=4326)
        qs = Route.objects.filter(path__distance_lte=(origin, D(km=km)))
        serializer = RouteGeoSerializer(qs, many=True)
        return Response(serializer.data)


class AreaDensity(APIView):
    """Get areas with amenity counts for choropleth visualization"""
    permission_classes = [AllowAny]
    def get(self, request):
        # optional category filter
        category = request.query_params.get("category")
        
        # get all areas with amenity counts using spatial join
        from django.db.models import Count, Q
        
        # Build filter for amenities within each area's boundary
        filter_kwargs = {}
        if category:
            filter_kwargs['category'] = category
        
        areas = Area.objects.all()
        result = []
        
        for area in areas:
            # Count amenities within this area's boundary
            qs = Amenity.objects.filter(location__within=area.boundary)
            if category:
                qs = qs.filter(category=category)
            count = qs.count()
            
            # Serialize area with count
            area_data = AreaGeoSerializer(area).data
            area_data['properties']['amenity_count'] = count
            result.append(area_data)
        
        return Response({
            'type': 'FeatureCollection',
            'features': result
        })


class SearchAmenities(APIView):
    """Search amenities by name, operator, cuisine, or address"""
    permission_classes = [AllowAny]
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            raise ValidationError("Query param 'q' must be at least 2 characters.")
        
        # optional category filter
        category = request.query_params.get("category")
        
        # limit results
        limit_param = request.query_params.get("limit", "50")
        try:
            limit = min(int(limit_param), 100)
        except (TypeError, ValueError):
            limit = 50
        
        # search across multiple fields using icontains
        from django.db.models import Q
        qs = Amenity.objects.filter(
            Q(name__icontains=query) |
            Q(operator__icontains=query) |
            Q(cuisine__icontains=query) |
            Q(addr_street__icontains=query)
        )
        
        if category:
            qs = qs.filter(category=category)
        
        qs = qs[:limit]
        serializer = AmenityGeoSerializer(qs, many=True)
        return Response(serializer.data)
