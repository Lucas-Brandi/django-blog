"""Rotas de posts da API v1 (prefixo /api/v1/posts/)."""

from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("", views.PostListCreateView.as_view(), name="list"),
    path("<int:pk>/", views.PostDetailView.as_view(), name="detail"),
]
