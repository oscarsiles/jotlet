MathJax = {
  tex: {
    inlineMath: [
      ["$", "$"],
      ["\\(", "\\)"],
    ],
  },
  svg: {
    fontCache: "global",
  },
  startup: {
    pageReady() {
      MathJax.startup.defaultPageReady();
      MathJax.startup.promise.then(() => {
        htmx.onLoad(function (elt) {
          var mathjax_enabled = JSON.parse(
            document.getElementById("mathjax_enabled").textContent
          );
          try {
            if (window.MathJax != null && mathjax_enabled) {
              window.MathJax.typesetPromise([elt]);
            }
          } catch (err) {}
        });
      });
    },
  },
};
