"""Rotas de tags da API v1 (prefixo /api/v1/tags/) — M5."""

from django.urls import path

from . import views

app_name = "tags"

urlpatterns = [
    path("", views.TagListCreateView.as_view(), name="list"),
]
