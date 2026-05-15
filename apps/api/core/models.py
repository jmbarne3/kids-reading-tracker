from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model.

    Roles:
    - parent: Full account. Can manage child accounts and child profiles.
    - child:  Full account (13+). Linked to a parent account via `parent` FK.

    Children under 13 who don't need their own login are represented by
    ChildProfile instead.
    """

    ROLE_PARENT = 'parent'
    ROLE_CHILD = 'child'
    ROLE_CHOICES = [
        (ROLE_PARENT, 'Parent'),
        (ROLE_CHILD, 'Child'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PARENT)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_accounts',
        limit_choices_to={'role': ROLE_PARENT},
    )
    date_of_birth = models.DateField(null=True, blank=True)
    avatar_url = models.URLField(blank=True)

    class Meta:
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return f'{self.email} ({self.role})'


class ChildProfile(models.Model):
    """
    Lightweight, no-login profile for children managed by a parent account.
    Used when the child is under 13 or when the family prefers a simple
    profile-selection flow without per-child passwords.
    An optional PIN can be set to restrict profile switching.
    """

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='child_profiles',
        limit_choices_to={'role': User.ROLE_PARENT},
    )
    name = models.CharField(max_length=100)
    avatar_url = models.URLField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    # Stored as a Django password hash; blank means no PIN required
    pin = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_pin(self, raw_pin: str) -> None:
        self.pin = make_password(raw_pin)

    def check_pin(self, raw_pin: str) -> bool:
        return check_password(raw_pin, self.pin)

    def __str__(self):
        return f'{self.name} (child of {self.parent.email})'


class SocialAccount(models.Model):
    """Links a third-party OAuth identity to a User account."""

    PROVIDER_GOOGLE = 'google'
    PROVIDER_APPLE = 'apple'
    PROVIDER_CHOICES = [
        (PROVIDER_GOOGLE, 'Google'),
        (PROVIDER_APPLE, 'Apple'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    # Apple may use a private relay address or omit email on subsequent logins
    email = models.EmailField(blank=True)

    class Meta:
        unique_together = ('provider', 'provider_user_id')

    def __str__(self):
        return f'{self.provider}:{self.provider_user_id} → {self.user.email}'
