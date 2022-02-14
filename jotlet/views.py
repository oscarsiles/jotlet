from django.contrib.auth.views import LoginView

from jotlet.http import HTTPResponseHXRedirect


class JotletLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_redirect_url())
