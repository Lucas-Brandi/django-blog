from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.
posts = [
    {
        "author": "Corey Schafer",
        "title": "Blog Post 1",
        "content": "First post content",
        "date_posted": "August 27, 2018",
    },
]


@login_required
def home(request):
    context = {
        "posts": posts,
        "title": "Home",
    }
    return render(request, "blog/home.html", context)


@login_required
def about(request):
    context = {
        "title": "About",
    }
    return render(request, "blog/about.html", context)
