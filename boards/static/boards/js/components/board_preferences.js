var modal = bootstrap.Modal.getInstance(document.getElementById("modal-1-div"));

modal._config.backdrop = "static";
htmx.on("show.bs.modal", function (evt) {
  modal._config.backdrop = "static";
});

htmx.on("hide.bs.modal", function (evt) {
  modal._config.backdrop = true;
});

// Tagify init
var moderatorsInput = document.querySelector("input[name=moderators]");
tagify = new Tagify(moderatorsInput, {
  delimiters: ",| ",
  originalInputValueFormat: (valuesArr) =>
    valuesArr.map((item) => item.value).join(","),
});
