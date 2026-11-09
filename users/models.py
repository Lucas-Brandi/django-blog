from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image

DEFAULT_IMAGE = "profile_pics/default.jpg"
MAX_IMAGE_SIZE = (400, 400)


class Profile(models.Model):
    """Extra profile data attached 1-to-1 to Django's built-in User."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(max_length=300, blank=True)
    image = models.ImageField(default=DEFAULT_IMAGE, upload_to="profile_pics")

    def __str__(self):
        return f"{self.user.username} Profile"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Downscale large uploads so the site never serves oversized images.
        # Lê e grava via Storage API (self.image.open/save) para funcionar tanto
        # no filesystem local quanto em storages remotos (Cloudflare R2), que não
        # expõem self.image.path.
        if not self.image or self.image.name == DEFAULT_IMAGE:
            return

        with self.image.open("rb") as fh:
            img = Image.open(fh)
            if img.height <= MAX_IMAGE_SIZE[1] and img.width <= MAX_IMAGE_SIZE[0]:
                return
            img_format = img.format or "JPEG"
            img.thumbnail(MAX_IMAGE_SIZE)
            buffer = BytesIO()
            img.save(buffer, format=img_format)

        # Regrava o mesmo nome com o conteúdo redimensionado.
        self.image.storage.delete(self.image.name)
        self.image.save(self.image.name, ContentFile(buffer.getvalue()), save=False)
        super().save(update_fields=["image"])


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Every time a User is saved, make sure it has a Profile too.

    - On first save (registration) -> creates the Profile automatically.
    - On every later save of the User -> makes sure the Profile is saved as well.
    """
    # Durante o loaddata os objetos chegam com raw=True e já trazem o Profile
    # no fixture; criar outro aqui causaria UNIQUE constraint em user_id.
    if kwargs.get("raw"):
        return
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()
