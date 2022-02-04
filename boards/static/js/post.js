const session_key = JSON.parse(document.getElementById('session_key').textContent);
const topic_pk = JSON.parse(document.getElementById('topic_pk').textContent);

$('#post-form').on('submit', function(e){
    console.log("Sending form...");
});
