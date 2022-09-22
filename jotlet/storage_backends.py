from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage, S3ManifestStaticStorage


class StaticStorage(S3ManifestStaticStorage):
    location = "static"


class PublicMediaStorage(S3Boto3Storage):
    location = settings.PUBLIC_MEDIA_LOCATION
