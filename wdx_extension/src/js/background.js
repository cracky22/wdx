import { API_ADD } from './constants.js';

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "save_source", title: "In wdx speichern", contexts: ["page"] });
  chrome.contextMenus.create({ id: "save_text", title: "Textauswahl speichern", contexts: ["selection"] });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'QUEUE_SAVE') {
    addToQueue(request.payload);
  }
});

async function addToQueue(payload) {
  const q = await chrome.storage.local.get("offlineQueue");
  const queue = q.offlineQueue || [];
  if (payload) {
    queue.push(payload);
    await chrome.storage.local.set({ offlineQueue: queue });
  }
}

chrome.alarms.create("retryQueue", { periodInMinutes: 5 });

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "retryQueue") {
    const q = await chrome.storage.local.get("offlineQueue");
    let queue = q.offlineQueue || [];
    if (queue.length === 0) return;

    const newQueue = [];
    for (const item of queue) {
      try {
        const res = await fetch(API_ADD, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(item),
        });
        if (!res.ok) throw new Error();
      } catch (e) {
        newQueue.push(item);
      }
    }
    await chrome.storage.local.set({ offlineQueue: newQueue });
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const payload = {
    url: tab.url,
    title: tab.title || "Kein Titel",
    text: info.selectionText ? info.selectionText.trim() : "",
    keywords: "",
  };

  try {
    const res = await fetch(API_ADD, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Server Error");
    notify("Erfolg", "Gespeichert!");
    
  } catch (err) {
    if (localStorage.getItem("wdx-exp-offline-queue") === "true") {
      addToQueue(payload);
      notify("Offline", "In Warteschlange gespeichert.");
    } else {
      notify("Fehler", "Verbindung fehlgeschlagen.");
    }
  }
});

function notify(title, message) {
  if (localStorage.getItem("wdx-notifications") === "true") {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "../img/icon512.png", 
      title: `wdx: ${title}`,
      message: message,
    });
  }
}