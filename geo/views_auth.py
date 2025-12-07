from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .models import Favorite


class SignupView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/signup.html"
    # If this view is used, redirect to allauth's login
    success_url = reverse_lazy("account_login")


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Simple profile page where a signed-in user can see
    their basic account details and saved favourites.
    """

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
