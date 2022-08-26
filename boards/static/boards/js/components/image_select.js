var modal2 = bootstrap.Modal.getInstance(
  document.getElementById("modal-2-div")
);

function escape_pressed(event) {
  if (event.key === "Escape") {
    modal2.hide();
    document.removeEventListener("keydown", escape_pressed);
  }
}
document.addEventListener("keydown", escape_pressed);
