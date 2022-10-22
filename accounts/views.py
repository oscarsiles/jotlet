from allauth.account.utils import has_verified_email
from allauth.account.views import LoginView, LogoutView, PasswordChangeView, PasswordSetView, SignupView
from allauth.socialaccount.views import SignupView as SocialSignupView
from axes.decorators import axes_dispatch, axes_form_invalid
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django_htmx.http import HttpResponseClientRedirect, HttpResponseClientRefresh

from boards.mixins import BoardListLinkHeaderMixin
from jotlet.mixins import JotletLinkHeaderMixin
from jotlet.utils import generate_link_header

from .forms import CustomLoginForm, CustomProfileEditForm, CustomSignupForm, CustomSocialSignupForm


class JotletDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = get_user_model()
    success_url = reverse_lazy("boards:index")
    template_name = "accounts/user_delete.html"

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return redirect("account_profile")
        response = super().form_valid(form)
        messages.add_message(
            self.request,
            messages.SUCCESS,
            f"Your account ({self.request.user.username}) was successfully deleted.",
        )
        return response


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
        if not form.cleaned_data["remember_me"]:
            self.request.session.set_expiry(0)
            self.request.session.modified = True

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


class JotletProfileView(JotletLinkHeaderMixin, BoardListLinkHeaderMixin, LoginRequiredMixin, generic.DetailView):
    context_object_name = "user"
    template_name = "accounts/profile.html"

    def get_template_names(self):
        templates = super().get_template_names()
        if self.request.htmx:
            templates[0] = "accounts/components/profile_detail.html"
        return templates

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_email_verified"] = has_verified_email(self.request.user, email=None)
        return context

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        files_css = []
        files_js = [static("accounts/js/profile.js")]

        response = generate_link_header(response, files_css, files_js)
        return response


class JotletProfileEditView(LoginRequiredMixin, generic.UpdateView):
    model = get_user_model()
    form_class = CustomProfileEditForm
    template_name = "accounts/components/forms/profile_edit.html"

    def get_object(self):
        return self.request.user

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["optin_newsletter"] = self.request.user.profile.optin_newsletter
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.user.profile.optin_newsletter = form.cleaned_data["optin_newsletter"]
        self.request.user.profile.save()
        return response

    def get_success_url(self):
        return reverse_lazy("account_profile")


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
