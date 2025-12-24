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
  connectBtn: document.getElementById('connectBtn'),
  progress: document.getElementById('progressBar'),
  settingsBtn: document.getElementById('settingsBtn'),
  feedback: document.getElementById('feedback'),
  versionText: document.getElementById('version')
};

let isConnected = false;

ui.settingsBtn.addEventListener('click', () => chrome.runtime.openOptionsPage());
ui.connectBtn.addEventListener('click', checkConnection);

(async () => {
  ui.versionText.innerText = `v${VERSION} (${BUILDDATE})`;
  if (localStorage.getItem('wdx-autoconnect') !== 'false') {
    await checkConnection();
  } else {
    setDisconnectedUI();
  }
})();

async function checkConnection() {
  ui.progress.style.display = 'block';
  try {
    const res = await fetch(API_STATUS, { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      const data = await res.json();
      setConnectedUI(data.current_project);
    } else throw new Error();
  } catch (e) {
    setDisconnectedUI();
  } finally {
    ui.progress.style.display = 'none';
  }
}

function setConnectedUI(project) {
  isConnected = true;
  ui.statusDot.className = 'status-dot connected';
  ui.statusText.textContent = project || 'Verbunden';
  ui.saveBtn.disabled = false;
  ui.saveBtn.style.display = 'block';
  ui.connectBtn.style.display = 'none';
}

function setDisconnectedUI() {
  isConnected = false;
  ui.statusDot.className = 'status-dot error';
  ui.statusText.textContent = 'Nicht verbunden';
  ui.saveBtn.disabled = true;
  ui.saveBtn.style.display = 'none';
  ui.connectBtn.style.display = 'block';
}

ui.saveBtn.addEventListener('click', async () => {
  if (!isConnected) return;
  ui.progress.style.display = 'block';
  ui.saveBtn.disabled = true;

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const payload = {
      url: tab.url,
      title: tab.title,
      text: "", 
      keywords: ""
    };

    const res = await fetch(API_ADD, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) showFeedback("Gespeichert!", "success");
    else throw new Error();

  } catch (err) {
    if (localStorage.getItem('wdx-exp-offline-queue') === 'true') {
       chrome.runtime.sendMessage({ type: 'QUEUE_SAVE', payload: err.payload }); 
       showFeedback("Offline gespeichert (Queue)", "warning");
    } else {
       showFeedback("Fehler beim Speichern", "error");
    }
  } finally {
    ui.saveBtn.disabled = false;
    ui.progress.style.display = 'none';
  }
});

function showFeedback(msg, type) {
  ui.feedback.textContent = msg;
  ui.feedback.style.color = type === 'error' ? 'var(--md-sys-color-error)' : 
                            type === 'warning' ? '#e6b800' : 'var(--md-sys-color-success)';
  ui.feedback.style.opacity = 1;
  setTimeout(() => ui.feedback.style.opacity = 0, 2500);
}