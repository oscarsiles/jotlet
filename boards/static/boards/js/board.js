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

    switch (data.type) {
      case "session_connected":
      case "session_disconnected":
        htmx.find("#board-online-sessions").textContent = data.sessions;
        break;
      case "board_preferences_changed":
      case "topic_created":
        var boardDiv = "#board-" + board_slug;
        htmx.trigger(htmx.find(boardDiv), "topicCreated");
        break;
      case "topic_updated":
        var topicDiv = "#topic-" + data.topic_pk;
        htmx.trigger(htmx.find(topicDiv), "topicUpdated");
        break;
      case "topic_deleted":
        var boardDiv = "#board-" + board_slug;
        htmx.find("#topic-" + data.topic_pk).remove();
        htmx.trigger(htmx.find(boardDiv), "topicDeleted");
        break;
      case "post_created":
        var newCardDiv =
          data.reply_to == null
            ? "#newCard-" + data.topic_pk + "-div"
            : "#newCard-post-" + data.reply_to + "-div";
        console.log(newCardDiv);
        htmx.ajax("GET", data.fetch_url, {
          target: newCardDiv,
          swap: "beforebegin",
        });
        break;
      case "post_updated":
        var postDiv = "#container-post-" + data.post_pk;
        htmx.trigger(htmx.find(postDiv), "postUpdated");
        break;
      case "post_deleted":
        htmx.find("#post-" + data.post_pk).remove();
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
  Alpine.store("boardPreferences", {
    bg_type: "",
    bg_opacity: "",
    img_uuid: "",
    img_srcset_webp: "",
    img_srcset_jpeg: "",
    get colorVisible() {
      return this.bg_type == "c" ? true : false;
    },
    get imageVisible() {
      return this.bg_type == "i" ? true : false;
    },
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

document.addEventListener("alpine:initializing", () => {
  Alpine.directive("markdown", (el, {}, { effect, evaluateLater }) => {
    let getHTML = evaluateLater();

    effect(() => {
      getHTML(() => {
        el.innerHTML = DOMPurify.sanitize(marked.parseInline(el.innerHTML), {
          ALLOWED_TAGS: ["b", "i", "em", "strong", "br", "p", "code"],
        });
      });
    });
  });
});
