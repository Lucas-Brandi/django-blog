"""Serializers da API de posts (M4).

Expõem o model Post em JSON para o front React. O autor nunca vem do corpo
da requisição: é definido a partir de request.user na view. A resposta traz
o autor aninhado (username + imagem de perfil absoluta) e as tags.
"""

from rest_framework import serializers

from blog.models import Post
from users.models import Profile


class PostAuthorSerializer(serializers.Serializer):
    """Representação enxuta do autor: username e URL absoluta da imagem."""

    username = serializers.CharField(source="user.username", read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, profile):
        url = profile.image.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class PostSerializer(serializers.ModelSerializer):
    """Serializer de leitura e escrita de Post.

    - author: somente leitura; definido pela view a partir de request.user.
    - tags: somente leitura (nomes); o gerenciamento de tags é escopo de M5.
    """

    author = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "title", "content", "author", "created_at", "updated_at", "tags"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_author(self, post):
        # O Profile é 1-para-1 com o User (criado pelo signal). get_or_create
        # protege o caso raro de um usuário sem Profile.
        profile, _ = Profile.objects.get_or_create(user=post.author)
        return PostAuthorSerializer(profile, context=self.context).data

    def get_tags(self, post):
        return [tag.name for tag in post.tags.all()]
