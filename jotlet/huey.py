from django_redis import get_redis_connection
from huey import PriorityRedisExpireHuey


class DjangoPriorityRedisExpiryHuey(PriorityRedisExpireHuey):
    """
    Subclassed to use the existing connection pool from the Django
    cache backend, when using `django-redis`.
    """

    def __init__(self, *args, **kwargs):
        connection = get_redis_connection()
        kwargs["connection_pool"] = connection.connection_pool

        super().__init__(*args, **kwargs)
