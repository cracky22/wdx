const API_BASE = "http://127.0.0.1:8765";
const API_ADD = API_BASE + "/api/add_source";
const API_STATUS = API_BASE + "/api/status";
const EXTENSION_VERION = "v1.2.0";

let isConnected = false;

const statusEl = document.getElementById("status");
const connectBtn = document.getElementById("connectBtn");
const saveBtn = document.getElementById("saveBtn");
const version = document.getElementById("version");
const projectEl = document.getElementById("currentProject");
const projectNameEl = document.getElementById("projectName");
const saveMessageEl = document.getElementById("saveMessage");

version.innerText = EXTENSION_VERION;

function applyTheme() {
  if (
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    document.body.classList.add("dark");
    document.body.classList.remove("light");
  } else {
    document.body.classList.add("light");
    document.body.classList.remove("dark");
  }
}
applyTheme();
window
  .matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", applyTheme);

function showMessage(text, type = "success") {
  saveMessageEl.textContent = text;
  saveMessageEl.className = type;
  saveMessageEl.style.opacity = 1;
  setTimeout(() => (saveMessageEl.style.opacity = 0), 3000);
}

async function updateConnection() {
  connectBtn.disabled = true;
  connectBtn.style.opacity = "0.5";
  connectBtn.textContent = "Verbinde wdx...";

  try {
    const response = await fetch(API_STATUS, { method: "GET" });
    if (response.ok) {
      const data = await response.json();
      isConnected = true;
      statusEl.textContent = "Verbunden mit wdx";
      statusEl.className = "status connected";
      connectBtn.textContent = "Verbunden ✓";
      connectBtn.classList.add("connected");
      saveBtn.disabled = false;
      saveBtn.style.opacity = "1";
      projectNameEl.textContent =
        data.current_project || "Kein Projekt geöffnet";
      projectEl.style.display = "block";
    } else {
      throw new Error();
    }
  } catch (err) {
    isConnected = false;
    statusEl.textContent = "Verbindung fehlgeschlagen – wdx läuft nicht?";
    statusEl.className = "status disconnected";
    connectBtn.textContent = "Verbinden";
    connectBtn.classList.remove("connected");
    saveBtn.disabled = true;
    saveBtn.style.opacity = "0.5";
    projectEl.style.display = "none";
  }
  connectBtn.disabled = false;
  connectBtn.style.opacity = "1";
}

connectBtn.addEventListener("click", updateConnection);

saveBtn.addEventListener("click", async () => {
  if (!isConnected) {
    showMessage("Keine Verbindung zu wdx", "error");
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  const payload = {
    url: tab.url,
    title: tab.title,
    text: "",
    keywords: "",
  };

  try {
    const response = await fetch(API_ADD, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (response.ok) {
      showMessage("Quelle erfolgreich gespeichert!");
      updateConnection();
    } else {
      showMessage("Fehler beim Speichern", "error");
    }
  } catch (err) {
    showMessage("Keine Verbindung zum wdx-Server", "error");
  }
});

updateConnection();
