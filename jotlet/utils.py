import datetime

from django.utils import timezone


def offset_date(days=0, hours=0, minutes=0, seconds=0):
    return timezone.now() + datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
