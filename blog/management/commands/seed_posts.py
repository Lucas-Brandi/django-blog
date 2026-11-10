"""Seed de posts de exemplo para o desenvolvimento do front (M4).

Cria um usuário de exemplo (se necessário), algumas tags e posts, para que o
front React tenha dados reais ao consumir GET /api/v1/posts/.

Uso:
    python manage.py seed_posts            # cria ~5 posts de exemplo
    python manage.py seed_posts --count 20 # cria 20 posts
    python manage.py seed_posts --clear    # apaga os posts antes de semear

O comando é idempotente no usuário/tags (get_or_create); sem --clear ele
apenas acrescenta novos posts.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from blog.models import Post, Tag

User = get_user_model()

SEED_USERNAME = "demo_author"
SEED_EMAIL = "demo_author@example.com"

SAMPLE_TAGS = ["django", "python", "rest", "frontend", "backend"]

SAMPLE_POSTS = [
    (
        "Primeiros passos com a API",
        "Como consumir os endpoints da API REST do blog a partir do front React.",
        ["django", "rest"],
    ),
    (
        "Autenticação com JWT",
        "Entenda o fluxo de login, refresh e logout usando tokens JWT.",
        ["backend", "rest"],
    ),
    (
        "Paginação na listagem",
        "A listagem de posts é paginada; veja como navegar entre as páginas.",
        ["rest", "frontend"],
    ),
    (
        "Escrevendo o primeiro post",
        "Só usuários autenticados podem criar posts, e o autor vem do token.",
        ["backend", "python"],
    ),
    (
        "Organizando com tags",
        "As tags ajudam a categorizar os posts e aparecem na resposta da API.",
        ["django", "python"],
    ),
]


class Command(BaseCommand):
    help = "Cria posts de exemplo para o desenvolvimento do front."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=len(SAMPLE_POSTS),
            help="Quantidade de posts a criar (padrão: %(default)s).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Apaga todos os posts existentes antes de semear.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            self.stderr.write(self.style.ERROR("--count precisa ser >= 1."))
            return

        if options["clear"]:
            deleted, _ = Post.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Posts removidos: {deleted}."))

        author, created = User.objects.get_or_create(
            username=SEED_USERNAME,
            defaults={"email": SEED_EMAIL},
        )
        if created:
            author.set_unusable_password()
            author.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"Usuário de exemplo criado: {SEED_USERNAME}."))

        tags = {name: Tag.objects.get_or_create(name=name)[0] for name in SAMPLE_TAGS}

        created_count = 0
        for index in range(count):
            title, content, tag_names = SAMPLE_POSTS[index % len(SAMPLE_POSTS)]
            # Numera o título quando o count excede a lista base, para não repetir.
            if index >= len(SAMPLE_POSTS):
                title = f"{title} ({index + 1})"
            post = Post.objects.create(title=title, content=content, author=author)
            post.tags.set(tags[name] for name in tag_names)
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Posts criados: {created_count}."))
