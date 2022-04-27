from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from jotlet.admin import DisableDeleteInlineFormSet

from .models import UserProfile

admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    formset = DisableDeleteInlineFormSet
    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
