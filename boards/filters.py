from functools import reduce

import django_filters
from django.db.models import Q

from .forms import BoardFilterForm
from .models import Board


class BoardFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method="filter_title_description", label="Title/Description")
    owner = django_filters.CharFilter(method="filter_username", label="User", lookup_expr="iexact")
    before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lt")
    after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gt")

    board_list_type = "own"

    class Meta:
        model = Board
        form = BoardFilterForm
        fields = [
            "q",
            "created_at",
            "owner",
        ]

    def __init__(self, *args, **kwargs):
        self.board_list_type = kwargs.pop("board_list_type", "own")
        super().__init__(*args, **kwargs)
        if self.board_list_type == "own":
            self.filters.pop("owner")

    @property
    def form(self):
        if not hasattr(self, "_form"):
            form = self.get_form_class()
            if self.is_bound:
                self._form = form(self.data, prefix=self.form_prefix, board_list_type=self.board_list_type)
            else:
                self._form = form(prefix=self.form_prefix, board_list_type=self.board_list_type)
        return self._form

    @property
    def qs(self):
        qs = super().qs.prefetch_related("owner").distinct()

        if self.board_list_type == "mod":
            qs = qs.filter(preferences__moderators__in=[self.request.user])
        elif self.board_list_type == "own":
            qs = qs.filter(owner=self.request.user)

        return qs.order_by("-created_at", "id")

    def filter_title_description(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))

    def filter_username(self, queryset, name, value):
        # https://stackoverflow.com/a/14908214
        value = value.split(",")
        value = (Q(owner__username__iexact=n) for n in value)
        value = reduce(lambda a, b: a | b, value)
        return queryset.filter(value)
