from storages.backends.s3boto3 import S3Boto3Storage, S3ManifestStaticStorage


class StaticStorage(S3ManifestStaticStorage):
    location = "static"
    default_acl = "public-read"


class PublicMediaStorage(S3Boto3Storage):
    location = "media"
    default_acl = "public-read"
