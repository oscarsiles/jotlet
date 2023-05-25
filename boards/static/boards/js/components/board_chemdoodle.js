var enable_chemdoodle = JSON.parse(
  document.getElementById("chemdoodle_enabled").textContent
);

if (enable_chemdoodle) {
  ChemDoodle.DEFAULT_STYLES.bondLength_2D = 14.4;
  ChemDoodle.DEFAULT_STYLES.bonds_width_2D = 0.6;
  ChemDoodle.DEFAULT_STYLES.bonds_saturationWidthAbs_2D = 2.6;
  ChemDoodle.DEFAULT_STYLES.bonds_hashSpacing_2D = 2.5;
  ChemDoodle.DEFAULT_STYLES.atoms_font_size_2D = 10;
  ChemDoodle.DEFAULT_STYLES.atoms_font_families_2D = [
    "Helvetica",
    "Arial",
    "sans-serif",
  ];
  ChemDoodle.DEFAULT_STYLES.atoms_displayTerminalCarbonLabels_2D = true;
  ChemDoodle.DEFAULT_STYLES.atoms_useJMOLColors = true;
}

function renderChemdoodle(id) {
  if (enable_chemdoodle) {
    let chemdoodleJSON = JSON.parse(
      document.getElementById(`post-${id}-chemdoodle-json`).textContent
    );
    let viewACS = new ChemDoodle.ViewerCanvas(
      `post-${id}-chemdoodle-canvas`,
      100,
      100
    );
    var content = new ChemDoodle.io.JSONInterpreter().contentFrom(
      chemdoodleJSON
    );
    viewACS.loadContent(content["molecules"], content["shapes"]);
  }
}
