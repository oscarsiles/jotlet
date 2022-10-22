from functools import cached_property

import auto_prefetch
from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from boards.models import Board


class UserProfile(auto_prefetch.Model):
    user = auto_prefetch.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    optin_newsletter = models.BooleanField(default=False, verbose_name="Opt-in to newsletter")
    history = HistoricalRecords(cascade_delete_history=True)

    class Meta:
        verbose_name = "profile"

    def __str__(self):
        return f"{self.user.username}'s profile"

    @cached_property
    def get_board_count(self):
        return Board.objects.filter(owner=self.user).count()

    @cached_property
    def get_mod_board_count(self):
        return Board.objects.filter(preferences__moderators__in=[self.user]).count()
