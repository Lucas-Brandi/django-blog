"""Rotas da API REST versão 1 (prefixo /api/v1/)."""

from django.urls import path

from config import api

app_name = "api-v1"

urlpatterns = [
    path("health/", api.health, name="health"),
]
