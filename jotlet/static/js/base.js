// Toast Notification
function toastNotification() {
  return {
    message: "",
    bg_color: "",
    btn_color: "",
    openToast(event) {
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

// Morph HTMX Plugin
htmx.defineExtension('alpine-morph', {
  isInlineSwap: function (swapStyle) {
      return swapStyle === 'morph';
  },
  handleSwap: function (swapStyle, target, fragment) {
      if (swapStyle === 'morph') {
          if (fragment.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
              Alpine.morph(target, fragment.firstElementChild);
              return [target];
          } else {
              Alpine.morph(target, fragment.outerHTML);
              return [target];
          }
      }
  }
});