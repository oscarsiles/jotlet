from django.urls import path

from . import views

app_name = "notices"
urlpatterns = [
    path("clear/<str:notice>", views.ClearNoticeView.as_view(), name="clear-notice"),
]
