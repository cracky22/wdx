import '@material/web/switch/switch.js';

const settings = [
  'autoconnect', 
  'notifications', 
  'exp-offline-queue', 
  'exp-extract-context'
];

settings.forEach(async id => {
  const el = document.getElementById(id);
  const key = `wdx-${id}`;
  
  const data = await chrome.storage.local.get(key);
  el.selected = data[key] === 'true';

  el.addEventListener('change', (e) => {
    chrome.storage.local.set({ [key]: String(e.target.selected) });
  });
});