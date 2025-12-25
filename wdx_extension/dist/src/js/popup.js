import '@material/web/button/filled-button.js';
import '@material/web/button/outlined-button.js';
import '@material/web/icon/icon.js';
import '@material/web/iconbutton/icon-button.js';
import '@material/web/progress/linear-progress.js';
import { API_STATUS, API_ADD, VERSION, BUILDDATE } from './constants.js';

const ui = {
  statusText: document.getElementById('statusText'),
  statusDot: document.getElementById('statusDot'),
  saveBtn: document.getElementById('saveBtn'),
  manualConnectBtn: document.getElementById('manualConnectBtn'),
  progress: document.getElementById('progressBar'),
  settingsBtn: document.getElementById('settingsBtn'),
  feedback: document.getElementById('feedback'),
  versionText: document.getElementById('version')
};

let isConnected = false;

ui.settingsBtn.addEventListener('click', () => chrome.runtime.openOptionsPage());
ui.manualConnectBtn.addEventListener('click', checkConnection);

(async () => {
  ui.versionText.innerText = `v${VERSION} (${BUILDDATE})`;
  
  const keys = ['wdx-autoconnect', 'wdx-notifications', 'wdx-exp-offline-queue'];
  const prefs = await chrome.storage.local.get(keys);
  
  if (prefs['wdx-autoconnect'] === undefined) {
    await chrome.storage.local.set({
      'wdx-autoconnect': 'true',
      'wdx-notifications': 'true',
      'wdx-exp-offline-queue': 'false'
    });
  }

  const sessionActive = sessionStorage.getItem('wdx-session-active') === 'true';
  const autoConnect = prefs['wdx-autoconnect'] !== 'false';

  if (autoConnect || sessionActive) {
    await checkConnection();
  } else {
    setDisconnectedUI();
  }
})();

async function checkConnection() {
  ui.progress.style.display = 'block';
  ui.manualConnectBtn.disabled = true;
  
  try {
    const res = await fetch(API_STATUS, { signal: AbortSignal.timeout(2100) });
    if (res.ok) {
      const data = await res.json();
      setConnectedUI(data.current_project);
    } else throw new Error();
  } catch (e) {
    setDisconnectedUI();
  } finally {
    ui.progress.style.display = 'none';
    ui.manualConnectBtn.disabled = false;
  }
}

function setConnectedUI(project) {
  isConnected = true;
  sessionStorage.setItem('wdx-session-active', 'true');
  ui.statusDot.className = 'status-dot connected';
  ui.statusText.textContent = project || 'Verbunden';
  ui.saveBtn.disabled = false;
  ui.manualConnectBtn.style.display = 'none';
}

function setDisconnectedUI() {
  isConnected = false;
  ui.statusDot.className = 'status-dot error';
  ui.statusText.textContent = 'Nicht verbunden';
  ui.manualConnectBtn.style.display = 'block';

  chrome.storage.local.get('wdx-exp-offline-queue').then(data => {
    ui.saveBtn.disabled = data['wdx-exp-offline-queue'] !== 'true';
  });
}

ui.saveBtn.addEventListener('click', async () => {
  const data = await chrome.storage.local.get('wdx-exp-offline-queue');
  const offlineQueueActive = data['wdx-exp-offline-queue'] === 'true';
  
  if (!isConnected && !offlineQueueActive) return;

  ui.progress.style.display = 'block';
  ui.saveBtn.disabled = true;

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const payload = { url: tab.url, title: tab.title, text: "", keywords: "" };

    if (!isConnected && offlineQueueActive) {
        throw { payload: payload, manualOffline: true };
    }

    const res = await fetch(API_ADD, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) showFeedback("Gespeichert!", "success");
    else throw new Error();

  } catch (err) {
    const payloadToQueue = err.payload || (await getCurrentTabPayload());
    if (offlineQueueActive) {
       chrome.runtime.sendMessage({ type: 'QUEUE_SAVE', payload: payloadToQueue }); 
       showFeedback("Offline gespeichert", "warning");
    } else {
       showFeedback("Fehler beim Speichern", "error");
    }
  } finally {
    ui.progress.style.display = 'none';
    const updatedData = await chrome.storage.local.get('wdx-exp-offline-queue');
    if (isConnected || updatedData['wdx-exp-offline-queue'] === 'true') {
        ui.saveBtn.disabled = false;
    }
  }
});

async function getCurrentTabPayload() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        return { url: tab.url, title: tab.title, text: "", keywords: "" };
    } catch (e) { return null; }
}

function showFeedback(msg, type) {
  ui.feedback.textContent = msg;
  ui.feedback.style.color = type === 'error' ? 'var(--md-sys-color-error)' : 
                            type === 'warning' ? '#e6b800' : 'var(--md-sys-color-success)';
  ui.feedback.style.opacity = 1;
  setTimeout(() => ui.feedback.style.opacity = 0, 2500);
}