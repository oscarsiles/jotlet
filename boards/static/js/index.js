var toastElement = document.getElementById("toast");
var toastBody = document.getElementById("toast-body");
var toastClose = document.getElementById("toast-close");

var toast = bootstrap.Toast.getOrCreateInstance(toastElement, {
  delay: 3000,
});

htmx.on("showMessage", (e) => {
  toastBody.innerText = e.detail.message;
  var baseToastClass = "toast align-items-center border-0 ";
  var baseToastCloseClass = "me-2 m-auto btn-close ";

  if (e.detail.color == null) {
    toastElement.className = baseToastClass + "text-white bg-success";
    toastClose.className = baseToastCloseClass + "btn-close-white";
  } else if (e.detail.color == "warning") {
    toastElement.className = baseToastClass + "text-black bg-warning";
  } else if (e.detail.color == "info") {
    toastElement.className = baseToastClass + "text-black bg-info";
  } else if (e.detail.color == "light") {
    toastElement.className = baseToastClass + "text-black bg-light";
  } else {
    toastElement.className = baseToastClass + "text-white bg-" + e.detail.color;
    toastClose.className = baseToastCloseClass + "btn-close-white";
  }
  toast.show();
});
