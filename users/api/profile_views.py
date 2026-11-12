"""Views do perfil do usuário (M3).

Endpoints sob /api/v1/users/:
  - me/            GET/PATCH do próprio perfil (multipart suportado)
  - me/image/      DELETE restaura a imagem padrão
  - <username>/    GET perfil público (opcional)
"""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import DEFAULT_IMAGE, Profile

from .profile_serializers import ProfileSerializer, PublicProfileSerializer

User = get_user_model()


@extend_schema(tags=["users"])
class MeView(APIView):
    """GET/PATCH /api/v1/users/me/ — lê e atualiza o próprio perfil.

    Opera sempre sobre request.user.profile, então um usuário nunca consegue
    alterar o perfil de outro (não há id na URL).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get_profile(self, request):
        # get_or_create protege contra o caso raro de um User sem Profile.
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return profile

    @extend_schema(summary="Lê o próprio perfil", responses={200: ProfileSerializer})
    def get(self, request):
        profile = self._get_profile(request)
        serializer = ProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Atualiza o próprio perfil",
        request=ProfileSerializer,
        responses={200: ProfileSerializer},
    )
    def patch(self, request):
        profile = self._get_profile(request)
        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(
    tags=["users"],
    summary="Restaura a imagem de perfil padrão",
    responses={200: ProfileSerializer},
)
class MeImageView(APIView):
    """DELETE /api/v1/users/me/image/ — restaura a imagem de perfil padrão."""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        old_name = profile.image.name
        # Nunca apaga a imagem padrão compartilhada; só remove a foto do usuário.
        if old_name and old_name != DEFAULT_IMAGE:
            profile.image.storage.delete(old_name)
        profile.image = DEFAULT_IMAGE
        profile.save()
        serializer = ProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["users"],
    summary="Perfil público de um usuário",
    responses={200: PublicProfileSerializer},
)
class PublicProfileView(APIView):
    """GET /api/v1/users/<username>/ — perfil público (username, bio, imagem)."""

    permission_classes = [AllowAny]

    def get(self, request, username):
        profile = get_object_or_404(
            Profile.objects.select_related("user"),
            user__username=username,
        )
        serializer = PublicProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)
