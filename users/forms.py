from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class UserUpdateForm(forms.ModelForm):
    """Lets a logged-in user update their basic account info."""

    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email"]


class ProfileUpdateForm(forms.ModelForm):
    """Lets a logged-in user update (or remove) their profile picture and bio."""

    # Django's ClearableFileInput already renders a "Clear" checkbox,
    # so removing the photo is handled by the same field.
    image = forms.ImageField(required=False)

    class Meta:
        model = Profile
        fields = ["image", "bio"]
