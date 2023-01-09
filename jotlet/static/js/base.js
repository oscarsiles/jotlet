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
  hcaptcha.render("hcaptcha-div", {});
}
