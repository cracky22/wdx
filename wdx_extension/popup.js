const API_BASE = 'http://127.0.0.1:8765';
const API_ADD = API_BASE + '/api/add_source';
const API_STATUS = API_BASE + '/api/status';  // Neuer Endpoint für Status + Projekt

let isConnected = false;

const statusEl = document.getElementById('status');
const connectBtn = document.getElementById('connectBtn');
const saveBtn = document.getElementById('saveBtn');
const projectEl = document.getElementById('currentProject');
const projectNameEl = document.getElementById('projectName');

// Dark Mode automatisch an System anpassen
function applyTheme() {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.body.classList.add('dark');
    document.body.classList.remove('light');
  } else {
    document.body.classList.add('light');
    document.body.classList.remove('dark');
  }
}
applyTheme();
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

// Verbindung prüfen und Projekt laden
async function updateConnection() {
  connectBtn.disabled = true;
  connectBtn.textContent = "Prüfe Verbindung...";

  try {
    const response = await fetch(API_STATUS, { method: 'GET' });

    if (response.ok) {
      const data = await response.json();

      isConnected = true;
      statusEl.textContent = "Verbunden mit WDX";
      statusEl.className = "status connected";
      connectBtn.textContent = "Verbunden ✓";
      connectBtn.classList.add("connected");
      saveBtn.disabled = false;

      if (data.current_project) {
        projectNameEl.textContent = data.current_project;
        projectEl.style.display = "block";
      } else {
        projectNameEl.textContent = "Kein Projekt geöffnet";
        projectEl.style.display = "block";
      }
    } else {
      throw new Error("Nicht 200");
    }
  } catch (err) {
    isConnected = false;
    statusEl.textContent = "Verbindung fehlgeschlagen – WDX läuft nicht?";
    statusEl.className = "status disconnected";
    connectBtn.textContent = "Verbinden";
    connectBtn.classList.remove("connected");
    saveBtn.disabled = true;
    projectEl.style.display = "none";
  }

  connectBtn.disabled = false;
}

connectBtn.addEventListener('click', updateConnection);

// Speichern in WDX
saveBtn.addEventListener('click', async () => {
  if (!isConnected) {
    alert("Keine Verbindung zu WDX");
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  const payload = {
    url: tab.url,
    title: tab.title,
    text: "",
    keywords: ""
  };

  try {
    const response = await fetch(API_ADD, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      alert("Quelle erfolgreich in WDX gespeichert!");
      updateConnection(); // Aktualisiert Projekt-Anzeige
    } else {
      alert("Fehler beim Speichern (Server-Antwort nicht OK).");
    }
  } catch (err) {
    alert("Keine Verbindung zum WDX-Server.");
  }
});

// Beim Öffnen des Popups prüfen
updateConnection();