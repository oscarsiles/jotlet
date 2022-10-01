import httpx
from django.conf import settings


def get_client_ip(request):
    cf_connecting_ip = request.META.get("HTTP_CF_CONNECTING_IP")  # for cloudflare proxy
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if cf_connecting_ip:
        ip = cf_connecting_ip
    elif x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def cf_turnstile_verified(request):
    if settings.CF_TURNSTILE_ENABLED:
        if request.method == "POST":
            if request.POST.get("cf-turnstile-response"):
                # check Turnstile
                cf_turnstile_response = request.POST.get("cf-turnstile-response")
                ip = get_client_ip(request)
                data = {
                    "secret": settings.CF_TURNSTILE_SECRET_KEY,
                    "response": cf_turnstile_response,
                    "remoteip": ip,
                }
                r = httpx.post(settings.CF_TURNSTILE_VERIFY_URL, data=data)
                result = r.json()
                if result["success"]:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    else:
        return True


def hcaptcha_verified(request):
    if settings.HCAPTCHA_ENABLED:
        if request.method == "POST":
            if request.POST.get("h-captcha-response"):
                # check hCaptcha
                h_captcha_response = request.POST.get("h-captcha-response")
                data = {
                    "secret": settings.HCAPTCHA_SECRET_KEY,
                    "response": h_captcha_response,
                }
                r = httpx.post(settings.HCAPTCHA_VERIFY_URL, data=data)
                result = r.json()
                if result["success"]:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    else:
        return True
