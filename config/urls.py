"""
URL configuration for django_project project.

O backend é exclusivamente uma API REST (JSON) + Django Admin. As páginas HTML
e suas rotas foram removidas em M9; o front é uma aplicação independente.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API REST (JSON) consumida pelo front React.
    path("api/v1/", include("config.api_urls")),
    # Documentação OpenAPI (M7): schema cru + Swagger UI.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
