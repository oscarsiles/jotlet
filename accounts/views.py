from allauth.account.views import LoginView, LogoutView, PasswordChangeView, PasswordSetView, SignupView
from allauth.socialaccount.views import SignupView as SocialSignupView
from axes.decorators import axes_dispatch, axes_form_invalid
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh

from .forms import CustomLoginForm, CustomSignupForm, CustomSocialSignupForm


@method_decorator(axes_dispatch, name="dispatch")
@method_decorator(axes_form_invalid, name="form_invalid")
class JotletLoginView(LoginView):
    show_modal = False
    form_class = CustomLoginForm
    success_url = reverse_lazy("boards:index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            self.show_modal = True
        context["show_modal"] = self.show_modal
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponseClientRedirect(self.get_success_url())


class JotletLockoutView(generic.TemplateView):
    show_modal = False
    template_name = "accounts/lockout.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            self.show_modal = True
        context["show_modal"] = self.show_modal
        context["cooloff_time"] = f"{int(settings.AXES_COOLOFF_TIME.total_seconds()/60)} minutes"
        return context


class JotletLogoutView(LogoutView):
    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        return HttpResponseClientRefresh()


class JotletSignupView(SignupView):
    show_modal = False
    form_class = CustomSignupForm
    success_url = reverse_lazy("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            self.show_modal = True
        context["show_modal"] = self.show_modal
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        return HttpResponseClientRedirect(response.get("Location", "/"))


class JotletSocialSignupView(SocialSignupView):
    form_class = CustomSocialSignupForm


class JotletChangePasswordView(LoginRequiredMixin, PasswordChangeView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_page = self.request.GET.get("next")
        if next_page:
            context["next"] = next_page
        return context

    def form_valid(self, form):
        super().form_valid(form)
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
        super().form_valid(form)
        return HttpResponseClientRedirect(self.get_success_url())

    def get_success_url(self):
        next_url = self.request.POST.get("next", None)
        if next_url:
            return next_url
        else:
            return reverse_lazy("boards:index")
