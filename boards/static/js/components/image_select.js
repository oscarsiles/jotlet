selectedValue = $("#id_background_image").attr("value");
if (selectedValue != "") {
  $("#" + selectedValue).prop("checked", true);
}

$("#image-select .form-check-input").click(function () {
  var label = $("label[for='" + $(this).attr("id") + "']");
  $("#button-id_background_image").hide();
  $("#id_background_image").attr("value", $(this).attr("id"));
  $("#src-webp").attr("srcset", label.find("source").first().attr("srcset"));
  $("#src-jpeg").attr("srcset", label.find("source").last().attr("srcset"));
  $("#img-id_background_image").show();
});

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
