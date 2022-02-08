console.log("Sanity check from board.js.");

var board_slug = JSON.parse(document.getElementById('board_slug').textContent);
var session_key = JSON.parse(document.getElementById('session_key').textContent);

var baseUrl = window.location.pathname.split('/')[1] == 'boards' ? window.location.host : window.location.host + "/" + window.location.pathname.split('/')[1];
var pathName = window.location.pathname.split('/')[1] == 'boards' ? '' : '/' + window.location.pathname.split('/')[1];

let boardSocket = null;

function connect() {
    var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";    
    boardSocket = new WebSocket(ws_scheme + "://" + baseUrl + "/ws/boards/" + board_slug + "/");

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

        switch (data.type) {
            case "session_connected":
            case "session_disconnected":
                htmx.find('#board-online-sessions').textContent = data.sessions
                break;
            case "topic_created":
                if (session_key != data.session_key) {
                    let newTopic = htmx.find('#newTopic-div');
                    newTopic.setAttribute('hx-get', pathName + Urls['boards:htmx-topic-fetch'](data.topic_pk));
                    htmx.process(newTopic);
                    htmx.trigger(newTopic, 'topicCreated')
                }
                break;
            case "topic_updated":
                if (session_key != data.session_key) {
                    htmx.find('#topic-' + data.topic_pk + "-subject").textContent = data.topic_subject;
                }
                break;
            case "topic_deleted":
                htmx.find('#topic-' + data.topic_pk).remove();
                break;
            case "post_created":
                if (session_key != data.session_key) {
                    let newCard = htmx.find('#newCard-' + data.topic_pk + '-div');
                    newCard.setAttribute('hx-get', pathName + Urls['boards:htmx-post-fetch'](data.post_pk));
                    htmx.process(newCard);
                    htmx.trigger(newCard, 'postCreated');
                }
                break;
            case "post_updated":
                if (session_key != data.session_key) {
                    htmx.find('#post-' + data.post_pk + "-text").textContent = data.post_content;
                }
                break;
            case "post_deleted":
                htmx.find('#post-' + data.post_pk).remove();
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
