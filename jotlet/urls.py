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
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView

from . import views

urlpatterns = [
    path("accounts/", include("accounts.urls")),
    path("admin/", admin.site.urls),
    path("boards/", include("boards.urls")),
    path("notices/", include("notices.urls")),
    path("privacy/", views.PrivacyPolicyView.as_view(), name="privacy-policy"),
    path("terms/", views.TermsOfUseView.as_view(), name="terms-of-use"),
    path("qr_code/", include("qr_code.urls", namespace="qr_code")),
    path(
        "robots.txt",
        cache_page(60 * 60 * 24)(TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    ),
    path("favicon.ico", RedirectView.as_view(url=staticfiles_storage.url("favicon/favicon.ico"))),
    path("", RedirectView.as_view(url="boards/")),
]

if settings.DEBUG_TOOLBAR_ENABLED:
    urlpatterns += (path("__debug__/", include("debug_toolbar.urls")),)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
