var ratyClass = "raty-div";

function setup_raty(div) {
  var post_pk = div.querySelector("#post_pk").textContent;
  var starsDiv = `#stars-${post_pk}-div`;
  var starsSubmitDiv = `#stars-${post_pk}-submit`;
  var footerDiv = `post-${post_pk}-footer`;

  var has_reacted = JSON.parse(
    document.getElementById(footerDiv).querySelector("#has_reacted").textContent
  );
  if (has_reacted) {
    var reacted_score = JSON.parse(
      document.getElementById(footerDiv).querySelector("#reacted_score")
        .textContent
    );
  }

  $(div).raty({
    starOn: "/static/images/star-on.svg",
    starOff: "/static/images/star-off.svg",
    hints: [1, 2, 3, 4, 5],
    click: function (score, evt) {
      setTimeout(function () {
        $(starsSubmitDiv).click();
      }, 0);
    },
  });

  if (has_reacted) {
    $(div).data("raty").score(reacted_score);
  }
}

var els = document.getElementsByClassName("raty-div");
for (var i = 0; i < els.length; i++) {
  setup_raty(els[i]);
}

htmx.onLoad(function (elt) {
  if (
    elt.classList.contains("post-card-footer") ||
    elt.classList.contains("post-card")
  ) {
    setup_raty(elt.querySelector("." + ratyClass));
  }
});
