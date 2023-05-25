var allowImageUploads = JSON.parse(
  document.getElementById("allow_image_uploads").textContent
);
var enableChemdoodle = JSON.parse(
  document.getElementById("chemdoodle_enabled").textContent
);
var boardSlug = JSON.parse(document.getElementById("board_slug").textContent);
var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

// ChemDoodle setup
var chemdoodleEditCanvas = null;
var chemdoodleJson = null;
var canvasWidth = null;
var canvasHeight = null;

function chemdoodleToJSONField(evt, chemdoodleEnabled) {
  var json = null;
  if (chemdoodleEnabled) {
    json = JSON.stringify(
      new ChemDoodle.io.JSONInterpreter().contentTo(
        chemdoodleEditCanvas.molecules,
        chemdoodleEditCanvas.shapes
      )
    );
  }
  evt.detail.requestConfig.parameters.additional_data = json;
  return evt;
}

if (enableChemdoodle) {
  var json = document.getElementById("id_additional_data").value;
  if (json != "null") {
    chemdoodleJson = JSON.parse(json);
    toggleChemdoodleEditor();
  }
}

function toggleChemdoodleEditor() {
  var isChemdoodleCanvasEnabled =
    Alpine.store("postForm").chemdoodleCanvasEnabled;

  if (!isChemdoodleCanvasEnabled) {
    document.querySelector(".modal-dialog").classList.add("modal-lg");
    canvasWidth =
      bootstrap.Modal.getInstance("#modal-1-div")._dialog.clientWidth * 0.9;
    canvasHeight = canvasWidth * 0.6;
    if (!chemdoodleEditCanvas) {
      chemdoodleEditCanvas = new ChemDoodle.SketcherCanvas(
        "chemdoodle-edit-canvas",
        canvasWidth,
        canvasHeight,
        { requireStartingAtom: false }
      );
      if (chemdoodleJson) {
        var data = new ChemDoodle.io.JSONInterpreter().contentFrom(
          chemdoodleJson
        );
        chemdoodleEditCanvas.loadContent(data["molecules"], data["shapes"]);
      }
      chemdoodleEditCanvas.repaint();

      document
        .getElementById("chemdoodle-edit-canvas")
        .setAttribute("x-ref", "chemdoodleEditCanvas");
    } else {
    }
  } else {
    document.querySelector(".modal-dialog").classList.remove("modal-lg");
  }

  Alpine.store("postForm").chemdoodleCanvasEnabled = !isChemdoodleCanvasEnabled;
}

// setup tags/toolbar
var allowedTags = ["span", "b", "i", "em", "strong", "br", "p", "code"];
if (allowImageUploads) {
  allowedTags.push("img");
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
  toolbarItems.splice(2, 0, {
    name: "chemdoodle",
    action: (editor) => {
      return toggleChemdoodleEditor();
    },
    className: "bi bi-chemdoodle",
    title: "Chemdoodle",
  });
}

var easyMDE = new EasyMDE({
  autoDownloadFontAwesome: false,
  autofocus: true,
  autoRefresh: { delay: 300 },
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
