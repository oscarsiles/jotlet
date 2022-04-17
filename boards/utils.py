from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Reaction


def channel_group_send(group_name, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name, message)
