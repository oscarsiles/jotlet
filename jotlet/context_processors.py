from django.conf import settings  # import the settings file


def captcha_sitekeys(request):
    # return the value you want as a dictionary. you may add multiple values in there.
    if settings.HCAPTCHA_ENABLED:
        return {
            "HCAPTCHA_SITE_KEY": settings.HCAPTCHA_SITE_KEY,
            "CF_TURNSTILE_SITE_KEY": False,
        }
    elif settings.CF_TURNSTILE_ENABLED:
        return {
            "HCAPTCHA_SITE_KEY": False,
            "CF_TURNSTILE_SITE_KEY": settings.CF_TURNSTILE_SITE_KEY,
        }
    else:
        return {"HCAPTCHA_SITE_KEY": False, "CF_TURNSTILE_SITE_KEY": False}
