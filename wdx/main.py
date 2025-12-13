import tkinter as tk
import ttkbootstrap as ttk
from tkinter import simpledialog, messagebox
import datetime
import json
import uuid
from constants import APP_TITLE
from server import start_server
from project_manager import ProjectManager
from main_window import MainWindow
from project_window import ProjectWindow
from pathlib import Path
from bs4 import BeautifulSoup

class WdxApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.project_manager = ProjectManager()
        self.main_window = MainWindow(root, self)
        start_server(self)

        self.last_connection = None
        self.connection_count = 0
        self.current_project_name = None

        # Darkmode aus Einstellungen laden
        self.dark_mode = self.load_dark_mode_setting()
        self.apply_theme()

        self.update_connection_status()

    def load_dark_mode_setting(self):
        settings_file = Path.home() / "Documents" / "wdx" / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                return settings.get("dark_mode", False)
            except:
                return False
        return False

    def save_dark_mode_setting(self, enabled):
        settings_file = Path.home() / "Documents" / "wdx" / "settings.json"
        settings = {"dark_mode": enabled}
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)

    def apply_theme(self):
        theme = "darkly" if self.dark_mode else "flatly"
        self.root.style.theme_use(theme)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.save_dark_mode_setting(self.dark_mode)
        self.apply_theme()
        # MainWindow neu zeichnen
        self.main_window.main_frame.destroy()
        self.main_window = MainWindow(self.root, self)

    def update_connection_status(self):
        if self.last_connection:
            minutes_ago = (datetime.datetime.now() - self.last_connection).total_seconds() / 60
            if minutes_ago < 5:
                text = f"Verbunden ({self.connection_count} Aktionen)"
                style = "success"
            else:
                text = f"Letzte Verbindung vor {int(minutes_ago)} Min."
                style = "warning"
        else:
            text = "Keine Browser-Verbindung"
            style = "danger"
        self.main_window.status_label.config(text=text, bootstyle=style)
        self.root.after(30000, self.update_connection_status)

    def open_project(self, project):
        self.main_window.hide()
        self.current_project_name = project["name"]
        ProjectWindow(self.root, project, self)

    # ... (der Anfang von main.py bleibt unverändert bis handle_communication)

    def handle_communication(self, data):
        self.last_connection = datetime.datetime.now()
        self.connection_count += 1

        self.root.deiconify()
        self.root.lift()

        if self.current_project_name:
            project = next(p for p in self.project_manager.projects if p["name"] == self.current_project_name)
        else:
            project_names = [p["name"] for p in self.project_manager.projects]
            if not project_names:
                messagebox.showerror("Fehler", "Keine Projekte vorhanden.")
                return
            project_name = simpledialog.askstring("Projekt wählen", "In welches Projekt speichern?\n\n" + "\n".join(project_names), parent=self.root)
            if not project_name or project_name not in project_names:
                messagebox.showerror("Fehler", "Ungültiger Projektname!")
                return
            project = next(p for p in self.project_manager.projects if p["name"] == project_name)

        source = {
            "id": str(uuid.uuid4()),
            "type": "source",
            "url": data["url"],
            "title": data.get("title", ""),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "color": "#ffffff",
            "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 300,
            "pos_y": 300,
            "favicon": "",
            "saved_pages": []
        }

        project_dir = project["path"]
        images_dir = project_dir / "images"
        sites_dir = project_dir / "sites"
        images_dir.mkdir(exist_ok=True)
        sites_dir.mkdir(exist_ok=True)

        try:
            import requests
            from urllib.parse import urljoin, urlparse
            from bs4 import BeautifulSoup  # Neue Abhängigkeit – pip install beautifulsoup4

            # Seite herunterladen
            response = requests.get(data["url"], timeout=15)
            if response.status_code == 200:
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')

                # HTML speichern
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                html_filename = f"page_{source['id']}_{timestamp}.html"
                html_path = sites_dir / html_filename
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                source["saved_pages"].append({
                    "file": html_filename,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # Favicon finden (beste Methode)
                favicon_url = None
                # 1. <link rel="icon"> oder <link rel="shortcut icon">
                icon_link = soup.find("link", rel=lambda x: x and "icon" in x)
                if icon_link and icon_link.get("href"):
                    favicon_url = urljoin(data["url"], icon_link["href"])

                # 2. Fallback: /favicon.ico
                if not favicon_url:
                    parsed = urlparse(data["url"])
                    favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"

                # Favicon herunterladen
                if favicon_url:
                    try:
                        favicon_response = requests.get(favicon_url, timeout=10)
                        if favicon_response.status_code == 200 and favicon_response.content:
                            favicon_filename = f"favicon_{source['id']}.ico"
                            # Falls es PNG ist, umbenennen
                            if "image/png" in favicon_response.headers.get("Content-Type", ""):
                                favicon_filename = f"favicon_{source['id']}.png"
                            favicon_path = images_dir / favicon_filename
                            with open(favicon_path, "wb") as f:
                                f.write(favicon_response.content)
                            source["favicon"] = favicon_filename
                    except:
                        pass  # Wenn Favicon nicht geht, einfach ignorieren

        except Exception as e:
            print("Fehler beim Speichern von HTML/Favicon:", e)

        # Quelle in items speichern
        if "items" not in project["data"]:
            project["data"]["items"] = []
        project["data"]["items"].append(source)
        project["last_modified"] = datetime.datetime.now().isoformat()
        with open(project["data_file"], "w", encoding="utf-8") as f:
            json.dump(project["data"], f, indent=4)
        self.project_manager.save_projects()

if __name__ == "__main__":
    root = ttk.Window()
    app = WdxApp(root)
    try:
        root.mainloop()
    finally:
        if hasattr(app, "httpd"):
            app.httpd.shutdown()
            app.httpd.server_close()