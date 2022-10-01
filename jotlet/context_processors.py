from django.conf import settings  # import the settings file


def captcha_sitekeys(request):
    # return the value you want as a dictionary. you may add multiple values in there.
    return {
        "HCAPTCHA_SITE_KEY": settings.HCAPTCHA_SITE_KEY if settings.HCAPTCHA_ENABLED else False,
        "CF_TURNSTILE_SITE_KEY": settings.CF_TURNSTILE_SITE_KEY if settings.CF_TURNSTILE_SITE_KEY else False,
    }
