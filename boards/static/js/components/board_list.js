document.getElementById("board-filter-form").removeAttribute("method");

var is_all_boards = JSON.parse(
  document.getElementById("is_all_boards").textContent
);

if (is_all_boards) {
  var ownerInput = document.querySelector("input[name=owner]");
  tagify = new Tagify(ownerInput, {
    delimiters: ",| ",
    originalInputValueFormat: (valuesArr) =>
      valuesArr.map((item) => item.value).join(","),
  });
}
