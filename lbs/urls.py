# url routing
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from geo.views import (
    AmenityViewSet, AreaViewSet, RouteViewSet, FavoriteViewSet,
    NearestAmenities, AmenitiesWithinArea, RoutesIntersectingArea,
    AmenitiesWithinRadius, RoutesWithinRadius
)

router = DefaultRouter()
router.register(r"amenities", AmenityViewSet, basename="amenity")
router.register(r"areas", AreaViewSet, basename="area")
router.register(r"routes", RouteViewSet, basename="route")
router.register(r"favorites", FavoriteViewSet, basename="favorite")

urlpatterns = [
    path("admin/", admin.site.urls),
    # allauth for google login
    path("accounts/", include("allauth.urls")),
    path("api/", include(router.urls)),
    path("api/amenities/nearest", NearestAmenities.as_view()),
    path("api/amenities/within", AmenitiesWithinArea.as_view()),
    path("api/amenities/in-area", AmenitiesWithinArea.as_view()),
    path("api/amenities/radius", AmenitiesWithinRadius.as_view()),
    path("api/routes/intersecting", RoutesIntersectingArea.as_view()),
    path("api/routes/radius", RoutesWithinRadius.as_view()),
    path("", include("geo.urls")),
]
