let isMarking = false;
let startX, startY, endX, endY;
let overlay;

function createOverlay() {
  overlay = document.createElement("div");
  overlay.style.position = "fixed";
  overlay.style.top = "0";
  overlay.style.left = "0";
  overlay.style.width = "100%";
  overlay.style.height = "100%";
  overlay.style.backgroundColor = "rgba(0, 0, 255, 0.1)"; // Light blue, slightly transparent
  overlay.style.zIndex = "2147483647"; // Highest possible z-index
  overlay.style.display = "none";
  overlay.style.cursor = "crosshair";
  document.body.appendChild(overlay);

  overlay.addEventListener("mousedown", startMarking);
  overlay.addEventListener("mousemove", updateMarking);
  overlay.addEventListener("mouseup", endMarking);
}

function toggleMarkArea() {
  isMarking = !isMarking;
  overlay.style.display = isMarking ? "block" : "none";
  if (isMarking) {
    debugLog("Marking area enabled");
  } else {
    debugLog("Marking area disabled");
  }
}

function startMarking(e) {
  startX = e.clientX;
  startY = e.clientY;
  endX = startX;
  endY = startY;
  updateOverlay();
  debugLog("Started marking");
}

function updateMarking(e) {
  if (e.buttons !== 1) return;
  endX = e.clientX;
  endY = e.clientY;
  updateOverlay();
}

function endMarking() {
    const coordinates = { startX, startY, endX, endY };
    const htmlFragment = getHtmlFragment(coordinates);
    sendCoordinatesAndHtml(JSON.stringify({ coordinates, htmlFragment }));
    debugLog("Ended marking");
    toggleMarkArea();
}

function getHtmlFragment(coords) {
    const x = coords.startX;
    const y = coords.startY;
    const width = coords.endX - coords.startX;
    const height = coords.endY - coords.startY;

    const elements = document.elementsFromPoint(x + width / 2, y + height / 2);
    for (let element of elements) {
        if (element !== overlay && !overlay.contains(element)) {
            let rect = element.getBoundingClientRect();
            if (rect.width >= width * 0.9 && rect.height >= height * 0.9) {
                return element.outerHTML;
            }
        }
    }
    return null;
}

function updateOverlay() {
  var left = Math.min(startX, endX);
  var top = Math.min(startY, endY);
  var width = Math.abs(endX - startX);
  var height = Math.abs(endY - startY);

  overlay.innerHTML = `
        <div style="position: absolute; left: ${left}px; top: ${top}px; width: ${width}px; height: ${height}px; border: 2px solid red;"></div>
    `;
}

createOverlay();
toggleMarkArea(); // Start with marking enabled

// Expose the toggleMarkArea function globally so it can be called from Python
window.toggleMarkArea = toggleMarkArea; 