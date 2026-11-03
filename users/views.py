from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render

from .forms import ProfileUpdateForm, UserRegisterForm, UserUpdateForm


def _style_form(form):
    for field in form.fields.values():
        css = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = f"{css} form-control".strip()
    return form


class StyledFormMixin:
    page_title = ""

    def get_form(self, form_class=None):
        return _style_form(super().get_form(form_class))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("title", self.page_title)
        return context


class UserLoginView(StyledFormMixin, LoginView):
    template_name = "users/login.html"
    page_title = "Login"


class UserLogoutView(LogoutView):
    template_name = "users/logout.html"
    extra_context = {"title": "Logout"}


class UserPasswordResetView(StyledFormMixin, PasswordResetView):
    template_name = "users/password_reset.html"
    email_template_name = "users/password_reset_email.html"
    page_title = "Forgot password"


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "users/password_reset_done.html"
    extra_context = {"title": "Email sent"}


class UserPasswordResetConfirmView(StyledFormMixin, PasswordResetConfirmView):
    template_name = "users/password_reset_confirm.html"
    page_title = "New password"


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "users/password_reset_complete.html"
    extra_context = {"title": "Password reset"}


def register(request):
    if request.method == "POST":
        form = _style_form(UserRegisterForm(request.POST))
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your account has been created. You can log in now.",
            )
            return redirect("login")
    else:
        form = _style_form(UserRegisterForm())

    return render(
        request,
        "users/register.html",
        {
            "form": form,
            "title": "Register",
        },
    )


@login_required
def profile(request):
    if request.method == "POST":
        u_form = _style_form(UserUpdateForm(request.POST, instance=request.user))
        p_form = _style_form(
            ProfileUpdateForm(
                request.POST,
                request.FILES,
                instance=request.user.profile,
            )
        )

        # "Remove photo" button: reset to the default picture and skip
        # validation of the (empty) file/bio inputs from that click.
        if "remove_picture" in request.POST:
            request.user.profile.image.delete(save=False)
            request.user.profile.image = "profile_pics/default.jpg"
            request.user.profile.save()
            messages.success(request, "Your profile picture has been removed.")
            return redirect("profile")

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("profile")
    else:
        u_form = _style_form(UserUpdateForm(instance=request.user))
        p_form = _style_form(ProfileUpdateForm(instance=request.user.profile))

    return render(
        request,
        "users/profile.html",
        {
            "u_form": u_form,
            "p_form": p_form,
            "title": "Profile",
        },
    )
