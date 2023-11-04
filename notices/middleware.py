from django.contrib import messages


class NoticesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_template_response(self, request, response):
        if not request.htmx and request.user.is_authenticated and request.session.get("beta_message", True):
            messages.add_message(
                request,
                messages.ERROR,
                "This website is still in BETA and may not be stable.",
                extra_tags="beta_message",
            )

        return response
