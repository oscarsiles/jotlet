document.getElementById("board-filter-form").removeAttribute("method");

var qInput = document.querySelector("input[name=q]");
qInput.addEventListener("keyup", (event) => {
  if (event.isComposing || event.keyCode === 229) {
    return;
  }
  htmx.trigger(htmx.find("#board-filter-form"), "filterChanged");
});

var beforeInput = document.querySelector("input[name=before]");
var afterInput = document.querySelector("input[name=after]");

beforeInput.addEventListener("change", (e) => {
  htmx.trigger(htmx.find("#board-filter-form"), "filterChanged");
});

afterInput.addEventListener("change", (e) => {
  htmx.trigger(htmx.find("#board-filter-form"), "filterChanged");
});

var ownerInput = document.querySelector("input[name=owner]");
tagify = new Tagify(ownerInput, {
  delimiters: ",| ",
  originalInputValueFormat: (valuesArr) =>
    valuesArr.map((item) => item.value).join(","),
});
tagify.on("add", (e) =>
  htmx.trigger(htmx.find("#board-filter-form"), "filterChanged")
);
tagify.on("change", (e) =>
  htmx.trigger(htmx.find("#board-filter-form"), "filterChanged")
);
tagify.on("remove", (e) =>
  htmx.trigger(htmx.find("#board-filter-form"), "filterChanged")
);
