"""Testes da API de perfil (M3).

Cobrem consulta/atualização do próprio perfil, troca e remoção de imagem
(restaurando o default sem apagá-lo), validações de imagem/username/email,
autenticação e isolamento entre usuários, além do storage local e de um
storage em memória simulando o R2.
"""

from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from users.models import DEFAULT_IMAGE

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Isola o throttle de login entre testes (o escopo "login" é 5/min)."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# --- Helpers / fixtures -----------------------------------------------------


def make_image_file(name="avatar.png", size=(50, 50), fmt="PNG", color=(10, 20, 30)):
    """Gera um upload de imagem em memória (sem tocar o disco)."""
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    buffer.seek(0)
    content_type = "image/png" if fmt == "PNG" else "image/jpeg"
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", email="alice@example.com", password="Str0ngPass!99")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", email="bob@example.com", password="Str0ngPass!99")


@pytest.fixture
def auth_client(client, user):
    login = client.post(
        reverse("api-v1:auth:login"),
        {"username": "alice", "password": "Str0ngPass!99"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client


# --- GET /users/me/ ---------------------------------------------------------


def test_me_requires_authentication(client):
    response = client.get(reverse("api-v1:users:me"))
    assert response.status_code == 401


def test_me_returns_own_profile_with_absolute_image_url(auth_client, user):
    response = auth_client.get(reverse("api-v1:users:me"))
    assert response.status_code == 200
    assert response.data["username"] == "alice"
    assert response.data["email"] == "alice@example.com"
    assert "bio" in response.data
    # URL absoluta (serializer recebeu o request no contexto).
    assert response.data["image_url"].startswith("http")


# --- PATCH /users/me/ -------------------------------------------------------


def test_me_updates_account_fields(auth_client, user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"username": "alice2", "bio": "hello there"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["username"] == "alice2"
    assert response.data["bio"] == "hello there"
    user.refresh_from_db()
    assert user.username == "alice2"


def test_me_updates_image(auth_client, user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file()},
        format="multipart",
    )
    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.image.name != DEFAULT_IMAGE
    assert user.profile.image.name.startswith("profile_pics/")


def test_me_rejects_duplicate_username(auth_client, user, other_user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"username": "bob"},
        format="json",
    )
    assert response.status_code == 400
    assert "username" in response.data["error"]["detail"]


def test_me_rejects_duplicate_email(auth_client, user, other_user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"email": "bob@example.com"},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.data["error"]["detail"]


def test_me_rejects_invalid_email(auth_client, user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"email": "not-an-email"},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.data["error"]["detail"]


def test_me_keeping_same_username_and_email_is_allowed(auth_client, user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"username": "alice", "email": "alice@example.com"},
        format="json",
    )
    assert response.status_code == 200


# --- Validação de imagem ----------------------------------------------------


def test_me_rejects_non_image_file(auth_client, user):
    bad = SimpleUploadedFile("payload.png", b"this is not an image", content_type="image/png")
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": bad},
        format="multipart",
    )
    assert response.status_code == 400
    assert "image" in response.data["error"]["detail"]


def test_me_rejects_oversized_image(auth_client, user, settings):
    settings.PROFILE_IMAGE_MAX_BYTES = 100  # limite baixo para o teste
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file(size=(300, 300))},
        format="multipart",
    )
    assert response.status_code == 400
    assert "image" in response.data["error"]["detail"]


def test_me_rejects_unsupported_image_format(auth_client, user):
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file(name="avatar.gif", fmt="GIF")},
        format="multipart",
    )
    assert response.status_code == 400
    assert "image" in response.data["error"]["detail"]


# --- DELETE /users/me/image/ ------------------------------------------------


def test_delete_image_restores_default(auth_client, user):
    # Primeiro envia uma imagem, depois remove.
    auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file()},
        format="multipart",
    )
    user.profile.refresh_from_db()
    uploaded_name = user.profile.image.name
    assert uploaded_name != DEFAULT_IMAGE

    response = auth_client.delete(reverse("api-v1:users:me_image"))
    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.image.name == DEFAULT_IMAGE
    # O arquivo enviado foi removido, mas o default permanece.
    storage = user.profile.image.storage
    assert not storage.exists(uploaded_name)
    assert storage.exists(DEFAULT_IMAGE)


def test_delete_image_requires_authentication(client):
    response = client.delete(reverse("api-v1:users:me_image"))
    assert response.status_code == 401


# --- Isolamento entre usuários ----------------------------------------------


def test_user_cannot_change_another_users_profile(client, user, other_user):
    # Autentica como bob e tenta roubar o username de alice: o endpoint me/
    # sempre age sobre o próprio usuário, então bob só altera bob.
    login = client.post(
        reverse("api-v1:auth:login"),
        {"username": "bob", "password": "Str0ngPass!99"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    response = client.patch(reverse("api-v1:users:me"), {"bio": "bob was here"}, format="json")
    assert response.status_code == 200

    user.refresh_from_db()
    user.profile.refresh_from_db()
    # Alice não foi tocada.
    assert user.profile.bio == ""
    other_user.profile.refresh_from_db()
    assert other_user.profile.bio == "bob was here"


# --- Perfil público (opcional) ----------------------------------------------


def test_public_profile_returns_safe_fields(client, user):
    response = client.get(reverse("api-v1:users:public", args=["alice"]))
    assert response.status_code == 200
    assert response.data["username"] == "alice"
    assert "bio" in response.data
    assert "image_url" in response.data
    # Não vaza e-mail no perfil público.
    assert "email" not in response.data


def test_public_profile_unknown_username_is_404(client):
    response = client.get(reverse("api-v1:users:public", args=["ghost"]))
    assert response.status_code == 404


# --- Storage local vs. R2 (storage em memória) ------------------------------


def test_image_upload_works_with_local_storage(auth_client, user, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file(size=(600, 600))},
        format="multipart",
    )
    assert response.status_code == 200
    user.profile.refresh_from_db()
    # O nome não duplica o prefixo da pasta (profile_pics/profile_pics/...).
    assert user.profile.image.name.count("profile_pics/") == 1
    # Redimensionado para no máximo 400x400 pelo Profile.save().
    with user.profile.image.open("rb") as fh:
        img = Image.open(fh)
        assert img.width <= 400 and img.height <= 400


def test_image_upload_works_with_in_memory_storage(auth_client, user, settings):
    # Simula um storage remoto (como o R2) sem path local nem rede, validando
    # que Profile.save() e a substituição funcionam via Storage API.
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    response = auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file(size=(600, 600))},
        format="multipart",
    )
    assert response.status_code == 200
    user.profile.refresh_from_db()
    storage = user.profile.image.storage
    assert storage.exists(user.profile.image.name)


def test_image_replace_does_not_leave_orphan(auth_client, user, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file(name="first.png")},
        format="multipart",
    )
    user.profile.refresh_from_db()
    first_name = user.profile.image.name
    storage = user.profile.image.storage

    auth_client.patch(
        reverse("api-v1:users:me"),
        {"image": make_image_file(name="second.png")},
        format="multipart",
    )
    user.profile.refresh_from_db()
    second_name = user.profile.image.name

    assert second_name != first_name
    # O arquivo antigo não ficou órfão.
    assert not storage.exists(first_name)
    assert storage.exists(second_name)
