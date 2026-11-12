"""Serializers da API de posts e tags (M4 e M5).

Expõem os models Post e Tag em JSON para o front React. O autor nunca vem do
corpo da requisição: é definido a partir de request.user na view. A resposta
de post traz o autor aninhado (username + imagem de perfil absoluta) e as tags.

M5: as tags podem ser associadas na criação/edição de um post (por nome ou id)
e são normalizadas para minúsculas para evitar duplicatas (sem diferenciar
maiúsculas de minúsculas).
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from blog.models import Post, Tag
from users.models import Profile


class PostAuthorSerializer(serializers.Serializer):
    """Representação enxuta do autor: username e URL absoluta da imagem."""

    username = serializers.CharField(source="user.username", read_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, profile) -> str:
        url = profile.image.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class TagSerializer(serializers.ModelSerializer):
    """Serializer de leitura/escrita de Tag, com contagem de posts.

    O nome é normalizado (strip + lower) para manter a unicidade
    case-insensitive garantida no banco (constraint unique_tag_name_ci).
    """

    post_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name", "post_count"]
        read_only_fields = ["id"]

    def get_post_count(self, tag) -> int:
        # Usa a anotação da view quando presente (evita N+1); senão conta direto.
        annotated = getattr(tag, "post_count", None)
        if annotated is not None:
            return annotated
        return tag.posts.count()

    def validate_name(self, value):
        normalized = value.strip().lower()
        if not normalized:
            raise serializers.ValidationError("O nome da tag não pode ser vazio.")
        if Tag.objects.filter(name__iexact=normalized).exists():
            raise serializers.ValidationError("Já existe uma tag com esse nome.")
        return normalized


def resolve_tags(values):
    """Resolve uma lista de nomes e/ou ids de tags para instâncias de Tag.

    Aceita itens como string (nome) ou inteiro (id). Nomes são normalizados
    (strip + lower) e criados sob demanda via get_or_create; ids precisam
    existir. Levanta ValidationError em entradas inválidas.
    """
    tags = []
    for item in values:
        if isinstance(item, bool):
            raise serializers.ValidationError("Tag inválida.")
        if isinstance(item, int):
            try:
                tags.append(Tag.objects.get(pk=item))
            except Tag.DoesNotExist as exc:
                raise serializers.ValidationError(f"Tag com id {item} não encontrada.") from exc
        elif isinstance(item, str):
            name = item.strip().lower()
            if not name:
                raise serializers.ValidationError("O nome da tag não pode ser vazio.")
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        else:
            raise serializers.ValidationError("As tags devem ser informadas por nome (texto) ou id (número).")
    return tags


class PostSerializer(serializers.ModelSerializer):
    """Serializer de leitura e escrita de Post.

    - author: somente leitura; definido pela view a partir de request.user.
    - tags: leitura devolve os nomes; escrita aceita uma lista de nomes e/ou
      ids (write-only), associando as tags ao criar e ao editar (M5).
    """

    author = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    tag_input = serializers.ListField(
        child=serializers.JSONField(),
        write_only=True,
        required=False,
        source="tags",
    )

    class Meta:
        model = Post
        fields = ["id", "title", "content", "author", "created_at", "updated_at", "tags", "tag_input"]
        read_only_fields = ["id", "created_at", "updated_at"]

    @extend_schema_field(PostAuthorSerializer)
    def get_author(self, post):
        # O Profile é 1-para-1 com o User (criado pelo signal). get_or_create
        # protege o caso raro de um usuário sem Profile.
        profile, _ = Profile.objects.get_or_create(user=post.author)
        return PostAuthorSerializer(profile, context=self.context).data

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_tags(self, post):
        return [tag.name for tag in post.tags.all()]

    def create(self, validated_data):
        tag_values = validated_data.pop("tags", None)
        post = super().create(validated_data)
        if tag_values is not None:
            post.tags.set(resolve_tags(tag_values))
        return post

    def update(self, instance, validated_data):
        tag_values = validated_data.pop("tags", None)
        post = super().update(instance, validated_data)
        if tag_values is not None:
            post.tags.set(resolve_tags(tag_values))
        return post
