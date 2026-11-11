"""Testes da documentação OpenAPI (M7).

Verificam que o schema e o Swagger UI são servidos, que o esquema descreve a
autenticação JWT e que os endpoints da API aparecem no schema gerado.
"""

import pytest
import yaml
from django.urls import reverse
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_schema_endpoint_serves_openapi(client):
    response = client.get(reverse("schema"))
    assert response.status_code == 200
    schema = yaml.safe_load(response.content)
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Django Blog API"


def test_swagger_ui_is_served(client):
    response = client.get(reverse("swagger-ui"))
    assert response.status_code == 200


def test_schema_describes_jwt_auth(client):
    response = client.get(reverse("schema"))
    schemes = yaml.safe_load(response.content)["components"]["securitySchemes"]
    assert "jwtAuth" in schemes
    assert schemes["jwtAuth"]["type"] == "http"
    assert schemes["jwtAuth"]["scheme"] == "bearer"
    assert schemes["jwtAuth"]["bearerFormat"] == "JWT"


def test_all_endpoints_present_in_schema(client):
    response = client.get(reverse("schema"))
    paths = yaml.safe_load(response.content)["paths"]
    expected = {
        "/api/v1/health/",
        "/api/v1/auth/register/",
        "/api/v1/auth/login/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/logout/",
        "/api/v1/auth/password-reset/",
        "/api/v1/auth/password-reset/confirm/",
        "/api/v1/posts/",
        "/api/v1/posts/{id}/",
        "/api/v1/posts/{post_id}/comments/",
        "/api/v1/comments/{id}/",
        "/api/v1/tags/",
        "/api/v1/users/me/",
        "/api/v1/users/me/image/",
        "/api/v1/users/{username}/",
    }
    assert expected.issubset(set(paths.keys()))
