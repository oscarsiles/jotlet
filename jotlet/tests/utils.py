from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django_htmx.middleware import HtmxMiddleware


def create_session(request):
    session_middleware = SessionMiddleware(request)
    session_middleware.process_request(request)
    request.session.save()


def create_htmx_session(request):
    def dummy_view(_request):
        return HttpResponse()

    create_session(request)
    htmx_middleware = HtmxMiddleware(dummy_view)
    htmx_middleware(request)
