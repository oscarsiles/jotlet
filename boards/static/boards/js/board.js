var allow_image_uploads = JSON.parse(
  document.getElementById("allow_image_uploads").textContent
);
var enable_chemdoodle = JSON.parse(
  document.getElementById("chemdoodle_enabled").textContent
);
var board_slug = JSON.parse(document.getElementById("board_slug").textContent);
var boardSocket = null;
var baseUrl =
  window.location.pathname.split("/")[1] == "boards"
    ? window.location.host
    : window.location.host + "/" + window.location.pathname.split("/")[1];
var pathName =
  window.location.pathname.split("/")[1] == "boards"
    ? ""
    : "/" + window.location.pathname.split("/")[1];

function connectWebsocket() {
  var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
  boardSocket = new RobustWebSocket(
    ws_scheme + "://" + baseUrl + "/ws/boards/" + board_slug + "/",
    null,
    {
      timeout: 5000,
      shouldReconnect: function (event, ws) {
        console.log(
          "WebSocket connection closed unexpectedly. Trying to reconnect..."
        );
        if (event.code === 1008 || event.code === 1011) return;
        return [0, 3000, 10000][ws.attempts];
      },
    }
  );

  boardSocket.onopen = function (e) {
    console.log("Successfully connected to the WebSocket.");
  };

  boardSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    var boardDiv = "#board-" + board_slug;

    switch (data.type) {
      case "session_connected":
      case "session_disconnected":
        try {
          htmx.find("#board-online-sessions").textContent = data.sessions;
          break;
        } catch (e) {
          break;
        }
      case "board_preferences_changed":
      case "board_updated":
        htmx.trigger(htmx.find(boardDiv), "boardUpdated");
        break;
      case "topic_created":
        htmx.trigger(htmx.find(boardDiv), "topicCreated");
        break;
      case "topic_updated":
        var topicDiv = "#topic-" + data.topic_pk;
        htmx.trigger(htmx.find(topicDiv), "topicUpdated");
        break;
      case "topic_deleted":
        htmx.find("#topic-" + data.topic_pk).remove();
        break;
      case "post_created":
        var newCardDiv =
          data.parent == null
            ? "#newCard-topic-" + data.topic_pk + "-div"
            : "#newCard-post-" + data.parent + "-div";
        htmx.ajax("GET", data.fetch_url, {
          target: newCardDiv,
          swap: "beforebegin",
        });
        htmx.trigger(htmx.find(boardDiv), "postCreated");
        break;
      case "post_updated":
        var postDiv = "#container-post-" + data.post_pk;
        htmx.trigger(htmx.find(postDiv), "postUpdated");
        break;
      case "post_deleted":
        var topicDiv = "#topic-" + data.topic_pk;
        htmx.find("#container-post-" + data.post_pk).remove();
        htmx.trigger(htmx.find(topicDiv), "postDeleted");
        break;
      case "reaction_updated":
        var postFooterDiv = "#post-" + data.post_pk + "-footer-htmx-div";
        htmx.trigger(htmx.find(postFooterDiv), "reactionUpdated");
        break;
      default:
        console.error("Unknown message type: " + data);
        break;
    }
  };

  boardSocket.onerror = function (err) {
    console.log("WebSocket encountered an error: " + err.message);
    console.log("Closing the socket.");
    boardSocket.close();
  };
}

document.addEventListener("alpine:init", () => {
  function img_srcset_res(pathfilename, res) {
    var filepath = pathfilename.substr(0, pathfilename.lastIndexOf("."));
    var ext = pathfilename.split(".").pop();
    return `${filepath}@${res}x.${ext}`;
  }

  Alpine.store("board", {
    is_overflow: false,
    deleteConfirm: false,
  });

  Alpine.store("boardPreferences", {
    bg_type: "",
    bg_opacity: "",
    img_id: "",
    img_srcset_webp: "",
    img_srcset_jpeg: "",
    get colorVisible() {
      return this.bg_type == "c" ? true : false;
    },
    get imageVisible() {
      return this.bg_type == "i" ? true : false;
    },
    img_srcset_jpeg_res(res) {
      return img_srcset_res(this.img_srcset_jpeg, res);
    },
    img_srcset_webp_res(res) {
      return img_srcset_res(this.img_srcset_webp, res);
    },
  });

  Alpine.store("postForm", {
    chemdoodleCanvasEnabled: false,
  });
});

function starRating() {
  return {
    rating: 0,
    hoverRating: 0,
    isHover: false,
    ratings: [1, 2, 3, 4, 5],
    rate(score) {
      if (this.rating == score) {
        this.rating = 0;
      } else {
        this.rating = score;
      }
    },
    starClass(score) {
      if (this.hoverRating >= score && this.hoverRating != 0) {
        return "bi-star-fill";
      } else if (this.rating >= score && this.hoverRating == 0) {
        return "bi-star-fill";
      } else {
        return "bi-star";
      }
    },
  };
}

connectWebsocket();

// Alpine x-markdown
var allowed_tags = ["span", "b", "i", "em", "strong", "br", "p", "code"];
var allowed_attr = ["title", "x-ignore"];
if (allow_image_uploads) {
  allowed_tags.push("img");
  allowed_attr.push("alt", "src");
}

document.addEventListener("alpine:initializing", () => {
  Alpine.directive("markdown", (el) => {
    el.innerHTML = DOMPurify.sanitize(marked.parseInline(el.innerHTML), {
      ALLOWED_ATTR: allowed_attr,
      ALLOWED_TAGS: allowed_tags,
      SANITIZE_NAMED_PROPS: true,
    });
  });
});
