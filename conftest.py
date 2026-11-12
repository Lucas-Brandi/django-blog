"""Configuração global do pytest (M8).

Isola o armazenamento de mídia dos testes: todo upload feito durante a suíte
vai para um diretório temporário por teste, nunca para o `media/` do projeto.
Assim os testes de upload (perfil) não deixam arquivos órfãos em
`media/profile_pics/`.

O diretório temporário é semeado com o `profile_pics/default.jpg` real, porque
alguns testes verificam que o avatar padrão continua existindo no storage (ex.:
ao remover a imagem, o perfil volta para o default).
"""

import shutil
from pathlib import Path

import pytest
from django.conf import settings

from users.models import DEFAULT_IMAGE

# Caminho do avatar padrão no repositório (fonte para semear o MEDIA_ROOT temp).
_REAL_DEFAULT_IMAGE = Path(settings.MEDIA_ROOT) / DEFAULT_IMAGE


@pytest.fixture(autouse=True)
def temp_media_root(tmp_path, settings):
    """Redireciona MEDIA_ROOT para um diretório temporário isolado por teste.

    Testes que precisam de outro MEDIA_ROOT (ou de outro STORAGES) continuam
    livres para sobrescrever `settings.MEDIA_ROOT`/`settings.STORAGES`: por ser
    uma fixture de função, cada teste parte deste isolamento e pode ajustá-lo.
    """
    media_root = tmp_path / "media"
    media_root.mkdir()

    # Semeia o avatar padrão para os testes que checam sua existência.
    if _REAL_DEFAULT_IMAGE.exists():
        destination = media_root / DEFAULT_IMAGE
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_REAL_DEFAULT_IMAGE, destination)

    settings.MEDIA_ROOT = str(media_root)
    yield media_root
