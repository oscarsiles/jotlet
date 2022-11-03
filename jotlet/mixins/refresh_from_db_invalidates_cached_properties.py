# License: LGPL V3.0
# https://www.gnu.org/licenses/lgpl-3.0.en.html
# https://gitlab.com/-/snippets/1747035

from django.utils.functional import cached_property


class InvalidateCachedPropertiesMixin:
    def refresh_from_db(self, *args, **kwargs):
        self.invalidate_cached_properties()
        return super().refresh_from_db(*args, **kwargs)

    def invalidate_cached_properties(self):
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, cached_property):
                self.__dict__.pop(key, None)
