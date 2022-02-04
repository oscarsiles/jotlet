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
            case "topic_created":
                var clone = document.importNode(document.querySelector('#topicTemplate').content, true)
                clone.querySelector('#topic-pk').id = 'topic-' + data.topic_pk;
                clone.querySelector('#topic-pk-subject').innerHTML = data.topic_subject;
                clone.querySelector('#topic-pk-subject').id = 'topic-' + data.topic_pk + '-subject';
                try {
                    clone.querySelector('#topic-pk-update-url').href = Urls['boards:topic_update'](board_slug, data.topic_pk);
                    clone.querySelector('#topic-pk-update-url').id = 'topic-' + data.topic_pk + '-update-url';
                    clone.querySelector('#topic-pk-delete-url').href = Urls['boards:topic_delete'](board_slug, data.topic_pk);
                    clone.querySelector('#topic-pk-delete-url').id = 'topic-' + data.topic_pk + '-delete-url';
                } catch (e) { // not owner or staff
                }
                $(clone).insertBefore('#topic-create');
                break;
            case "topic_updated":
                $('#topic-' + data.topic_pk + "-subject").html(data.topic_subject);
                break;
            case "topic_deleted":
                document.getElementById('topic-' + data.topic_pk).remove();
                break;
            case "post_created":
                var clone = document.importNode(document.querySelector('#cardTemplate').content, true)
                clone.querySelector('#post-pk').id = 'post-' + data.post_pk;
                clone.querySelector('#post-pk-text').innerHTML = data.post_content;
                clone.querySelector('#post-pk-text').id = 'post-' + data.post_pk + '-text';
                try {
                    clone.querySelector('#post-pk-update-url').href = Urls['boards:post_update'](board_slug, data.topic_pk, data.post_pk);
                    clone.querySelector('#post-pk-update-url').id = 'post-' + data.post_pk + '-update-url';
                    clone.querySelector('#post-pk-delete-url').href = Urls['boards:post_delete'](board_slug, data.topic_pk, data.post_pk);
                    clone.querySelector('#post-pk-delete-url').id = 'post-' + data.post_pk + '-delete-url';
                } catch (e) { // not owner or staff
                }
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
