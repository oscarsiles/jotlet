document.addEventListener("alpine:init", () => {
  Alpine.store("userPreferences", {
    deleteConfirm: false,
  });
});
