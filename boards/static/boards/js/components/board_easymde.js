var allowImageUploads = JSON.parse(
  document.getElementById("allow_image_uploads").textContent
);
var enableChemdoodle = JSON.parse(
  document.getElementById("chemdoodle_enabled").textContent
);
var boardSlug = JSON.parse(document.getElementById("board_slug").textContent);
var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

// setup tags/toolbar
var allowedTags = ["span", "b", "i", "em", "strong", "br", "p", "code"];
if (allowImageUploads) {
  allowedTags.push("img");
}
if (enableChemdoodle) {
  allowedTags.push("canvas");
}
var toolbarItems = [
  {
    name: "bold",
    action: EasyMDE.toggleBold,
    className: "bi bi-type-bold",
    title: "Bold",
  },
  {
    name: "italic",
    action: EasyMDE.toggleItalic,
    className: "bi bi-type-italic",
    title: "Italic",
  },
  "|",
  {
    name: "preview",
    action: EasyMDE.togglePreview,
    className: "bi bi-eye-fill no-disable",
    title: "Preview",
  },
];
if (allowImageUploads) {
  toolbarItems.splice(2, 0, {
    name: "upload-image",
    action: EasyMDE.drawUploadedImage,
    className: "bi bi-image",
    title: "Upload Image",
  });
}
if (enableChemdoodle) {
  canvasWidth =
    bootstrap.Modal.getInstance("#modal-1-div")._dialog.clientWidth * 0.9;
  canvasHeight = canvasWidth * 0.6;
  toolbarItems.splice(2, 0, {
    name: "chemdoodle",
    action: (editor) => {
      document.querySelector(".modal-dialog").classList.add("modal-lg");
      var editorCanvas = new ChemDoodle.SketcherCanvas(
        "chemdoodle-edit-canvas",
        canvasWidth,
        canvasHeight,
        { requireStartingAtom: false }
      );
      editorCanvas.repaint();
    },
    className: "bi bi-chemdoodle",
    title: "Chemdoodle",
  });
}

var easyMDE = new EasyMDE({
  autoDownloadFontAwesome: false,
  autofocus: true,
  element: document.getElementsByName("content")[0],
  forceSync: true,
  imageAccept: allowImageUploads
    ? ["image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp"]
    : [],
  imagePathAbsolute: true,
  imageCSRFToken: allowImageUploads ? csrfToken : "",
  imageMaxSize: allowImageUploads ? 1024 * 1024 * 2 : 0,
  imageTexts: { sbInit: "" },
  imageUploadEndpoint: allowImageUploads
    ? `/boards/${boardSlug}/image/post/upload/`
    : "",
  maxHeight: "100%",
  nativeSpellChecker: true,
  previewImagesInEditor: allowImageUploads,
  renderingConfig: {
    sanitizerFunction: (renderedHTML) => {
      return DOMPurify.sanitize(renderedHTML, {
        ALLOWED_ATTR: ["alt", "src", "title", "x-ignore"],
        ALLOWED_TAGS: allowedTags,
        SANITIZE_NAMED_PROPS: true,
      });
    },
  },
  spellChecker: false,
  status: allowImageUploads ? ["upload-image"] : false,
  toolbar: toolbarItems,
  toolbarButtonClassPrefix: "mde",
  uploadImage: allowImageUploads,
});

easyMDE.codemirror.on("beforeChange", (_, changes) => {
  if (easyMDE.value().length > 1000 && changes.origin !== "+delete") {
    changes.cancel();
  }
});
