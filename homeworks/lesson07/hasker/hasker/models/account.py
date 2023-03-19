from django.contrib.auth.models import AbstractUser
from django.db import models


def get_upload_path():
    """"""
    return 'media/'


class User(AbstractUser):
    """
    Users within the Django authentication system are represented by this
    model.

    Username and password are required. Other fields are optional.
    """
    avatar = models.FileField('Аватар', upload_to=get_upload_path, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"
        db_table = 'auth.User'
