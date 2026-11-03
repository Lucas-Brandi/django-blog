from PIL import Image

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Extra profile data attached 1-to-1 to Django's built-in User."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(max_length=300, blank=True)
    image = models.ImageField(
        default="profile_pics/default.jpg", upload_to="profile_pics"
    )

    def __str__(self):
        return f"{self.user.username} Profile"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Downscale large uploads so the site never serves oversized images.
        img = Image.open(self.image.path)
        max_size = (400, 400)
        if img.height > max_size[1] or img.width > max_size[0]:
            img.thumbnail(max_size)
            img.save(self.image.path)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Every time a User is saved, make sure it has a Profile too.

    - On first save (registration) -> creates the Profile automatically.
    - On every later save of the User -> makes sure the Profile is saved as well.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()
