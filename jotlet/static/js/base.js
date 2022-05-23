// Toast Notification
function toastNotification() {
  return {
    message: "",
    bg_color: "",
    btn_color: "btn-close-white",
    openToast(event) {
      this.open = true;
      this.message = event.detail.message;

      this.bg_color = "text-bg-success";
      this.btn_color = "btn-close-white";
      if (event.detail.color == "warning") {
        this.bg_color = "text-bg-warning";
        this.btn_color = "btn-close-black";
      } else if (event.detail.color == "info") {
        this.bg_color = "text-bg-info";
        this.btn_color = "btn-close-black";
      } else if (event.detail.color == "light") {
        this.bg_color = "text-bg-light";
        this.btn_color = "btn-close-black";
      } else if (event.detail.color != null) {
        this.bg_color = "text-bg-" + event.detail.color;
      }
    },
  };
}

function hcaptchaReady() {
  hcaptcha.render("hcaptcha-div", {});
}
