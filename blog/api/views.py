"""Views da API de posts (M4).

Endpoints sob /api/v1/posts/:
  - GET  /api/v1/posts/           lista paginada (mais recentes primeiro)
  - POST /api/v1/posts/           cria (autenticado; author = request.user)
  - GET  /api/v1/posts/<id>/      detalhe
  - PUT/PATCH /api/v1/posts/<id>/ atualiza (só o autor ou staff)
  - DELETE    /api/v1/posts/<id>/ remove (só o autor ou staff)

Busca opcional via ?search= no título e no conteúdo.
"""

from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from blog.models import Post

from .permissions import IsAuthorOrStaffOrReadOnly
from .serializers import PostSerializer


class PostListCreateView(generics.ListCreateAPIView):
    """GET lista (paginada, mais recentes primeiro) e POST cria um post."""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # select_related no autor e prefetch das tags evitam N+1 na listagem.
        queryset = Post.objects.select_related("author").prefetch_related("tags").order_by("-created_at", "-id")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))
        return queryset

    def perform_create(self, serializer):
        # O autor nunca vem do corpo da requisição: é sempre o usuário logado.
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT/PATCH e DELETE de um post. Alterar/excluir só o autor ou staff."""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrStaffOrReadOnly]
    queryset = Post.objects.select_related("author").prefetch_related("tags")
