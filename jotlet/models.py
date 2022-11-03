import auto_prefetch

from .mixins.refresh_from_db_invalidates_cached_properties import InvalidateCachedPropertiesMixin


class InvalidatingAutoPrefetchModel(InvalidateCachedPropertiesMixin, auto_prefetch.Model):
    class Meta:
        abstract = True
