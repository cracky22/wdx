import json
import os

manifest_path = 'wdx_extension/manifest.json'
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

if 'scripting' not in manifest['permissions']:
    manifest['permissions'].append('scripting')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print('Updated manifest.json')

popup_path = 'wdx_extension/src/js/popup.js'
with open(popup_path, 'r', encoding='utf-8') as f:
    popup_code = f.read()

old_popup_code = "    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });\n    const payload = { url: tab.url, title: tab.title, text: \"\", keywords: \"\" };"
new_popup_code = "    const payload = await getCurrentTabPayload();"

if old_popup_code in popup_code:
    popup_code = popup_code.replace(old_popup_code, new_popup_code)
    with open(popup_path, 'w', encoding='utf-8') as f:
        f.write(popup_code)
    print('Updated popup.js')
else:
    print('popup.js already updated or string not found')

bg_path = 'wdx_extension/src/js/background.js'
with open(bg_path, 'r', encoding='utf-8') as f:
    bg_code = f.read()

old_bg_code = """chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const payload = {
    url: tab.url,
    title: tab.title || "Kein Titel",
    text: info.selectionText ? info.selectionText.trim() : "",
    keywords: "",
  };"""

new_bg_code = """chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let author = "";
  let date = "";
  try {
      const prefs = await chrome.storage.local.get('wdx-exp-extract-context');
      if (prefs['wdx-exp-extract-context'] === 'true') {
          const results = await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              func: () => {
                  const getMeta = (names) => {
                      for (let name of names) {
                          const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                          if (el) return el.content;
                      }
                      return "";
                  };
                  return {
                      author: getMeta(['author', 'article:author', 'twitter:creator']),
                      date: getMeta(['published_date', 'article:published_time', 'date']) || document.lastModified
                  };
              }
          });
          if (results && results[0]) {
              author = results[0].result.author;
              date = results[0].result.date;
          }
      }
  } catch(e) { console.error("Smart Context failed", e); }

  const payload = {
    url: tab.url,
    title: tab.title || "Kein Titel",
    text: info.selectionText ? info.selectionText.trim() : "",
    keywords: "",
    author: author,
    date: date
  };"""

if old_bg_code in bg_code:
    bg_code = bg_code.replace(old_bg_code, new_bg_code)
    with open(bg_path, 'w', encoding='utf-8') as f:
        f.write(bg_code)
    print('Updated background.js')
else:
    print('background.js already updated or string not found')

main_path = 'wdx/__main__.py'
with open(main_path, 'r', encoding='utf-8') as f:
    main_code = f.read()

old_main_code = """        new_source = {
            "id": source_id,
            "type": "source",
            "url": url,
            "title": data.get("title", url),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "color": "#ffffff","""

new_main_code = """        new_source = {
            "id": source_id,
            "type": "source",
            "url": url,
            "title": data.get("title", url),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "author": data.get("author", ""),
            "date": data.get("date", ""),
            "color": "#ffffff","""

if old_main_code in main_code:
    main_code = main_code.replace(old_main_code, new_main_code)
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_code)
    print('Updated __main__.py')
else:
    print('__main__.py already updated or string not found')