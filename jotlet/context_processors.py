from django.conf import settings  # import the settings file


def hcaptcha_sitekey(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {"HCAPTCHA_SITE_KEY": settings.HCAPTCHA_SITE_KEY if settings.HCAPTCHA_ENABLED else None}
