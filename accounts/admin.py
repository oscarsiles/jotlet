from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from jotlet.admin import DisableDeleteInlineFormSet

from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    formset = DisableDeleteInlineFormSet
    extra = 0


@admin.register(get_user_model())
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional info",
            {
                "fields": ("optin_newsletter",),
            },
        ),
    )
    inlines = [UserProfileInline]
