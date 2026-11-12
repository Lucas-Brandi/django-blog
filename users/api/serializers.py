"""Serializers da API de autenticação (M2).

Espelham o contrato das views HTML atuais: e-mail obrigatório no cadastro e
aplicação dos validadores de senha do Django. O `Profile` continua sendo
criado pelo signal `create_or_update_user_profile` em `users/models.py`.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Cadastro de usuário: username, email (obrigatório) e senha + confirmação."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2"]

    def validate_password(self, value):
        # Aplica os AUTH_PASSWORD_VALIDATORS do Django. A similaridade com os
        # atributos do usuário é checada em validate(), onde já temos username/email.
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "As senhas não conferem."})

        user = User(username=attrs.get("username"), email=attrs.get("email"))
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()  # dispara o signal que cria o Profile
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Solicitação de reset: recebe o e-mail. A resposta é sempre a mesma."""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirmação de reset: uid + token + nova senha (com confirmação)."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "As senhas não conferem."})

        user = self._get_user(attrs["uid"])
        if user is None or not default_token_generator.check_token(user, attrs["token"]):
            # Mensagem genérica: não revela se o uid ou o token é que falhou.
            raise serializers.ValidationError({"token": "Link inválido ou expirado."})

        # Valida a nova senha com SetPasswordForm (mesmos validadores das views HTML).
        form = SetPasswordForm(
            user=user,
            data={"new_password1": attrs["new_password"], "new_password2": attrs["new_password2"]},
        )
        if not form.is_valid():
            raise serializers.ValidationError({"new_password": form.errors.get("new_password2", ["Senha inválida."])})

        attrs["user"] = user
        attrs["form"] = form
        return attrs

    @staticmethod
    def _get_user(uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def save(self):
        form = self.validated_data["form"]
        return form.save()


def make_reset_token(user):
    """Gera (uidb64, token) para o link de reset de senha."""
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


# --- Serializers apenas de resposta (documentação OpenAPI / M7) --------------


class RegisterResponseSerializer(serializers.Serializer):
    """Resposta do cadastro: dados básicos do usuário criado."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()


class DetailResponseSerializer(serializers.Serializer):
    """Resposta genérica com uma mensagem em `detail`."""

    detail = serializers.CharField()
