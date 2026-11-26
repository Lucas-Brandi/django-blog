"""Views da API de autenticação (M2).

Endpoints sob /api/v1/auth/:
  - register/          cadastro de usuário
  - login/             obtém o par de tokens (access + refresh)
  - refresh/           renova o access token
  - logout/            revoga o refresh token (blacklist)
  - password-reset/            solicita e-mail de reset (resposta genérica)
  - password-reset/confirm/    define a nova senha com uid + token
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    DetailResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterResponseSerializer,
    RegisterSerializer,
    make_reset_token,
)

User = get_user_model()

# Resposta padrão do fluxo de reset: idêntica exista ou não o e-mail, para não
# revelar quais endereços têm conta cadastrada.
_RESET_GENERIC_RESPONSE = {"detail": "Se o e-mail existir, enviaremos as instruções de redefinição."}


@extend_schema(
    tags=["auth"],
    summary="Cadastro de usuário (com login automático)",
    request=RegisterSerializer,
    responses={201: RegisterResponseSerializer},
)
class RegisterView(APIView):
    """POST /api/v1/auth/register/ — cria um usuário e já o autentica.

    Devolve o par de tokens JWT no mesmo formato do login (access + refresh,
    no corpo da resposta — o login não grava cookie), junto com os dados
    básicos do usuário. O Profile continua vindo do signal.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Login automático: mesmo par de tokens que o endpoint de login retorna.
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {"id": user.id, "username": user.username, "email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["auth"], summary="Login (obtém o par de tokens JWT)")
class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — retorna o par de tokens. Throttle por IP."""

    permission_classes = [AllowAny]
    throttle_scope = "login"


@extend_schema(
    tags=["auth"],
    summary="Logout (revoga o refresh token)",
    request=inline_serializer(
        name="LogoutRequest",
        fields={"refresh": serializers.CharField()},
    ),
    responses={205: OpenApiResponse(description="Refresh token revogado (blacklist).")},
)
class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — coloca o refresh token na blacklist."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"refresh": ["Este campo é obrigatório."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response({"refresh": ["Token inválido ou expirado."]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(
    tags=["auth"],
    summary="Solicita redefinição de senha",
    request=PasswordResetRequestSerializer,
    responses={200: DetailResponseSerializer},
)
class PasswordResetRequestView(APIView):
    """POST /api/v1/auth/password-reset/ — envia e-mail com o link do front."""

    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Envia o e-mail apenas quando a conta existe, mas a resposta é sempre igual.
        for user in User.objects.filter(email__iexact=email, is_active=True):
            self._send_reset_email(user)

        return Response(_RESET_GENERIC_RESPONSE, status=status.HTTP_200_OK)

    @staticmethod
    def _send_reset_email(user):
        uid, token = make_reset_token(user)
        reset_link = f"{settings.FRONTEND_URL}/password-reset/confirm/{uid}/{token}"
        body = render_to_string(
            "users/api/password_reset_email.txt",
            {"user": user, "reset_link": reset_link},
        )
        send_mail(
            subject="Redefinição de senha",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )


@extend_schema(
    tags=["auth"],
    summary="Confirma a redefinição de senha",
    request=PasswordResetConfirmSerializer,
    responses={200: DetailResponseSerializer},
)
class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password-reset/confirm/ — troca a senha via uid + token."""

    permission_classes = [AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Senha redefinida com sucesso."}, status=status.HTTP_200_OK)
