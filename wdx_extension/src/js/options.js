const version = document.getElementById("version");
version.innerText = EXTENSION_VERION;

function applyTheme() {
  if (
    window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    document.body.classList.add("dark");
    document.body.classList.remove("light");
  } else {
    document.body.classList.add("light");
    document.body.classList.remove("dark");
  }
}
applyTheme();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);


const container = document.getElementById('settingsContainer');

container.addEventListener('change', (event) => {
    const target = event.target;
    if (target.type === 'checkbox') {
        console.log(`ID: ${target.id} | Checked: ${target.checked}`);
        localStorage.setItem("wdx-" + target.id, target.checked);
    }
});

['autoconnect', 'notifications'].forEach(id => {
  const savedStatus = localStorage.getItem(`wdx-${id}`);
  if (savedStatus !== null) {
    document.getElementById(id).checked = savedStatus === 'true';
  }
});