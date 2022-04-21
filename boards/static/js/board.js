board_slug = JSON.parse(document.getElementById("board_slug").textContent);

baseUrl =
  window.location.pathname.split("/")[1] == "boards"
    ? window.location.host
    : window.location.host + "/" + window.location.pathname.split("/")[1];
pathName =
  window.location.pathname.split("/")[1] == "boards"
    ? ""
    : "/" + window.location.pathname.split("/")[1];

if (typeof boardSocket === "undefined") {
  function connect() {
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
          htmx.find("#topic-" + data.topic_pk).remove();
          break;
        case "post_created":
          var topicDiv = "#topic-" + data.topic_pk;
          htmx.trigger(htmx.find(topicDiv), "postCreated");
          break;
        case "post_updated":
          var postDiv = "#post-" + data.post_pk;
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
  connect();
}

// Board Preferences Alpine Data
function boardPreferences() {
  return {
    bg_type: "",
    get colorVisible() {
      return this.bg_type == "c" ? true : false;
    },
    get imageVisible() {
      return this.bg_type == "i" ? true : false;
    },
  };
}
