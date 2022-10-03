var allow_image_uploads = JSON.parse(
  document.getElementById("allow_image_uploads").textContent
);
var board_slug = JSON.parse(document.getElementById("board_slug").textContent);
var csrf_token = document.querySelector("[name=csrfmiddlewaretoken]").value;

var easyMDE = new EasyMDE({
  autoDownloadFontAwesome: false,
  autofocus: true,
  element: document.getElementsByName("content")[0],
  forceSync: true,
  imageAccept: allow_image_uploads
    ? ["image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp"]
    : [],
  imagePathAbsolute: true,
  imageCSRFToken: allow_image_uploads ? csrf_token : "",
  imageMaxSize: allow_image_uploads ? 1024 * 1024 * 2 : 0,
  imageTexts: { sbInit: "" },
  imageUploadEndpoint: allow_image_uploads
    ? `/boards/${board_slug}/image/post/upload/`
    : "",
  inputStyle: "textarea",
  maxHeight: "100%",
  nativeSpellChecker: false,
  previewImagesInEditor: allow_image_uploads,
  renderingConfig: {
    sanitizerFunction: (renderedHTML) => {
      return DOMPurify.sanitize(renderedHTML, {
        ALLOWED_ATTR: ["alt", "src", "title", "x-ignore"],
        ALLOWED_TAGS: allow_image_uploads
          ? ["span", "b", "i", "em", "strong", "br", "p", "code", "img"]
          : ["span", "b", "i", "em", "strong", "br", "p", "code"],
        SANITIZE_NAMED_PROPS: true,
      });
    },
  },
  spellChecker: false,
  status: allow_image_uploads ? ["upload-image"] : false,
  toolbar: allow_image_uploads
    ? [
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
        {
          name: "upload-image",
          action: EasyMDE.drawUploadedImage,
          className: "bi bi-image",
          title: "Upload Image",
        },
        "|",
        {
          name: "preview",
          action: EasyMDE.togglePreview,
          className: "bi bi-eye-fill no-disable",
          title: "Preview",
        },
      ]
    : [
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
      ],
  toolbarButtonClassPrefix: "mde",
  uploadImage: allow_image_uploads,
});

easyMDE.codemirror.on("beforeChange", (_, changes) => {
  if (easyMDE.value().length > 1000 && changes.origin !== "+delete") {
    changes.cancel();
  }
});
