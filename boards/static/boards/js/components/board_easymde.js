var csrf_token = document.querySelector("[name=csrfmiddlewaretoken]").value;
var board_slug = JSON.parse(document.getElementById("board_slug").textContent);
var allow_image_uploads = JSON.parse(
  document.getElementById("allow_image_uploads").textContent
);

var easyMDE = new EasyMDE({
  autoDownloadFontAwesome: true,
  element: document.getElementsByName("content")[0],
  forceSync: true,
  iconClassMap: {
    bold: "bi bi-type-bold",
    italic: "bi bi-type-italic",
    "upload-image": "bi bi-image",
    preview: "bi bi-eye-fill",
  },
  imageAccept: ["image/png", "image/jpeg", "image/webp", "image/bmp"],
  imagePathAbsolute: true,
  imageCSRFToken: csrf_token,
  imageMaxSize: allow_image_uploads ? 1024 * 1024 * 2 : 0,
  imageTexts: { sbInit: "" },
  imageUploadEndpoint: `/boards/${board_slug}/image/post/upload/`,
  inputStyle: "textarea",
  maxHeight: "100%",
  nativeSpellChecker: false,
  previewImagesInEditor: true,
  renderingConfig: {
    sanitizerFunction: (renderedHTML) => {
      return DOMPurify.sanitize(renderedHTML, {
        ALLOWED_TAGS: ["b", "i", "em", "strong", "br", "p", "code", "img"],
      });
    },
  },
  spellChecker: false,
  status: allow_image_uploads ? ["upload-image"] : false,
  toolbar: allow_image_uploads
    ? ["bold", "italic", "upload-image", "|", "preview"]
    : ["bold", "italic", "|", "preview"],
  uploadImage: allow_image_uploads,
});

easyMDE.codemirror.on("beforeChange", (_, changes) => {
  if (easyMDE.value().length > 1000 && changes.origin !== "+delete") {
    changes.cancel();
  }
});
