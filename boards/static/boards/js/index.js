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
