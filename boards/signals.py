import os

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_cleanup.signals import cleanup_pre_delete
from sorl.thumbnail import delete

from .models import Board, BoardPreferences

@receiver(post_save, sender=Board)
def create_board_preferences(sender, instance, created, **kwargs):
    if created:
        BoardPreferences.objects.create(board=instance)

@receiver(cleanup_pre_delete)
def sorl_delete(**kwargs):
    delete(kwargs['file'])
