from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.templatetags.static import static as static_tag
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView

from accounts.views import JotletLoginView

from . import views

urlpatterns = [
    path("accounts/", include("accounts.urls")),
    path("admin/login/", JotletLoginView.as_view(), name="admin-login"),
    path("admin/", admin.site.urls),
    path("boards/", include("boards.urls")),
    path("notices/", include("notices.urls")),
    path("privacy/", views.PrivacyPolicyView.as_view(), name="privacy-policy"),
    path("terms/", views.TermsOfUseView.as_view(), name="terms-of-use"),
    path(
        "robots.txt",
        cache_page(60 * 60 * 24)(TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    ),
    path("favicon.ico", RedirectView.as_view(url=static_tag("favicon/favicon.ico"))),
    path("", RedirectView.as_view(url="boards/")),
]

if settings.DEBUG_TOOLBAR_ENABLED:
    urlpatterns += (path("__debug__/", include("debug_toolbar.urls")),)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
