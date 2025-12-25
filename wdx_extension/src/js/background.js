import { API_ADD } from './constants.js';

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "save_source", title: "In wdx speichern", contexts: ["page"] });
  chrome.contextMenus.create({ id: "save_text", title: "Textauswahl speichern", contexts: ["selection"] });
  
  chrome.alarms.create("retryQueue", { periodInMinutes: 5 });
});

chrome.runtime.onStartup.addListener(() => {
    processQueue();
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'QUEUE_SAVE') {
    addToQueue(request.payload);
  }
});

async function addToQueue(payload) {
  if (!payload) return;
  const q = await chrome.storage.local.get("offlineQueue");
  const queue = q.offlineQueue || [];
  
  // const exists = queue.some(item => item.url === payload.url && item.text === payload.text);
  // if (!exists) ...
  
  queue.push(payload);
  await chrome.storage.local.set({ offlineQueue: queue });
  
  // processQueue(); 
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "retryQueue") {
    processQueue();
  }
});

async function processQueue() {
    const q = await chrome.storage.local.get("offlineQueue");
    let queue = q.offlineQueue || [];
    if (queue.length === 0) return;

    const newQueue = [];
    let processedCount = 0;

    for (const item of queue) {
      try {
        const res = await fetch(API_ADD, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(item),
        });
        if (!res.ok) throw new Error();
        processedCount++;
      } catch (e) {
        newQueue.push(item);
      }
    }
    
    await chrome.storage.local.set({ offlineQueue: newQueue });
    
    if (processedCount > 0) {
        notify("Sync", `${processedCount} Elemente nachsynchronisiert.`);
    }
}

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
    addToQueue(payload);
    notify("Offline", "In Warteschlange gespeichert.");
  }
});

function notify(title, message) {
  try {
      if (localStorage.getItem("wdx-notifications") === "true") {
        chrome.notifications.create({
          type: "basic",
          iconUrl: "../img/icon512.png", 
          title: `wdx: ${title}`,
          message: message,
        });
      }
  } catch(e) {
      chrome.notifications.create({
          type: "basic",
          iconUrl: "../img/icon512.png", 
          title: `wdx: ${title}`,
          message: message,
      });
  }
}