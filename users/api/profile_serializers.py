"""Serializers do perfil do usuário (M3).

Espelham o contrato das views HTML (UserUpdateForm + ProfileUpdateForm):
username, email, bio e imagem. O redimensionamento 400x400 acontece em
Profile.save(); aqui só validamos a entrada e montamos URLs absolutas.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from users.models import DEFAULT_IMAGE

User = get_user_model()

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG"}


def _validate_image_file(image):
    """Valida tamanho e conteúdo real do arquivo (não confia na extensão)."""
    max_bytes = settings.PROFILE_IMAGE_MAX_BYTES
    if image.size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise serializers.ValidationError(f"A imagem excede o tamanho máximo de {max_mb:.1f} MB.")

    # Verifica o conteúdo real com Pillow: um arquivo malicioso renomeado para
    # .jpg não passa por aqui.
    try:
        image.seek(0)
        with Image.open(image) as img:
            img_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise serializers.ValidationError("Arquivo de imagem inválido ou corrompido.") from exc
    finally:
        image.seek(0)

    if img_format not in ALLOWED_IMAGE_FORMATS:
        raise serializers.ValidationError("Formato não suportado. Use JPG ou PNG.")
    return image


class ProfileSerializer(serializers.Serializer):
    """GET/PATCH do próprio perfil: dados do User + bio/imagem do Profile."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    bio = serializers.CharField(max_length=300, allow_blank=True, required=False)
    image = serializers.ImageField(required=False, write_only=True)
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, profile):
        """URL absoluta da imagem (serializer precisa de request no contexto)."""
        url = profile.image.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def validate_username(self, value):
        qs = User.objects.filter(username__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return value

    def validate_email(self, value):
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise serializers.ValidationError("Este e-mail já está em uso.")
        return value

    def validate_image(self, value):
        return _validate_image_file(value)

    def to_representation(self, profile):
        return {
            "username": profile.user.username,
            "email": profile.user.email,
            "bio": profile.bio,
            "image_url": self.get_image_url(profile),
        }

    def update(self, profile, validated_data):
        user = profile.user
        user_changed = False
        if "username" in validated_data:
            user.username = validated_data["username"]
            user_changed = True
        if "email" in validated_data:
            user.email = validated_data["email"]
            user_changed = True
        if user_changed:
            user.save(update_fields=["username", "email"])

        if "bio" in validated_data:
            profile.bio = validated_data["bio"]

        if "image" in validated_data:
            # Remove o arquivo antigo (exceto o default compartilhado) para não
            # deixar órfãos no storage ao substituir a foto.
            old_name = profile.image.name
            if old_name and old_name != DEFAULT_IMAGE:
                profile.image.storage.delete(old_name)
            profile.image = validated_data["image"]

        profile.save()
        return profile


class PublicProfileSerializer(serializers.Serializer):
    """Perfil público (opcional): só username, bio e imagem."""

    def to_representation(self, profile):
        url = profile.image.url
        request = self.context.get("request")
        if request is not None:
            url = request.build_absolute_uri(url)
        return {
            "username": profile.user.username,
            "bio": profile.bio,
            "image_url": url,
        }
