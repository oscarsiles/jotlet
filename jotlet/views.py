from allauth.account.views import LoginView, PasswordChangeView, PasswordSetView, SignupView
from django.contrib.auth.mixins import LoginRequiredMixin

from django.urls import reverse_lazy

from jotlet.http import HTTPResponseHXRedirect


class JotletLoginView(LoginView):
    success_url = reverse_lazy("boards:index")
    show_modal = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            self.show_modal = True
        context["show_modal"] = self.show_modal
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())


class JotletSignupView(SignupView):
    show_modal = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            self.show_modal = True
        context["show_modal"] = self.show_modal
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())


class JotletChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())

    def get_success_url(self):
        next_url = self.request.POST.get("next", None)
        if next_url:
            return "%s" % (next_url)
        else:
            return reverse_lazy("boards:index")


class JotletSetPasswordView(PasswordSetView):
    def form_valid(self, form):
        response = super().form_valid(form)
        return HTTPResponseHXRedirect(self.get_success_url())

    def get_success_url(self):
        next_url = self.request.POST.get("next", None)
        if next_url:
            return "%s" % (next_url)
        else:
            return reverse_lazy("boards:index")
