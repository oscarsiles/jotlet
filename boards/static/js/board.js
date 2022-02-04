console.log("Sanity check from board.js.");

const board_slug = JSON.parse(document.getElementById('board_slug').textContent);
const session_key = JSON.parse(document.getElementById('session_key').textContent);
const can_delete_post = JSON.parse(document.getElementById('can_delete_post').textContent);

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
                var t = document.querySelector('#cardTemplate')
                t.content.querySelector('#post-pk').id = 'post-' + data.post_pk;
                t.content.querySelector('#post-pk-text').innerHTML = data.post_content;
                t.content.querySelector('#post-pk-text').id = 'post-' + data.post_pk + '-text';
                t.content.querySelector('#post-pk-update-url').href = Urls['boards:post_update'](board_slug, data.topic_pk, data.post_pk);
                t.content.querySelector('#post-pk-delete-url').href = Urls['boards:post_delete'](board_slug, data.topic_pk, data.post_pk);
                var clone = document.importNode(t.content, true)
                document.getElementById('topic-' + data.topic_pk).appendChild(clone);
                break;
            case "post_updated":
                $('#post-' + data.post_pk + "-text").html(data.post_content);
                break;
            case "post_deleted":
                document.getElementById('post-' + data.post_pk).remove();
                break;
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
