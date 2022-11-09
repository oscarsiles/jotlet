from django.urls import include, path

from . import views

urlpatterns = [
    path("delete/", views.JotletAccountDeleteView.as_view(), name="account_delete"),
    path("lockout/", views.JotletLockoutView.as_view(), name="account_lockout"),
    path("login/", views.JotletLoginView.as_view(), name="account_login"),
    path("logout/", views.JotletLogoutView.as_view(), name="account_logout"),
    path("password/change/", views.JotletChangePasswordView.as_view(), name="account_change_password"),
    path("password/set/", views.JotletSetPasswordView.as_view(), name="account_set_password"),
    path("profile/", views.JotletProfileView.as_view(), name="account_profile"),
    path("profile/edit/", views.JotletProfileEditView.as_view(), name="account_profile_edit"),
    path("signup/", views.JotletSignupView.as_view(), name="account_signup"),
    path("social/signup/", views.JotletSocialSignupView.as_view(), name="socialaccount_signup"),
    path("", include("allauth.urls")),
]
