"""
URL configuration for lbs project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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
    # allauth handles login / logout / signup / social logins
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
