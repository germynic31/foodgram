from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(_('email'), unique=True, max_length=254)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    password = models.CharField(_('password'), max_length=150)
    avatar = models.ImageField(
        _('avatar'),
        upload_to='users',
        blank=True,
        null=True,
        default=None
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username', 'password']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ('id',)
