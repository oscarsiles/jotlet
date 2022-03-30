var modal = bootstrap.Modal.getInstance(document.getElementById("modal-1-div"));

var toggleBackgroundOptions = function (bg_type) {
  switch (bg_type) {
    case "i":
      htmx.find("#div_id_background_image").style.display = "block";
      htmx.find("#div_id_background_opacity").style.display = "block";
      htmx.find("#div_id_background_color").style.display = "none";
      break;
    case "c":
      htmx.find("#div_id_background_color").style.display = "block";
      htmx.find("#div_id_background_image").style.display = "none";
      htmx.find("#div_id_background_opacity").style.display = "none";
      break;
  }
};

modal._config.backdrop = "static";
$("#div_id_background_type").removeClass("mb-3");

var background_type = $(
  '#id_background_type input[type="radio"]:checked'
).val();
toggleBackgroundOptions(background_type);

htmx.on("show.bs.modal", function (evt) {
  modal._config.backdrop = "static";
});

htmx.on("hide.bs.modal", function (evt) {
  modal._config.backdrop = true;
});

var el = document.getElementById("id_background_type");
el.addEventListener("change", function (evt) {
  toggleBackgroundOptions(evt.target.value);
});

var moderatorsInput = document.querySelector("input[name=moderators]");
tagify = new Tagify(moderatorsInput, {
  delimiters: ",| ",
  originalInputValueFormat: (valuesArr) =>
    valuesArr.map((item) => item.value).join(","),
});
