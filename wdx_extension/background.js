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
  let text = "";
  let keywords = "";

  if (info.menuItemId === "save_text" && info.selectionText) {
    text = info.selectionText.trim();
    keywords = prompt("Schlagworte (Kommas getrennt):") || "";
  } else if (info.menuItemId === "save_source") {
    keywords = prompt("Schlagworte (Kommas getrennt):") || "";
  }

  // Nachricht ans Popup senden – dort wird gespeichert und Meldung angezeigt
  chrome.runtime.sendMessage({
    type: info.menuItemId === "save_text" ? "save_text" : "save_page",
    url: tab.url,
    title: tab.title,
    text: text,
    keywords: keywords
  });
});