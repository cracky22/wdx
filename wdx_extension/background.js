chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save_source",
    title: "Quelle in wdx sichern",
    contexts: ["page"]
  });
  chrome.contextMenus.create({
    id: "save_text",
    title: "Ausgewählten Text in wdx sichern",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || !tab.url) return;

  let text = "";

  if (info.menuItemId === "save_text" && info.selectionText) {
    text = info.selectionText.trim();
  }

  const payload = {
    url: tab.url,
    title: tab.title || "Kein Titel",
    text: text,
    keywords: ""
  };

  try {
    const response = await fetch("http://127.0.0.1:8765/api/add_source", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (response.ok) {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icon48.png",
        title: "wdx",
        message: text ? "Ausgewählter Text erfolgreich gespeichert!" : "Quelle erfolgreich gespeichert!"
      });
    } else {
      throw new Error("Server error");
    }
  } catch (err) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon48.png",
      title: "wdx Fehler",
      message: "Verbindung zu wdx fehlgeschlagen – ist die App gestartet?"
    });
  }
});