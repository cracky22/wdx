# Installation von wdx

## Kurzversion

Um **wdx** zu nutzen, lade die neueste Version aus den [Releases](https://github.com/cracky22/wdx/releases) herunter.

1. Entpacke die Datei **wdx_extension.crx** mit einem Tool wie [7-Zip](https://7-zip.org/).
2. Öffne deinen Browser und gehe zu **Erweiterungen**.
3. Aktiviere den **Entwicklermodus** und wähle **Entpackte Erweiterung laden** und verwende den entpackten Ordner aus.
4. Starte anschließend **main.py** / **main.pyc** mit  [Python](https://www.python.org/downloads/).

##

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

### Python-Abhängigkeiten installieren

wdx benötigt einige externe Python-Pakete, die vor dem Start installiert werden müssen. Lade dir dazu aus dem 
Repository die **requirements.txt** herunter.


Installiere die Abhängigkeiten anschließend mit **pip**:

```bash
pip install -r requirements.txt
```

> Hinweis: `tkinter` gehört zur Python-Standardbibliothek und ist in der Regel bereits enthalten. Unter manchen Linux-Distributionen muss es ggf. separat über den Paketmanager installiert werden.

### Schritt 4: Python-Skript ausführen

Im Projektordner befindet sich die Datei **main.py** bzw. **main.pyc**.

* Öffne ein Terminal oder eine Kommandozeile
* Navigiere in das wdx-Verzeichnis
* Starte das Skript mit:

```bash
python main.pyc
```

oder, falls vorhanden (source code):

```bash
python main.py
```

### Fertig

Sobald die Erweiterung geladen ist und das Python-Skript läuft, ist wdx einsatzbereit.

Falls etwas nicht funktioniert, überprüfe zuerst die Python-Version und ob die Erweiterung korrekt geladen wurde.


_Info: diese Anleitung wurde mithilfe Künstlicher Intelligenz erstellt_