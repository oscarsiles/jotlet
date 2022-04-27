from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    optin_newsletter = models.BooleanField(default=False)
    history = HistoricalRecords(cascade_delete_history=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
