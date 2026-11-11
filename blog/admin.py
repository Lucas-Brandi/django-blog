from django.contrib import admin

from .models import Comment, Post, Tag


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "created_at")
    list_select_related = ("post", "author")


admin.site.register(Post)
admin.site.register(Tag)
