// Toast Notification
function toastNotification() {
  return {
    open: false,
    message: "",
    bg_color: "text-white bg-success",
    btn_color: "btn-close-white",
    openToast(event) {
      this.open = true;
      this.message = event.detail.message;

      this.bg_color = "text-white bg-success";
      this.btn_color = "btn-close-white";
      if (event.detail.color == "warning") {
        this.bg_color = "text-black bg-warning";
        this.btn_color = "btn-close-black";
      } else if (event.detail.color == "info") {
        this.bg_color = "text-black bg-info";
        this.btn_color = "btn-close-black";
      } else if (event.detail.color == "light") {
        this.bg_color = "text-black bg-light";
        this.btn_color = "btn-close-black";
      } else if (event.detail.color != null) {
        this.bg_color = "text-white bg-" + event.detail.color;
      }
      setTimeout(() => {
        this.open = false;
      }, 3000);
    },
  };
}

function hcaptchaReady() {
  hcaptcha.render("hcaptcha-div", {});
}
