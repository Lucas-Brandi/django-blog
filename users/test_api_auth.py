"""Testes da API de autenticação (M2).

Cobrem registro, login, refresh, logout (blacklist), reset de senha
(resposta genérica + envio condicional) e throttling.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import Profile

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", email="alice@example.com", password="Str0ngPass!99")


# --- Registro ---------------------------------------------------------------


def test_register_creates_user_and_single_profile(client):
    url = reverse("api-v1:auth:register")
    payload = {
        "username": "bob",
        "email": "bob@example.com",
        "password": "Str0ngPass!99",
        "password2": "Str0ngPass!99",
    }
    response = client.post(url, payload, format="json")

    assert response.status_code == 201
    assert response.data["username"] == "bob"
    assert "password" not in response.data
    created = User.objects.get(username="bob")
    # O signal cria exatamente um Profile, sem duplicar.
    assert Profile.objects.filter(user=created).count() == 1


def test_register_requires_matching_passwords(client):
    url = reverse("api-v1:auth:register")
    payload = {
        "username": "bob",
        "email": "bob@example.com",
        "password": "Str0ngPass!99",
        "password2": "different",
    }
    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    # Erro por campo, dentro do envelope padronizado da API.
    assert "password2" in response.data["error"]["detail"]


def test_register_rejects_weak_password(client):
    url = reverse("api-v1:auth:register")
    payload = {"username": "bob", "email": "bob@example.com", "password": "123", "password2": "123"}
    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    assert "password" in response.data["error"]["detail"]


def test_register_requires_email(client):
    url = reverse("api-v1:auth:register")
    payload = {"username": "bob", "password": "Str0ngPass!99", "password2": "Str0ngPass!99"}
    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    assert "email" in response.data["error"]["detail"]


# --- Login / refresh --------------------------------------------------------


def test_login_returns_token_pair(client, user):
    url = reverse("api-v1:auth:login")
    response = client.post(url, {"username": "alice", "password": "Str0ngPass!99"}, format="json")
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_login_invalid_credentials(client, user):
    url = reverse("api-v1:auth:login")
    response = client.post(url, {"username": "alice", "password": "wrong"}, format="json")
    assert response.status_code == 401


def test_refresh_returns_new_access(client, user):
    login = client.post(
        reverse("api-v1:auth:login"),
        {"username": "alice", "password": "Str0ngPass!99"},
        format="json",
    )
    refresh = login.data["refresh"]
    response = client.post(reverse("api-v1:auth:refresh"), {"refresh": refresh}, format="json")
    assert response.status_code == 200
    assert "access" in response.data


# --- Logout / blacklist -----------------------------------------------------


def test_logout_blacklists_refresh(client, user):
    login = client.post(
        reverse("api-v1:auth:login"),
        {"username": "alice", "password": "Str0ngPass!99"},
        format="json",
    )
    access = login.data["access"]
    refresh = login.data["refresh"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout = client.post(reverse("api-v1:auth:logout"), {"refresh": refresh}, format="json")
    assert logout.status_code == 205

    # Refresh revogado deve ser rejeitado.
    client.credentials()
    again = client.post(reverse("api-v1:auth:refresh"), {"refresh": refresh}, format="json")
    assert again.status_code == 401


def test_logout_requires_authentication(client, user):
    login = client.post(
        reverse("api-v1:auth:login"),
        {"username": "alice", "password": "Str0ngPass!99"},
        format="json",
    )
    refresh = login.data["refresh"]
    # Sem o header Authorization.
    response = client.post(reverse("api-v1:auth:logout"), {"refresh": refresh}, format="json")
    assert response.status_code == 401


# --- Reset de senha ---------------------------------------------------------


def test_password_reset_sends_email_for_existing_account(client, user):
    url = reverse("api-v1:auth:password_reset")
    response = client.post(url, {"email": "alice@example.com"}, format="json")
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert "password-reset/confirm/" in mail.outbox[0].body


def test_password_reset_response_identical_for_unknown_email(client, user):
    url = reverse("api-v1:auth:password_reset")
    known = client.post(url, {"email": "alice@example.com"}, format="json")
    mail.outbox.clear()
    unknown = client.post(url, {"email": "nobody@example.com"}, format="json")

    assert known.status_code == unknown.status_code == 200
    assert known.data == unknown.data
    # Nenhum e-mail é enviado para um endereço inexistente.
    assert len(mail.outbox) == 0


def test_password_reset_confirm_changes_password(client, user):
    from users.api.serializers import make_reset_token

    uid, token = make_reset_token(user)
    url = reverse("api-v1:auth:password_reset_confirm")
    payload = {
        "uid": uid,
        "token": token,
        "new_password": "BrandNew!Pass42",
        "new_password2": "BrandNew!Pass42",
    }
    response = client.post(url, payload, format="json")
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.check_password("BrandNew!Pass42")


def test_password_reset_confirm_rejects_bad_token(client, user):
    from users.api.serializers import make_reset_token

    uid, _ = make_reset_token(user)
    url = reverse("api-v1:auth:password_reset_confirm")
    payload = {
        "uid": uid,
        "token": "invalid-token",
        "new_password": "BrandNew!Pass42",
        "new_password2": "BrandNew!Pass42",
    }
    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    assert "token" in response.data["error"]["detail"]


# --- Throttling -------------------------------------------------------------


def test_login_is_throttled(client, user, settings):
    from django.core.cache import cache

    # Taxa mínima e cache limpo para um teste determinístico e isolado.
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"] = "1/min"
    cache.clear()
    try:
        url = reverse("api-v1:auth:login")
        payload = {"username": "alice", "password": "Str0ngPass!99"}

        first = client.post(url, payload, format="json")
        second = client.post(url, payload, format="json")

        assert first.status_code == 200
        assert second.status_code == 429
    finally:
        cache.clear()
