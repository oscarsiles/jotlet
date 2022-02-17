from allauth.account.views import LoginView, PasswordChangeView, PasswordSetView
from django.contrib.auth.mixins import LoginRequiredMixin

from django.urls import reverse_lazy

from jotlet.http import HTTPResponseHXRedirect


class JotletLoginView(LoginView):
    success_url = reverse_lazy("boards:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())


class JotletChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())

    def get_success_url(self):
        # find your next url here
        next_url = self.request.POST.get("next", None)  # here method should be GET or POST.
        if next_url:
            return "%s" % (next_url)  # you can include some query strings as well
        else:
            return reverse_lazy("boards:index")  # what url you wish to return


class JotletSetPasswordView(PasswordSetView):
    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())

    def get_success_url(self):
        # find your next url here
        next_url = self.request.POST.get("next", None)  # here method should be GET or POST.
        if next_url:
            return "%s" % (next_url)  # you can include some query strings as well
        else:
            return reverse_lazy("boards:index")  # what url you wish to return
