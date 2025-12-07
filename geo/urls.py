from django.urls import path
from django.views.generic import TemplateView

from .views_auth import ProfileView

urlpatterns = [
    path("", TemplateView.as_view(template_name="map.html"), name="map"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
