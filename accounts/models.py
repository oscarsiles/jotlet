from functools import cached_property

import auto_prefetch
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords

from boards.models import Board
from jotlet.mixins.refresh_from_db_invalidates_cached_properties import InvalidateCachedPropertiesMixin


class User(AbstractUser):
    optin_newsletter = models.BooleanField(default=False, verbose_name="Opt-in to newsletter")


class UserProfile(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    user = auto_prefetch.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True)

    # user preferences
    boards_paginate_by = models.PositiveSmallIntegerField(default=10)

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
