var easyMDE = new EasyMDE({
  autoDownloadFontAwesome: true,
  element: document.getElementsByName("content")[0],
  forceSync: true,
  iconClassMap: {
    bold: "bi bi-type-bold",
    italic: "bi bi-type-italic",
    preview: "bi bi-eye-fill",
  },
  maxHeight: "100%",
  renderingConfig: {
    sanitizerFunction: (renderedHTML) => {
      return DOMPurify.sanitize(renderedHTML, {
        ALLOWED_TAGS: ["b", "i", "em", "strong", "br", "p", "code"],
      });
    },
  },
  spellChecker: false,
  status: false,
  toolbar: ["bold", "italic", "|", "preview"],
});

easyMDE.codemirror.on("beforeChange", (_, changes) => {
  if (easyMDE.value().length > 1000 && changes.origin !== "+delete") {
    changes.cancel();
  }
});
