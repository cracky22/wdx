import '@material/web/iconbutton/icon-button.js';
import '@material/web/icon/icon.js';
import '@material/web/list/list.js';
import '@material/web/list/list-item.js';
import { API_ADD } from './constants.js';

const ui = {
  list: document.getElementById('queueList'),
  syncBtn: document.getElementById('syncAllBtn'),
  backBtn: document.getElementById('backBtn')
};

ui.backBtn.addEventListener('click', () => window.location.href = 'popup.html');
ui.syncBtn.addEventListener('click', syncAll);

async function renderQueue() {
  const { offlineQueue = [] } = await chrome.storage.local.get('offlineQueue');
  const list = document.getElementById('queueList');
  list.innerHTML = '';

  if (offlineQueue.length === 0) {
    list.innerHTML = '<div class="empty-msg" style="user-select: none;">Warteschlange ist leer</div>';
    return;
  }

  offlineQueue.forEach((item, index) => {
    const listItem = document.createElement('md-list-item');
    
    listItem.headline = item.title || 'Kein Titel';
    listItem.supportingText = item.url;
    
    const titleSpan = document.createElement('span');
    titleSpan.slot = 'headline';
    titleSpan.textContent = item.title || 'Kein Titel';
    listItem.appendChild(titleSpan);

    const urlSpan = document.createElement('span');
    urlSpan.slot = 'supporting-text';
    urlSpan.textContent = item.url;
    listItem.appendChild(urlSpan);

    const deleteBtn = document.createElement('md-icon-button');
    deleteBtn.slot = 'end';
    deleteBtn.innerHTML = '<md-icon>delete</md-icon>';
    deleteBtn.onclick = (e) => {
        e.stopPropagation();
        removeItem(index);
    };

    listItem.appendChild(deleteBtn);
    ui.list.appendChild(listItem);
  });
}

async function removeItem(index) {
  const { offlineQueue } = await chrome.storage.local.get('offlineQueue');
  offlineQueue.splice(index, 1);
  await chrome.storage.local.set({ offlineQueue });
  renderQueue();
}

async function syncAll() {
  chrome.runtime.sendMessage({ type: 'PROCESS_QUEUE' });
  setTimeout(renderQueue, 1000);
}

renderQueue();