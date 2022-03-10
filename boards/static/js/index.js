document.addEventListener(
  "DOMContentLoaded",
  function () {
    var input = document.querySelector("input[name=u]");
    tagify = new Tagify(input, {
      delimiters: " ",
      originalInputValueFormat: (valuesArr) =>
        valuesArr.map((item) => item.value).join(","),
    });
    tagify.on("add", (e) =>
      htmx.trigger(htmx.find("#input-user-search"), "userAdded")
    );
    tagify.on("change", (e) =>
      htmx.trigger(htmx.find("#input-user-search"), "userChanged")
    );
    tagify.on("remove", (e) =>
      htmx.trigger(htmx.find("#input-user-search"), "userRemoved")
    );
  },
  false
);
