from django.urls import include, path
from django.views import generic

from . import views

urlpatterns = [
    path("login/", views.JotletLoginView.as_view(), name="account_login"),
    path("signup/", views.JotletSignupView.as_view(), name="account_signup"),
    path("password/change/", views.JotletChangePasswordView.as_view(), name="account_change_password"),
    path("password/set/", views.JotletSetPasswordView.as_view(), name="account_set_password"),
    path("", include("allauth.urls")),
]
