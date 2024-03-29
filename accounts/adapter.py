import contextlib

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import perform_login
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model


class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """
        Whether to allow sign ups.
        """
        allow_signups = super().is_open_for_signup(request)
        # Override with setting, otherwise default to super.
        return getattr(settings, "ACCOUNT_ALLOW_SIGNUPS", allow_signups)

    def save_user(self, request, user, form):
        user = super().save_user(request, user, form)
        user.profile.optin_newsletter = form.cleaned_data["optin_newsletter"]
        user.profile.save(update_fields=["optin_newsletter"])
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        """
        Whether to allow sign ups.
        """
        allow_signups = super().is_open_for_signup(request, sociallogin)
        # Override with setting, otherwise default to super.
        return getattr(settings, "SOCIALACCOUNT_ALLOW_SIGNUPS", allow_signups)

    def pre_social_login(self, request, sociallogin):
        # if user exists, connect the account to the existing account and login
        user = sociallogin.user
        if user.id:
            return
        with contextlib.suppress(get_user_model().DoesNotExist):
            user = get_user_model().objects.get(email__iexact=user.email)
            sociallogin.state["process"] = "connect"
            perform_login(request, user, "none")

    def populate_user(self, request, sociallogin, data):
        if sociallogin.account.provider == "microsoft":
            data["email"] = sociallogin.account.extra_data["userPrincipalName"] or data["email"]
            sociallogin.email_addresses[0].email = (
                sociallogin.account.extra_data["userPrincipalName"] or data["email"]
            )
        return super().populate_user(request, sociallogin, data)
