var modal1 = bootstrap.Modal.getInstance(
  document.getElementById("modal-1-div")
);
var modal2 = bootstrap.Modal.getInstance(
  document.getElementById("modal-2-div")
);

function escape_pressed(event) {
  if (event.key === "Escape") {
    modal2.hide();
    modal1.show();
    document.removeEventListener("keydown", escape_pressed);
  }
}
document.addEventListener("keydown", escape_pressed);
