"""Testes da API de tags (M5).

Cobrem a listagem de tags com contagem de posts, a criação (autenticada e com
unicidade case-insensitive), a associação de tags ao criar/editar um post
(por nome e por id) e o filtro de posts por tag (?tag=<nome>).
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


# --- Listagem de tags (pública, com contagem de posts) ----------------------


def test_tag_list_is_public_with_post_count(client, author):
    django_tag = Tag.objects.create(name="django")
    Tag.objects.create(name="python")
    post = Post.objects.create(title="t", content="c", author=author)
    post.tags.add(django_tag)

    response = client.get(reverse("api-v1:tags:list"))
    assert response.status_code == 200
    by_name = {t["name"]: t for t in response.data["results"]}
    assert by_name["django"]["post_count"] == 1
    assert by_name["python"]["post_count"] == 0


# --- Criação de tags --------------------------------------------------------


def test_tag_create_requires_authentication(client):
    response = client.post(reverse("api-v1:tags:list"), {"name": "news"}, format="json")
    assert response.status_code == 401


def test_tag_create_normalizes_and_persists(author_client):
    response = author_client.post(reverse("api-v1:tags:list"), {"name": "  Django  "}, format="json")
    assert response.status_code == 201
    assert response.data["name"] == "django"
    assert Tag.objects.filter(name="django").count() == 1


def test_tag_create_rejects_case_insensitive_duplicate(author_client):
    Tag.objects.create(name="django")
    response = author_client.post(reverse("api-v1:tags:list"), {"name": "DJANGO"}, format="json")
    assert response.status_code == 400
    assert Tag.objects.filter(name__iexact="django").count() == 1


# --- Unicidade no banco (constraint) ----------------------------------------


def test_tag_db_constraint_blocks_case_insensitive_duplicate():
    from django.db import IntegrityError

    Tag.objects.create(name="django")
    with pytest.raises(IntegrityError):
        Tag.objects.create(name="Django")


# --- Associação de tags ao criar/editar post --------------------------------


def test_create_post_associates_tags_by_name(author_client):
    response = author_client.post(
        reverse("api-v1:posts:list"),
        {"title": "Novo", "content": "c", "tag_input": ["Django", "python"]},
        format="json",
    )
    assert response.status_code == 201
    assert sorted(response.data["tags"]) == ["django", "python"]
    post = Post.objects.get(id=response.data["id"])
    assert set(post.tags.values_list("name", flat=True)) == {"django", "python"}


def test_create_post_associates_tags_by_id(author_client):
    tag = Tag.objects.create(name="rest")
    response = author_client.post(
        reverse("api-v1:posts:list"),
        {"title": "Novo", "content": "c", "tag_input": [tag.id]},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["tags"] == ["rest"]


def test_edit_post_replaces_tags(author_client, author):
    post = Post.objects.create(title="t", content="c", author=author)
    post.tags.add(Tag.objects.create(name="old"))
    response = author_client.patch(
        reverse("api-v1:posts:detail", args=[post.id]),
        {"tag_input": ["new"]},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["tags"] == ["new"]
    assert set(post.tags.values_list("name", flat=True)) == {"new"}


def test_create_post_with_unknown_tag_id_is_400(author_client):
    response = author_client.post(
        reverse("api-v1:posts:list"),
        {"title": "Novo", "content": "c", "tag_input": [9999]},
        format="json",
    )
    assert response.status_code == 400


# --- Um post com várias tags e uma tag em vários posts ----------------------


def test_many_to_many_relationship(author):
    post1 = Post.objects.create(title="p1", content="c", author=author)
    post2 = Post.objects.create(title="p2", content="c", author=author)
    django_tag = Tag.objects.create(name="django")
    python_tag = Tag.objects.create(name="python")
    post1.tags.set([django_tag, python_tag])
    post2.tags.set([django_tag])

    assert post1.tags.count() == 2
    assert django_tag.posts.count() == 2


# --- Filtro de posts por tag ------------------------------------------------


def test_filter_posts_by_tag(client, author):
    django_tag = Tag.objects.create(name="django")
    python_tag = Tag.objects.create(name="python")
    p1 = Post.objects.create(title="p1", content="c", author=author)
    p2 = Post.objects.create(title="p2", content="c", author=author)
    Post.objects.create(title="p3", content="c", author=author)
    p1.tags.add(django_tag)
    p2.tags.add(python_tag)

    response = client.get(reverse("api-v1:posts:list"), {"tag": "django"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == p1.id


def test_filter_posts_by_tag_is_case_insensitive(client, author):
    django_tag = Tag.objects.create(name="django")
    p1 = Post.objects.create(title="p1", content="c", author=author)
    p1.tags.add(django_tag)

    response = client.get(reverse("api-v1:posts:list"), {"tag": "DJANGO"})
    assert response.status_code == 200
    assert response.data["count"] == 1
