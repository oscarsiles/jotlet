var is_logged_in = JSON.parse(
  document.getElementById("is_logged_in").textContent
);

if (is_logged_in) {
  var is_all_boards = JSON.parse(
    document.getElementById("is_all_boards").textContent
  );

  // Board Filter
  function boardFilter() {
    return {
      filterChanged() {
        this.$el.dispatchEvent(
          new CustomEvent("filterChanged", { bubbles: true })
        );
      },
      keyup: {
        "@keyup"() {
          this.filterChanged();
        },
      },
      change: {
        "@change"() {
          this.filterChanged();
        },
      },
      tagify: {
        "@add"() {
          this.filterChanged();
        },
        "@change"() {
          this.filterChanged();
        },
        "@remove"() {
          this.filterChanged();
        },
      },
    };
  }

  // Tagify init
  if (is_all_boards) {
    var tagify = null;
    htmx.on("#board-list", "htmx:load", function (evt) {
      if (tagify == null && evt.detail.elt.id == "board-filter-form") {
        var ownerInput = document.querySelector("input[name=owner]");
        tagify = new Tagify(ownerInput, {
          delimiters: ",| ",
          originalInputValueFormat: (valuesArr) =>
            valuesArr.map((item) => item.value).join(","),
        });
        tagify = null;
      }
    });
  }
}
