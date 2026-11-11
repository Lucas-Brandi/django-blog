"""Permissões da API de posts (M4).

Decisão D2 (leitura dos posts): a leitura é pública (qualquer um lista e vê
posts, sem autenticação), espelhando o perfil público já existente em M3.
A escrita exige autenticação e a edição/exclusão fica restrita ao autor
(ou a um usuário staff).
"""

from rest_framework import permissions


class IsAuthorOrStaffOrReadOnly(permissions.BasePermission):
    """Leitura liberada; escrita só autenticado; alterar/excluir só autor ou staff.

    - Métodos seguros (GET, HEAD, OPTIONS): sempre permitidos.
    - Métodos de escrita (POST): exigem usuário autenticado (checado no nível
      da view/queryset via IsAuthenticatedOrReadOnly).
    - Alterar/excluir um objeto específico (PUT/PATCH/DELETE): só o autor do
      post ou um usuário staff.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author_id == request.user.id or request.user.is_staff


class CanDeleteComment(permissions.BasePermission):
    """Excluir/editar um comentário: autor do comentário, autor do post ou staff (D5).

    - Métodos seguros (GET, HEAD, OPTIONS): sempre permitidos.
    - DELETE/edição: liberado ao autor do comentário, ao autor do post comentado
      ou a um usuário staff.
    """

    def has_object_permission(self, request, view, comment):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            comment.author_id == request.user.id or comment.post.author_id == request.user.id or request.user.is_staff
        )
