"""Rotas da API REST versão 1 (prefixo /api/v1/)."""

from django.urls import include, path

from config import api

app_name = "api-v1"

urlpatterns = [
    path("health/", api.health, name="health"),
    path("auth/", include("users.api.urls")),
    path("users/", include("users.api.profile_urls")),
    path("posts/", include("blog.api.urls")),
]
