"""Views da API de posts (M4).

Endpoints sob /api/v1/posts/:
  - GET  /api/v1/posts/           lista paginada (mais recentes primeiro)
  - POST /api/v1/posts/           cria (autenticado; author = request.user)
  - GET  /api/v1/posts/<id>/      detalhe
  - PUT/PATCH /api/v1/posts/<id>/ atualiza (só o autor ou staff)
  - DELETE    /api/v1/posts/<id>/ remove (só o autor ou staff)

Busca opcional via ?search= no título e no conteúdo.
"""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from blog.models import Comment, Post, Tag

from .comment_serializers import CommentSerializer
from .permissions import CanDeleteComment, IsAuthorOrStaffOrReadOnly
from .serializers import PostSerializer, TagSerializer


@extend_schema(tags=["posts"])
@extend_schema(
    methods=["GET"],
    summary="Lista posts (paginado, mais recentes primeiro)",
    parameters=[
        OpenApiParameter("search", str, description="Busca por título e conteúdo."),
        OpenApiParameter("tag", str, description="Filtra posts pela tag (case-insensitive)."),
    ],
)
@extend_schema(
    methods=["POST"],
    summary="Cria um post (autenticado; author = usuário logado)",
    examples=[
        OpenApiExample(
            "Post com tags",
            value={"title": "Meu post", "content": "Conteúdo do post.", "tag_input": ["django", "rest"]},
            request_only=True,
        )
    ],
)
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
        # Filtro por tag (M5): ?tag=<nome>, sem diferenciar maiúsculas/minúsculas.
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__name__iexact=tag.strip()).distinct()
        return queryset

    def perform_create(self, serializer):
        # O autor nunca vem do corpo da requisição: é sempre o usuário logado.
        serializer.save(author=self.request.user)


@extend_schema(tags=["posts"])
class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PUT/PATCH e DELETE de um post. Alterar/excluir só o autor ou staff."""

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrStaffOrReadOnly]
    queryset = Post.objects.select_related("author").prefetch_related("tags")


@extend_schema(tags=["tags"])
@extend_schema(
    methods=["POST"],
    examples=[OpenApiExample("Nova tag", value={"name": "django"}, request_only=True)],
)
class TagListCreateView(generics.ListCreateAPIView):
    """GET lista de tags (com contagem de posts) e POST cria uma tag (M5).

    Leitura pública (D2/D3); criação exige autenticação. A contagem de posts
    vem anotada no queryset para evitar N+1.
    """

    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Tag.objects.annotate(post_count=Count("posts")).order_by("name")


@extend_schema(tags=["comments"])
@extend_schema(
    methods=["POST"],
    examples=[OpenApiExample("Novo comentário", value={"content": "Ótimo post!"}, request_only=True)],
)
class CommentListCreateView(generics.ListCreateAPIView):
    """GET e POST /api/v1/posts/<post_id>/comments/ (M6).

    Lista os comentários de um post em ordem cronológica (paginada) e cria um
    novo comentário. Exige login conforme D5; o autor vem de request.user e o
    post vem da URL (nunca do corpo).
    """

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def _get_post(self):
        # 404 se o post não existir, antes de listar/criar comentários.
        return get_object_or_404(Post, pk=self.kwargs["post_id"])

    def get_queryset(self):
        # select_related no autor evita N+1 ao serializar cada comentário.
        return (
            Comment.objects.filter(post_id=self.kwargs["post_id"]).select_related("author").order_by("created_at", "id")
        )

    def perform_create(self, serializer):
        # O autor é sempre o usuário logado; o post vem da URL.
        serializer.save(author=self.request.user, post=self._get_post())


@extend_schema(tags=["comments"])
class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET, PATCH/PUT e DELETE /api/v1/comments/<id>/ (M6).

    DELETE (e edição opcional) são liberados ao autor do comentário, ao autor
    do post ou a staff (D5). A leitura segue a mesma exigência de login dos
    demais endpoints de comentário.
    """

    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, CanDeleteComment]
    queryset = Comment.objects.select_related("author", "post")
