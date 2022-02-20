"""jotlet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from . import views

from django_reverse_js import views as views_djrjs

urlpatterns = [
    path("admin/", admin.site.urls),
    path("boards/", include("boards.urls")),
    path("accounts/login/", views.JotletLoginView.as_view(), name="account_login"),
    path("accounts/signup/", views.JotletSignupView.as_view(), name="account_signup"),
    path("accounts/password/change/", views.JotletChangePasswordView.as_view(), name="account_change_password"),
    path("accounts/password/set/", views.JotletSetPasswordView.as_view(), name="account_set_password"),
    path("accounts/", include("allauth.urls")),
    path("", RedirectView.as_view(url="boards/")),
    path("reverse.js", views_djrjs.urls_js, name="reverse_js"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
