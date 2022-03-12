from urllib.parse import urlparse

import django_filters
from django.db.models import Q
from django.urls import resolve

from .forms import BoardFilterForm
from .models import Board


class BoardFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_title_description", label="Title/Description")
    owner = django_filters.CharFilter(method="filter_username", label="User")
    is_all_boards = False

    class Meta:
        model = Board
        form = BoardFilterForm
        fields = [
            "q",
            "owner",
        ]

    def __init__(self, *args, **kwargs):
        self.is_all_boards = kwargs.pop("is_all_boards", False)
        super().__init__(*args, **kwargs)
        if not self.is_all_boards:
            self.filters.pop("owner")

    @property
    def qs(self):
        qs = super().qs
        if self.is_all_boards:
            queryset = qs.order_by("-created_at")
        else:
            queryset = qs.filter(owner=self.request.user).order_by("-created_at")

        return queryset

    def filter_title_description(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))

    def filter_username(self, queryset, name, value):
        if value[0] != "":
            return queryset.filter(owner__username__in=value.split(","))
        return queryset