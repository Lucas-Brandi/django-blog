"""Rotas de comentários da API v1 (prefixo /api/v1/comments/) — M6."""

from django.urls import path

from . import views

app_name = "comments"

urlpatterns = [
    path("<int:pk>/", views.CommentDetailView.as_view(), name="detail"),
]
