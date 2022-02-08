from django.db.models.signals import post_save
from django.dispatch import receiver


from .models import Board, BoardPreferences

@receiver(post_save, sender=Board)
def create_board_preferences(sender, instance, created, **kwargs):
    if created:
        BoardPreferences.objects.create(board=instance)
