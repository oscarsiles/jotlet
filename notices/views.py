from django.http import HttpResponse
from django.views import generic


class ClearNoticeView(generic.View):
    def get(self, request, *args, **kwargs):
        notice = self.kwargs["notice"]
        request.session[notice] = False
        return HttpResponse(status=204)
