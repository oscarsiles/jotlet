from allauth.account.views import LoginView, LogoutView, PasswordChangeView, PasswordSetView, SignupView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh


class JotletLoginView(LoginView):
    show_modal = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            self.show_modal = True
        context["show_modal"] = self.show_modal
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return HttpResponseClientRedirect(self.get_success_url())


class JotletLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        return HttpResponseClientRefresh()


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
        return HttpResponseClientRedirect(response.get("Location"))


class JotletChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_page = self.request.GET.get("next")
        if next_page:
            context["next"] = next_page
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return HttpResponseClientRedirect(self.get_success_url())

    def get_success_url(self):
        next_url = self.request.POST.get("next", None)
        if next_url:
            return next_url
        else:
            return reverse_lazy("boards:index")


class JotletSetPasswordView(PasswordSetView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_page = self.request.GET.get("next")
        if next_page:
            context["next"] = next_page
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return HttpResponseClientRedirect(self.get_success_url())

    def get_success_url(self):
        next_url = self.request.POST.get("next", None)
        if next_url:
            return next_url
        else:
            return reverse_lazy("boards:index")
