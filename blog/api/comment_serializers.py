"""Serializers da API de comentários (M6).

Expõem o model Comment em JSON. O autor nunca vem do corpo da requisição: é
definido a partir de request.user na view. A resposta traz o autor aninhado
(username + imagem de perfil absoluta), reusando a representação dos posts.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from blog.models import Comment
from users.models import Profile

from .serializers import PostAuthorSerializer


class CommentSerializer(serializers.ModelSerializer):
    """Serializer de leitura/escrita de Comment.

    - author: somente leitura; definido pela view a partir de request.user.
    - post: somente leitura; vem da URL (/posts/<id>/comments/).
    """

    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "author", "content", "created_at"]
        read_only_fields = ["id", "post", "created_at"]

    @extend_schema_field(PostAuthorSerializer)
    def get_author(self, comment):
        # O Profile é 1-para-1 com o User (criado pelo signal). get_or_create
        # protege o caso raro de um usuário sem Profile.
        profile, _ = Profile.objects.get_or_create(user=comment.author)
        return PostAuthorSerializer(profile, context=self.context).data

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("O comentário não pode ser vazio.")
        return value
