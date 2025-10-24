chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save_source",
    title: "Quelle in wdx sichern",
    contexts: ["page"]
  });
  chrome.contextMenus.create({
    id: "save_text",
    title: "Text in wdx sichern",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const keywords = prompt("Schlagworte (durch Kommas getrennt):") || "";
  const data = {
    title: tab.title,
    url: tab.url,
    text: info.selectionText || "",
    keywords: keywords
  };
  fetch("http://localhost:8765/api/add_source", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP-Fehler: ${response.status}`);
      }
      return response.json();
    })
    .then(result => {
      if (result.status === "success") {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icon48.png",
          title: "wdx Connector",
          message: "Quelle erfolgreich an wdx gesendet."
        });
      } else {
        throw new Error(result.message);
      }
    })
    .catch(error => {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icon48.png",
        title: "wdx Connector Fehler",
        message: "Fehler beim Senden an wdx: Stelle sicher, dass wdx läuft und auf Port 8765 erreichbar ist."
      });
    });
});