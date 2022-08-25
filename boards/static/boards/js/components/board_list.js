var is_logged_in = JSON.parse(
  document.getElementById("is_logged_in").textContent
);

if (is_logged_in) {
  var board_list_type = JSON.parse(
    document.getElementById("board_list_type").textContent
  );

  // Tagify init
  if (board_list_type != "own") {
    var tagify = null;
    htmx.on("#board-list", "htmx:load", function (evt) {
      if (tagify == null && evt.detail.elt.id == "board-filter-form") {
        var ownerInput = document.querySelector("input[name=owner]");
        tagify = new Tagify(ownerInput, {
          delimiters: ",| ",
          originalInputValueFormat: (valuesArr) =>
            valuesArr.map((item) => item.value).join(","),
          trim: false,
        });
        // tagify = null;
      }
    });
  }
}
