# Installation von wdx

## Kurzversion

Um **wdx** zu nutzen, lade die neueste Version aus den [Releases](https://github.com/cracky22/wdx/releases) herunter.

1. Entpacke die Datei **wdx_extension.crx** mit einem Tool wie [7-Zip](https://7-zip.org/).
2. Öffne deinen Browser und gehe zu **Erweiterungen**.
3. Aktiviere den **Entwicklermodus**.
4. Wähle **Entpackte Erweiterung laden** und wähle den entpackten Ordner aus.
5. Starte anschließend **main.py(c)** mit einer installierten Version von [Python](https://www.python.org/downloads/).

---

## Ausführliche Version

### Voraussetzungen

Bevor du startest, stelle sicher, dass folgende Dinge installiert sind:

* Ein aktueller Webbrowser (z. B. Chrome oder Chromium-basierte Browser)
* [Python](https://www.python.org/downloads/) (empfohlen: aktuelle stabile Version)
* Ein Entpackungsprogramm wie [7-Zip](https://7-zip.org/)

### Schritt 1: wdx herunterladen

Gehe auf die **Releases-Seite** des Projekts:

👉 [https://github.com/cracky22/wdx/releases](https://github.com/cracky22/wdx/releases)

Lade dort die neueste Version herunter und speichere sie lokal auf deinem Rechner.

### Schritt 2: Browser-Erweiterung entpacken

Im heruntergeladenen Ordner findest du die Datei **wdx_extension.crx**.

* Öffne die Datei mit 7-Zip (oder einem vergleichbaren Tool)
* Entpacke den Inhalt in einen beliebigen Ordner
* Merke dir diesen Ordner, du benötigst ihn gleich im Browser

### Schritt 3: Erweiterung im Browser installieren

1. Öffne deinen Browser
2. Navigiere zur Erweiterungsverwaltung (z. B. `chrome://extensions`)
3. Aktiviere oben rechts den **Entwicklermodus**
4. Klicke auf **Entpackte Erweiterung laden**
5. Wähle den zuvor entpackten Ordner der wdx-Erweiterung aus

Nach dem Laden sollte die Erweiterung direkt in der Liste erscheinen.

### Schritt 4: Python-Skript ausführen

Im Projektordner befindet sich die Datei **main.py** bzw. **main.pyc**.

* Öffne ein Terminal oder eine Kommandozeile
* Navigiere in das wdx-Verzeichnis
* Starte das Skript mit:

```bash
python main.py
```

oder, falls vorhanden:

```bash
python main.pyc
```

### Fertig

Sobald die Erweiterung geladen ist und das Python-Skript läuft, ist wdx einsatzbereit.

Falls etwas nicht funktioniert, überprüfe zuerst die Python-Version und ob die Erweiterung korrekt geladen wurde.
