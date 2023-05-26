var enable_chemdoodle = JSON.parse(
  document.getElementById("chemdoodle_enabled").textContent
);

if (enable_chemdoodle) {
  ChemDoodle.DEFAULT_STYLES.bondLength_2D = 14.4;
  // ChemDoodle.DEFAULT_STYLES.bonds_width_2D = 0.6;
  ChemDoodle.DEFAULT_STYLES.bonds_saturationWidthAbs_2D = 2.6;
  ChemDoodle.DEFAULT_STYLES.bonds_hashSpacing_2D = 2.5;
  // ChemDoodle.DEFAULT_STYLES.atoms_font_size_2D = 10;
  ChemDoodle.DEFAULT_STYLES.atoms_font_families_2D = [
    "Helvetica",
    "Arial",
    "sans-serif",
  ];
  ChemDoodle.DEFAULT_STYLES.atoms_displayTerminalCarbonLabels_2D = true;
  ChemDoodle.DEFAULT_STYLES.atoms_useJMOLColors = false;
}

function renderChemdoodle(id) {
  if (enable_chemdoodle) {
    let chemdoodleJSON = JSON.parse(
      document.getElementById(`post-${id}-chemdoodle-json`).textContent
    );
    let viewerCanvas = new ChemDoodle.ViewerCanvas(
      `post-${id}-chemdoodle-canvas`
    );
    viewerCanvas.emptyMessage = "No Data Loaded!";
    var content = new ChemDoodle.io.JSONInterpreter().contentFrom(
      chemdoodleJSON
    );
    viewerCanvas.loadContent(content["molecules"], content["shapes"]);
    bounds = viewerCanvas.getContentBounds();
    width = Math.round(Math.abs(bounds["maxX"] - bounds["minX"])) + 30;
    height = Math.round(Math.abs(bounds["maxY"] - bounds["minY"])) + 30;
    viewerCanvas.resize(width, height);
    viewerCanvas.center();
    viewerCanvas.repaint();
  }
}
