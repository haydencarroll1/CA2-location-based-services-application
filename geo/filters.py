from django_filters import rest_framework as filters
from .models import Amenity

class AmenityFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    category = filters.CharFilter(field_name="category", lookup_expr="iexact")

    class Meta:
        model = Amenity
        fields = ["category", "name"]
