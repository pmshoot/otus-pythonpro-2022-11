from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Профиль пользователя

    - аватар (jpeg, png, gif)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField('Аватар',
                               upload_to='images/profile',
                               max_length=500,
                               default='images/profile/default.jpg',
                               blank=True)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance: User, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
