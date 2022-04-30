import httpx
from django.conf import settings


def hcaptcha_verified(request):
    if settings.HCAPTCHA_ENABLED:
        if request.method == "POST":
            if request.POST.get("h-captcha-response"):
                # check hCaptcha
                h_captcha_response = request.POST.get("h-captcha-response")
                data = {"secret": settings.HCAPTCHA_SECRET_KEY, "response": h_captcha_response}
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
