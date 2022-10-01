from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.forms import models

admin.site.site_title = "Jotlet Administration"
admin.site.site_header = admin.site.site_title
admin.site.login = login_required(admin.site.login)


class DisableDeleteInlineFormSet(models.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_delete = False
