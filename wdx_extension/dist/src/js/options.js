import '@material/web/switch/switch.js';

const settings = [
  'autoconnect', 
  'notifications', 
  'exp-offline-queue', 
  'exp-extract-context'
];

settings.forEach(id => {
  const el = document.getElementById(id);
  const key = `wdx-${id}`;
  
  el.selected = localStorage.getItem(key) === 'true';

  el.addEventListener('change', (e) => {
    localStorage.setItem(key, e.target.selected);
  });
});