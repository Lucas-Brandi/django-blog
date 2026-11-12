"""Testes do signal que cria/atualiza o Profile (M3/M8).

Cobrem o fluxo do `create_or_update_user_profile` (post_save em AUTH_USER_MODEL):

- criar um usuário cria exatamente um Profile;
- salvar o usuário de novo não duplica o Profile;
- recuperar/atualizar não gera um segundo Profile;
- o guard de `raw=True` (loaddata) não deixa o signal criar outro Profile,
  evitando o UNIQUE constraint em user_id quando o fixture já traz o Profile.
"""

import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models.signals import post_save

from users.models import Profile, create_or_update_user_profile

User = get_user_model()

pytestmark = pytest.mark.django_db


# --- Criação / atualização normais ------------------------------------------


def test_creating_user_creates_single_profile():
    user = User.objects.create_user(username="alice", email="alice@example.com", password="Str0ngPass!99")
    assert Profile.objects.filter(user=user).count() == 1


def test_saving_existing_user_does_not_duplicate_profile():
    user = User.objects.create_user(username="bob", email="bob@example.com", password="Str0ngPass!99")
    # Vários saves posteriores não podem criar Profiles extras.
    user.first_name = "Bob"
    user.save()
    user.last_name = "Builder"
    user.save()
    assert Profile.objects.filter(user=user).count() == 1


def test_profile_persists_on_user_update():
    user = User.objects.create_user(username="carol", email="carol@example.com", password="Str0ngPass!99")
    profile = user.profile
    profile.bio = "hello"
    profile.save()

    user.email = "carol2@example.com"
    user.save()

    # get_or_create não recria; o mesmo Profile continua, com a bio preservada.
    user.refresh_from_db()
    assert Profile.objects.filter(user=user).count() == 1
    assert user.profile.pk == profile.pk
    assert user.profile.bio == "hello"


def test_profile_recovered_if_missing_on_update():
    # Se por algum motivo o Profile sumir, um save do usuário o recria (uma vez).
    user = User.objects.create_user(username="dave", email="dave@example.com", password="Str0ngPass!99")
    Profile.objects.filter(user=user).delete()
    assert Profile.objects.filter(user=user).count() == 0

    user.save()
    assert Profile.objects.filter(user=user).count() == 1


# --- Guard de raw=True (loaddata) -------------------------------------------


def test_signal_skips_creation_when_raw():
    """Com raw=True o signal retorna cedo e NÃO cria Profile.

    Simula o caminho do loaddata, em que o Profile já vem no fixture. Dispara o
    receiver diretamente com raw=True/created=True: sem o guard, ele chamaria
    Profile.objects.create() e deixaria um Profile (ou quebraria no banco).
    """
    user = User.objects.create_user(username="erin", email="erin@example.com", password="Str0ngPass!99")
    # Estado de partida após a criação: exatamente um Profile.
    assert Profile.objects.filter(user=user).count() == 1

    # Chamada direta do receiver imitando o post_save do loaddata.
    create_or_update_user_profile(sender=User, instance=user, created=True, raw=True)

    # O guard impediu a criação de um segundo Profile.
    assert Profile.objects.filter(user=user).count() == 1


def test_loaddata_with_user_and_profile_does_not_raise(tmp_path):
    """loaddata de um fixture com User + Profile não deve quebrar.

    Sem o guard de `raw`, o post_save (raw=True) tentaria criar um segundo
    Profile para o mesmo user_id e estouraria UNIQUE constraint. Este teste
    carrega o fixture e confirma que fica exatamente um Profile.
    """
    fixture = [
        {
            "model": "auth.user",
            "pk": 4242,
            "fields": {
                "password": "!",
                "is_superuser": False,
                "username": "fixture_user",
                "email": "fixture@example.com",
                "is_staff": False,
                "is_active": True,
            },
        },
        {
            "model": "users.profile",
            "pk": 4242,
            "fields": {
                "user": 4242,
                "bio": "carregado via fixture",
                "image": "profile_pics/default.jpg",
            },
        },
    ]
    fixture_path = tmp_path / "profile_fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    out = StringIO()
    # Não deve levantar IntegrityError por conta do guard de raw.
    call_command("loaddata", str(fixture_path), stdout=out, verbosity=0)

    loaded = User.objects.get(pk=4242)
    assert Profile.objects.filter(user=loaded).count() == 1
    assert loaded.profile.bio == "carregado via fixture"


def test_signal_is_connected_once():
    """O receiver está registrado uma única vez em post_save de User.

    Protege contra registro duplicado do signal (ex.: se alguém mover o signal
    para apps.ready() sem remover o do models.py), que causaria Profiles em
    duplicidade.
    """
    count = 0
    for entry in post_save.receivers:
        # A estrutura interna muda entre versões do Django; o receiver é o
        # segundo elemento da tupla e pode ser um weakref.
        ref = entry[1]
        receiver = ref() if callable(ref) else ref
        if getattr(receiver, "__name__", None) == "create_or_update_user_profile":
            count += 1
    assert count == 1
