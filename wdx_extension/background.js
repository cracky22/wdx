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
  const data = {
    title: tab.title,
    url: tab.url,
    text: info.selectionText || ""
  };
  fetch("http://localhost:8765/api/add_source", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  }).catch(() => {
    alert("wdx ist nicht gestartet oder erreichbar.");
  });
});
