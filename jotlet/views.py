from django.conf import settings
from django.shortcuts import render
from django.views import generic


def handler500(request, *args, **argv):
    if settings.SENTRY_ENABLED:
        from sentry_sdk import last_event_id

        sentry_event_id = last_event_id()
        return render(request, "500.html", {"sentry_event_id": sentry_event_id}, status=500)
    else:
        return render(request, "500.html", status=500)


class PrivacyPolicyView(generic.TemplateView):
    template_name = "privacy_policy.html"


class TermsOfUseView(generic.TemplateView):
    template_name = "terms.html"
