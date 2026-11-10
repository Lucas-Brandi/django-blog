"""Testes da API de posts (M4).

Cobrem o CRUD completo, as permissões (leitura pública, escrita autenticada,
edição/exclusão só do autor ou staff), o autor definido a partir de
request.user, o formato da resposta, a paginação, a ordenação (mais recentes
primeiro) e a busca opcional por ?search=.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from blog.models import Post, Tag

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Isola o throttle de login entre testes (escopo "login" é 5/min)."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def author(db):
    return User.objects.create_user(username="alice", email="alice@example.com", password="Str0ngPass!99")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", email="bob@example.com", password="Str0ngPass!99")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="admin", email="admin@example.com", password="Str0ngPass!99", is_staff=True
    )


def _auth(client, username):
    login = client.post(
        reverse("api-v1:auth:login"),
        {"username": username, "password": "Str0ngPass!99"},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    return client


@pytest.fixture
def author_client(client, author):
    return _auth(client, "alice")


@pytest.fixture
def post(author):
    return Post.objects.create(title="Hello", content="world", author=author)


# --- Leitura pública (D2) ---------------------------------------------------


def test_list_is_public(client, post):
    response = client.get(reverse("api-v1:posts:list"))
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_detail_is_public(client, post):
    response = client.get(reverse("api-v1:posts:detail", args=[post.id]))
    assert response.status_code == 200
    assert response.data["id"] == post.id


def test_detail_unknown_is_404(client):
    response = client.get(reverse("api-v1:posts:detail", args=[9999]))
    assert response.status_code == 404


# --- Formato da resposta ----------------------------------------------------


def test_response_shape(client, author):
    post = Post.objects.create(title="Shape", content="body", author=author)
    tag = Tag.objects.create(name="django")
    tag.posts.add(post)

    response = client.get(reverse("api-v1:posts:detail", args=[post.id]))
    data = response.data
    assert set(data.keys()) == {"id", "title", "content", "author", "created_at", "updated_at", "tags"}
    assert data["author"]["username"] == "alice"
    assert data["author"]["image_url"].startswith("http")
    assert data["tags"] == ["django"]


# --- Criação (escrita autenticada; author = request.user) -------------------


def test_create_requires_authentication(client):
    response = client.post(reverse("api-v1:posts:list"), {"title": "x", "content": "y"}, format="json")
    assert response.status_code == 401


def test_create_sets_author_from_request_user(author_client, author):
    response = author_client.post(
        reverse("api-v1:posts:list"),
        {"title": "Novo", "content": "conteudo"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["author"]["username"] == "alice"
    created = Post.objects.get(id=response.data["id"])
    assert created.author_id == author.id


def test_author_in_body_is_ignored(author_client, author, other_user):
    # Mesmo informando outro author no corpo, o autor é sempre o usuário logado.
    response = author_client.post(
        reverse("api-v1:posts:list"),
        {"title": "Novo", "content": "conteudo", "author": other_user.id},
        format="json",
    )
    assert response.status_code == 201
    created = Post.objects.get(id=response.data["id"])
    assert created.author_id == author.id


# --- Edição/exclusão: só o autor ou staff -----------------------------------


def test_author_can_update_own_post(author_client, post):
    response = author_client.patch(
        reverse("api-v1:posts:detail", args=[post.id]),
        {"title": "Editado"},
        format="json",
    )
    assert response.status_code == 200
    post.refresh_from_db()
    assert post.title == "Editado"


def test_non_author_cannot_update(client, post, other_user):
    _auth(client, "bob")
    response = client.patch(
        reverse("api-v1:posts:detail", args=[post.id]),
        {"title": "Hacked"},
        format="json",
    )
    assert response.status_code == 403
    post.refresh_from_db()
    assert post.title == "Hello"


def test_non_author_cannot_delete(client, post, other_user):
    _auth(client, "bob")
    response = client.delete(reverse("api-v1:posts:detail", args=[post.id]))
    assert response.status_code == 403
    assert Post.objects.filter(id=post.id).exists()


def test_author_can_delete_own_post(author_client, post):
    response = author_client.delete(reverse("api-v1:posts:detail", args=[post.id]))
    assert response.status_code == 204
    assert not Post.objects.filter(id=post.id).exists()


def test_staff_can_update_any_post(client, post, staff_user):
    _auth(client, "admin")
    response = client.patch(
        reverse("api-v1:posts:detail", args=[post.id]),
        {"title": "Moderado"},
        format="json",
    )
    assert response.status_code == 200
    post.refresh_from_db()
    assert post.title == "Moderado"


def test_update_requires_authentication(client, post):
    response = client.patch(
        reverse("api-v1:posts:detail", args=[post.id]),
        {"title": "x"},
        format="json",
    )
    assert response.status_code == 401


# --- Paginação e ordenação --------------------------------------------------


def test_list_is_paginated(client, author, settings):
    # Usa o PAGE_SIZE real configurado em M1 (padrão 10). Criando mais posts
    # que o tamanho da página, a resposta deve vir paginada (envelope + next).
    from rest_framework.pagination import PageNumberPagination

    page_size = PageNumberPagination().page_size
    total = page_size + 3
    for i in range(total):
        Post.objects.create(title=f"Post {i}", content="c", author=author)

    response = client.get(reverse("api-v1:posts:list"))
    assert response.status_code == 200
    # Envelope de paginação do DRF (configurado em M1).
    assert set(response.data.keys()) == {"count", "next", "previous", "results"}
    assert response.data["count"] == total
    assert len(response.data["results"]) == page_size
    assert response.data["next"] is not None


def test_list_is_newest_first(client, author):
    for i in range(3):
        Post.objects.create(title=f"Post {i}", content="c", author=author)

    response = client.get(reverse("api-v1:posts:list"))
    assert response.status_code == 200
    # Mais recentes primeiro: o último criado ("Post 2") vem antes.
    titles = [p["title"] for p in response.data["results"]]
    assert titles == ["Post 2", "Post 1", "Post 0"]


# --- Busca opcional ---------------------------------------------------------


def test_search_matches_title_and_content(client, author):
    Post.objects.create(title="Django tips", content="about the framework", author=author)
    Post.objects.create(title="Random", content="mentions django inside", author=author)
    Post.objects.create(title="Unrelated", content="nothing here", author=author)

    response = client.get(reverse("api-v1:posts:list"), {"search": "django"})
    assert response.status_code == 200
    assert response.data["count"] == 2
