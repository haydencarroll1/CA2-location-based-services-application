from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .models import Favorite


class ProfileView(LoginRequiredMixin, TemplateView):
    # shows user their saved favorites

    template_name = "profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        favorites = (
            Favorite.objects.filter(user=user)
            .select_related("amenity")
            .order_by("-created_at")
        )
        context["favorites"] = favorites
        return context
