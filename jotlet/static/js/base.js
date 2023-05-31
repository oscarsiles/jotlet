// Tooltips
function initializeTooltips(el) {
  var tooltipTriggerList = el.querySelectorAll('[data-bs-toggle="tooltip"]');
  [...tooltipTriggerList].map(
    (tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl)
  );
}

// Toast Notification
function toastNotification() {
  return {
    message: "",
    bg_color: "",
    btn_theme: "",
    openToast(event) {
      this.message = event.detail.message;

      this.bg_color = "text-bg-success";
      this.btn_theme = "dark";
      if (event.detail.color == "warning") {
        this.bg_color = "text-bg-warning";
        this.btn_theme = "light";
      } else if (event.detail.color == "info") {
        this.bg_color = "text-bg-info";
        this.btn_theme = "light";
      } else if (event.detail.color == "light") {
        this.bg_color = "text-bg-light";
        this.btn_theme = "light";
      } else if (event.detail.color != null) {
        this.bg_color = "text-bg-" + event.detail.color;
      }
    },
  };
}

function hcaptchaReady() {
  if (typeof hcaptcha != "undefined") {
    hcaptcha.render("hcaptcha-div", {});
  }
}

function turnstileReady() {
  if (typeof turnstile != "undefined") {
    if (document.getElementsByTagName("iframe").length > 0) {
      turnstile.remove("#cf-turnstile-div");
    }
    turnstile.render("#cf-turnstile-div", {});
  }
}
