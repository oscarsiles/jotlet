from django.views import generic


class PrivacyPolicyView(generic.TemplateView):
    template_name = "privacy_policy.html"


class TermsOfUseView(generic.TemplateView):
    template_name = "terms.html"
