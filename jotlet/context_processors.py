from django.conf import settings  # import the settings file


def captcha_sitekeys(_request):
    # return the value you want as a dictionary. you may add multiple values in there.
    site_keys = {"HCAPTCHA_SITE_KEY": False, "CF_TURNSTILE_SITE_KEY": False}

    if settings.HCAPTCHA_ENABLED:
        site_keys["HCAPTCHA_SITE_KEY"] = settings.HCAPTCHA_SITE_KEY
    elif settings.CF_TURNSTILE_ENABLED:
        site_keys["CF_TURNSTILE_SITE_KEY"] = settings.CF_TURNSTILE_SITE_KEY

    return site_keys
