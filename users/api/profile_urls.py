"""Rotas de perfil da API v1 (prefixo /api/v1/users/)."""

from django.urls import path

from . import profile_views

app_name = "users"

urlpatterns = [
    path("me/", profile_views.MeView.as_view(), name="me"),
    path("me/image/", profile_views.MeImageView.as_view(), name="me_image"),
    # Perfil público por username (deixado por último para não capturar "me").
    path("<str:username>/", profile_views.PublicProfileView.as_view(), name="public"),
]
