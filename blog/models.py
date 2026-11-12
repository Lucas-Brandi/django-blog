from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # Ordem cronológica (mais antigos primeiro) para a listagem de comentários.
        ordering = ["created_at", "id"]

    def __str__(self):
        return self.content


class Tag(models.Model):
    name = models.CharField(max_length=100)
    posts = models.ManyToManyField(Post, related_name="tags")

    class Meta:
        constraints = [
            # Evita tags duplicadas sem diferenciar maiúsculas de minúsculas
            # (ex.: "Django" e "django" não coexistem). A normalização para
            # minúsculas é feita no serializer; o constraint é a garantia no banco.
            models.UniqueConstraint(
                Lower("name"),
                name="unique_tag_name_ci",
            ),
        ]

    def __str__(self):
        return self.name
