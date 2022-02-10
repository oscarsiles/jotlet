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
                    htmx.ajax('GET', pathName + Urls['boards:htmx-board-fetch'](board_slug), '#main-content-div');
                    // let newTopic = htmx.find('#newTopic-div');
                    // newTopic.setAttribute('hx-get', pathName + Urls['boards:htmx-topic-fetch'](data.topic_pk));
                    // htmx.process(newTopic);
                    // htmx.trigger(newTopic, 'topicCreated')
                }
                break;
            case "topic_updated":
                let divTopic = '#topic-' + data.topic_pk + '-subject';
                if (session_key != data.session_key) {
                    htmx.find(divTopic).textContent = data.topic_subject;
                }

                mathjaxTypeset(divTopic);
                break;
            case "topic_deleted":
                htmx.find('#topic-' + data.topic_pk).remove();
                break;
            case "post_created":
                if (session_key != data.session_key) {
                    let topicDiv = htmx.find('#topic-' + data.topic_pk);
                    htmx.ajax('GET', pathName + Urls['boards:htmx-topic-fetch'](data.topic_pk), topicDiv);
                    // Need to wait for HTMX to be fixed to do a single-post load
                    // let newCard = htmx.find('#topic-' + data.topic_pk).lastElementChild;
                    // newCard.setAttribute('hx-get', pathName + Urls['boards:htmx-post-fetch'](data.post_pk));
                    // htmx.process(newCard);
                    // htmx.trigger(newCard, 'postCreated');
                    // newCard.removeAttribute('hx-get');
                }
                break;
            case "post_updated":
                let divPost = '#post-' + data.post_pk + '-text';
                if (session_key != data.session_key) {
                    htmx.find(divPost).textContent = data.post_content;
                }
                
                mathjaxTypeset(divPost);
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

htmx.onLoad(function(elt){
    mathjaxTypeset(elt);
});

function mathjaxTypeset(elt) {
    if (window.MathJax != null) {
        window.MathJax.typesetPromise([elt]).catch((err) => console.log(err.message));
    }
}

