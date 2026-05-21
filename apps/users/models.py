from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User model for SimTrade Platform.
    Extends Django's AbstractUser with additional fields.
    """
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username
