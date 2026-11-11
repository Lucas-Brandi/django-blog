"""Testes da API de comentários (M6).

Cobrem a listagem (ordem cronológica, paginada), a criação (exige login, autor
de request.user, post da URL), e a exclusão/edição com as permissões: autor do
comentário, autor do post e staff.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from blog.models import Comment, Post

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
def post_author(db):
    return User.objects.create_user(username="alice", email="alice@example.com", password="Str0ngPass!99")


@pytest.fixture
def commenter(db):
    return User.objects.create_user(username="bob", email="bob@example.com", password="Str0ngPass!99")


@pytest.fixture
def stranger(db):
    return User.objects.create_user(username="carol", email="carol@example.com", password="Str0ngPass!99")


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
def post(post_author):
    return Post.objects.create(title="Hello", content="world", author=post_author)


# --- Listagem: exige login, ordem cronológica, paginada ---------------------


def test_list_requires_authentication(client, post):
    response = client.get(reverse("api-v1:posts:comments", args=[post.id]))
    assert response.status_code == 401


def test_list_is_chronological(client, post, post_author, commenter):
    c1 = Comment.objects.create(post=post, author=post_author, content="primeiro")
    c2 = Comment.objects.create(post=post, author=commenter, content="segundo")
    _auth(client, "bob")
    response = client.get(reverse("api-v1:posts:comments", args=[post.id]))
    assert response.status_code == 200
    ids = [c["id"] for c in response.data["results"]]
    assert ids == [c1.id, c2.id]


def test_list_only_returns_comments_of_the_post(client, post, post_author, commenter):
    other_post = Post.objects.create(title="Other", content="x", author=post_author)
    Comment.objects.create(post=post, author=commenter, content="deste post")
    Comment.objects.create(post=other_post, author=commenter, content="de outro post")
    _auth(client, "bob")
    response = client.get(reverse("api-v1:posts:comments", args=[post.id]))
    assert response.data["count"] == 1
    assert response.data["results"][0]["content"] == "deste post"


def test_list_is_paginated(client, post, commenter):
    from rest_framework.pagination import PageNumberPagination

    page_size = PageNumberPagination().page_size
    total = page_size + 2
    for i in range(total):
        Comment.objects.create(post=post, author=commenter, content=f"c{i}")
    _auth(client, "bob")
    response = client.get(reverse("api-v1:posts:comments", args=[post.id]))
    assert set(response.data.keys()) == {"count", "next", "previous", "results"}
    assert response.data["count"] == total
    assert len(response.data["results"]) == page_size


# --- Criação: login, autor de request.user, post da URL ---------------------


def test_create_requires_authentication(client, post):
    response = client.post(
        reverse("api-v1:posts:comments", args=[post.id]),
        {"content": "oi"},
        format="json",
    )
    assert response.status_code == 401


def test_create_sets_author_and_post(client, post, commenter):
    _auth(client, "bob")
    response = client.post(
        reverse("api-v1:posts:comments", args=[post.id]),
        {"content": "comentário novo"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["author"]["username"] == "bob"
    assert response.data["post"] == post.id
    created = Comment.objects.get(id=response.data["id"])
    assert created.author_id == commenter.id
    assert created.post_id == post.id


def test_create_ignores_author_and_post_in_body(client, post, commenter, stranger):
    other_post = Post.objects.create(title="Other", content="x", author=stranger)
    _auth(client, "bob")
    response = client.post(
        reverse("api-v1:posts:comments", args=[post.id]),
        {"content": "x", "author": stranger.id, "post": other_post.id},
        format="json",
    )
    assert response.status_code == 201
    created = Comment.objects.get(id=response.data["id"])
    assert created.author_id == commenter.id
    assert created.post_id == post.id


def test_create_on_unknown_post_is_404(client, commenter):
    _auth(client, "bob")
    response = client.post(
        reverse("api-v1:posts:comments", args=[9999]),
        {"content": "x"},
        format="json",
    )
    assert response.status_code == 404


def test_create_rejects_blank_content(client, post, commenter):
    _auth(client, "bob")
    response = client.post(
        reverse("api-v1:posts:comments", args=[post.id]),
        {"content": "   "},
        format="json",
    )
    assert response.status_code == 400


# --- Exclusão: autor do comentário, autor do post, staff --------------------


def test_comment_author_can_delete(client, post, commenter):
    comment = Comment.objects.create(post=post, author=commenter, content="x")
    _auth(client, "bob")
    response = client.delete(reverse("api-v1:comments:detail", args=[comment.id]))
    assert response.status_code == 204
    assert not Comment.objects.filter(id=comment.id).exists()


def test_post_author_can_delete_any_comment(client, post, commenter):
    comment = Comment.objects.create(post=post, author=commenter, content="x")
    _auth(client, "alice")  # alice é a autora do post
    response = client.delete(reverse("api-v1:comments:detail", args=[comment.id]))
    assert response.status_code == 204
    assert not Comment.objects.filter(id=comment.id).exists()


def test_staff_can_delete_any_comment(client, post, commenter, staff_user):
    comment = Comment.objects.create(post=post, author=commenter, content="x")
    _auth(client, "admin")
    response = client.delete(reverse("api-v1:comments:detail", args=[comment.id]))
    assert response.status_code == 204
    assert not Comment.objects.filter(id=comment.id).exists()


def test_stranger_cannot_delete(client, post, commenter, stranger):
    comment = Comment.objects.create(post=post, author=commenter, content="x")
    _auth(client, "carol")
    response = client.delete(reverse("api-v1:comments:detail", args=[comment.id]))
    assert response.status_code == 403
    assert Comment.objects.filter(id=comment.id).exists()


def test_delete_requires_authentication(client, post, commenter):
    comment = Comment.objects.create(post=post, author=commenter, content="x")
    response = client.delete(reverse("api-v1:comments:detail", args=[comment.id]))
    assert response.status_code == 401


# --- Edição do próprio comentário (opcional) --------------------------------


def test_comment_author_can_edit_own(client, post, commenter):
    comment = Comment.objects.create(post=post, author=commenter, content="antigo")
    _auth(client, "bob")
    response = client.patch(
        reverse("api-v1:comments:detail", args=[comment.id]),
        {"content": "editado"},
        format="json",
    )
    assert response.status_code == 200
    comment.refresh_from_db()
    assert comment.content == "editado"


def test_stranger_cannot_edit(client, post, commenter, stranger):
    comment = Comment.objects.create(post=post, author=commenter, content="antigo")
    _auth(client, "carol")
    response = client.patch(
        reverse("api-v1:comments:detail", args=[comment.id]),
        {"content": "hackeado"},
        format="json",
    )
    assert response.status_code == 403
    comment.refresh_from_db()
    assert comment.content == "antigo"
