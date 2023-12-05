import uuid
from functools import cached_property

import auto_prefetch
from cacheops import invalidate_model
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission
from django.contrib.postgres.functions import RandomUUID
from django.contrib.postgres.indexes import BrinIndex
from django.db import models
from django.db.models.functions import Now

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
            for perm_str in perm_list:
                perm = Permission.objects.get(content_type__app_label="boards", codename=perm_str)
                self.user_permissions.add(perm)
        if not hasattr(self, "profile"):
            UserProfile.objects.create(user=self)


class UserProfile(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, db_default=RandomUUID(), editable=False)
    user = auto_prefetch.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    created_at = models.DateTimeField(db_default=Now(), editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    # user preferences
    optin_newsletter = models.BooleanField(db_default=False, verbose_name="Opt-in to newsletter")
    boards_paginate_by = models.PositiveSmallIntegerField(db_default=10)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "profile"
        indexes = [
            BrinIndex(fields=["created_at"], autosummarize=True),
        ]

    def __str__(self):
        return f"{self.user.username}'s profile"

    @cached_property
    def get_board_count(self):
        return Board.objects.filter(owner=self.user).count()

    @cached_property
    def get_mod_board_count(self):
        return Board.objects.filter(preferences__moderators__in=[self.user]).count()
