console.log("Sanity check from board.js.");

const board_slug = JSON.parse(document.getElementById('board_slug').textContent);

let boardSocket = null;

function connect() {
    boardSocket = new WebSocket("ws://" + window.location.host + "/ws/boards/" + board_slug + "/");

    boardSocket.onopen = function(e) {
        console.log("Successfully connected to the WebSocket.");
    }

    boardSocket.onclose = function(e) {
        console.log("WebSocket connection closed unexpectedly. Trying to reconnect in 2s...");
        setTimeout(function() {
            console.log("Reconnecting...");
            connect();
        }, 2000);
    };

    boardSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log(data);

        switch (data.type) {
            case "post_created":
                console.log(data.topic_pk);
                break;
            case "post_deleted":
                document.getElementById('post-' + data.post_pk).remove();
            default:
                console.error("Unknown message type!");
                break;
        }
    };

    boardSocket.onerror = function(err) {
        console.log("WebSocket encountered an error: " + err.message);
        console.log("Closing the socket.");
        boardSocket.close();
    }
}
connect();
