console.log("Sanity check from board.js.");

var board_slug = JSON.parse(document.getElementById("board_slug").textContent);

var baseUrl =
  window.location.pathname.split("/")[1] == "boards"
    ? window.location.host
    : window.location.host + "/" + window.location.pathname.split("/")[1];
var pathName =
  window.location.pathname.split("/")[1] == "boards"
    ? ""
    : "/" + window.location.pathname.split("/")[1];

let boardSocket = null;

function connect() {
  var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
  boardSocket = new RobustWebSocket(
    ws_scheme + "://" + baseUrl + "/ws/boards/" + board_slug + "/"
  );

  boardSocket.onopen = function (e) {
    console.log("Successfully connected to the WebSocket.");
  };

  boardSocket.onclose = function (e) {
    console.log(
      "WebSocket connection closed unexpectedly. Trying to reconnect in 2s..."
    );
    setTimeout(function () {
      console.log("Reconnecting...");
      connect();
    }, 2000);
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

        mathjaxTypeset(topicDiv);
        break;
      case "topic_deleted":
        htmx.find("#topic-" + data.topic_pk).remove();
        break;
      case "post_created":
        var topicDiv = "#topic-" + data.topic_pk;
        htmx.trigger(htmx.find(topicDiv), "postCreated");
        break;
      case "post_approved":
      case "post_unapproved":
      case "post_updated":
        var postDiv = "#post-" + data.post_pk;
        htmx.trigger(htmx.find(postDiv), "postUpdated");

        mathjaxTypeset(postDiv);
        break;
      case "post_deleted":
        htmx.find("#post-" + data.post_pk).remove();
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

htmx.onLoad(function (elt) {
  mathjaxTypeset(elt);
});

function mathjaxTypeset(elt) {
  try {
    if (window.MathJax != null) {
      window.MathJax.typesetPromise([elt]).catch((err) =>
        console.log(err.message)
      );
    }
  } catch (err) {}
}
