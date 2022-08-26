// Tagify init
var moderatorsInput = document.querySelector("input[name=moderators]");
tagify = new Tagify(moderatorsInput, {
  delimiters: ",| ",
  originalInputValueFormat: (valuesArr) =>
    valuesArr.map((item) => item.value).join(","),
  trim: false,
});
