from functools import cached_property

import auto_prefetch
from cacheops import invalidate_model
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from simple_history.models import HistoricalRecords

from boards.models import Board
from jotlet.mixins.refresh_from_db_invalidates_cached_properties import InvalidateCachedPropertiesMixin


class User(AbstractUser):
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            perm_list = ["add_board"]
            if settings.TESTING:
                invalidate_model(Permission)
            for perm in perm_list:
                perm = Permission.objects.get(content_type__app_label="boards", codename=perm)
                self.user_permissions.add(perm)
        if not hasattr(self, "profile"):
            UserProfile.objects.create(user=self)


class UserProfile(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    user = auto_prefetch.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords(cascade_delete_history=True, excluded_fields=["user"])

    # user preferences
    optin_newsletter = models.BooleanField(default=False, verbose_name="Opt-in to newsletter")
    boards_paginate_by = models.PositiveSmallIntegerField(default=10)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "profile"

    def __str__(self):
        return f"{self.user.username}'s profile"

    @cached_property
    def get_board_count(self):
        return Board.objects.filter(owner=self.user).count()

    @cached_property
    def get_mod_board_count(self):
        return Board.objects.filter(preferences__moderators__in=[self.user]).count()
