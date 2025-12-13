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

class WdxApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.project_manager = ProjectManager()
        self.main_window = MainWindow(root, self)
        start_server(self)

        self.last_connection = None
        self.connection_count = 0
        self.current_project_name = None  # Wichtig für Erweiterung

        self.update_connection_status()

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
        self.current_project_name = project["name"]  # Für Erweiterung
        ProjectWindow(self.root, project, self)

    def handle_communication(self, data):
        self.last_connection = datetime.datetime.now()
        self.connection_count += 1

        self.root.deiconify()
        self.root.lift()

        # Wenn ein Projekt geöffnet ist → automatisch dort speichern
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
            "url": data["url"],
            "title": data.get("title", ""),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "color": "#ffffff",
            "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 300,
            "pos_y": 300
        }
        project["data"]["sources"].append(source)
        project["last_modified"] = datetime.datetime.now().isoformat()
        with open(project["data_file"], "w", encoding="utf-8") as f:
            json.dump(project["data"], f, indent=4)
        self.project_manager.save_projects()

        # Kein Popup mehr – alles automatisch
        # Optional: kleine Bestätigung
        # messagebox.showinfo("Erfolg", f"Quelle in '{project["name"]}' gespeichert.")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")
    app = WdxApp(root)
    try:
        root.mainloop()
    finally:
        if hasattr(app, "httpd"):
            app.httpd.shutdown()
            app.httpd.server_close()