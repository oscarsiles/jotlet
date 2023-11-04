from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.forms import models

from jotlet import settings

admin.site.site_title = "Jotlet Administration"
admin.site.site_header = admin.site.site_title


class DisableDeleteInlineFormSet(models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_delete = False
