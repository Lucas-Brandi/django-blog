"""Testes do management command seed_posts (M4)."""

import pytest
from django.core.management import call_command

from blog.models import Post

pytestmark = pytest.mark.django_db


def test_seed_creates_default_posts():
    call_command("seed_posts")
    assert Post.objects.count() == 5
    # Todos os posts têm autor e pelo menos uma tag.
    for post in Post.objects.all():
        assert post.author_id is not None
        assert post.tags.exists()


def test_seed_count_option():
    call_command("seed_posts", count=8)
    assert Post.objects.count() == 8


def test_seed_clear_resets_posts():
    call_command("seed_posts")
    call_command("seed_posts", clear=True)
    # Com --clear os anteriores são apagados e recriados; total volta a 5.
    assert Post.objects.count() == 5
