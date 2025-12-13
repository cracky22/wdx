const HISTORY_KEY = "wdx_history";
const MAX_HISTORY = 3;
const API_URL = "http://localhost:8765/api/add_source";

// Lade History aus Storage und zeige an
chrome.storage.local.get([HISTORY_KEY], (result) => {
  const history = result[HISTORY_KEY] || [];
  const list = document.getElementById("history");
  if (history.length === 0) {
    list.innerHTML = "<li>Keine gesicherten Quellen bisher.</li>";
  } else {
    history.forEach((item) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = item.url;
      a.target = "_blank";
      a.textContent = item.title || item.url;
      li.appendChild(a);
      li.appendChild(
        document.createTextNode(
          ` (${new Date(item.timestamp).toLocaleString()})`
        )
      );
      list.appendChild(li);
    });
  }
});

// Prüfe, ob WDX läuft
fetch(API_URL, { method: "GET" })
  .then(() => {
    document.getElementById("status").textContent = "WDX läuft";
    document.getElementById("status").className = "status online";
  })
  .catch(() => {
    document.getElementById("status").textContent = "WDX ist nicht erreichbar";
    document.getElementById("status").className = "status offline";
  });