import os
import json
import shutil
import base64
import datetime
import re
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.icons import Icon
import pyperclip
from zipfile import ZipFile
import time
import threading
import http.server
import socketserver
import urllib.parse

# ========= KONFIG =========
VERSION = "1.0.0 devbeta"
APP_TITLE = f"WDX {VERSION}"
ICON_BASE64 = "BASE64BILD"  # Platzhalter für Base64-Icon
WDX_DIR = Path(os.path.expanduser("~/Documents/wdx"))
PROJECTS_FILE = WDX_DIR / "projects.json"
PORT = 8765  # HTTP-Server-Port

# Windows ungültige Zeichen für Dateinamen
INVALID_CHARS = r'[<>:"/\\|?*]'

class WdxHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, app=None, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self.path == "/api/add_source":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(post_data)
                self.app.handle_communication(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Invalid JSON"}')
        else:
            self.send_response(404)
            self.end_headers()

class WdxApp:
    def __init__(self, root):
        self.root = root
        self.style = ttk.Style("flatly")  # Modernes Design mit ttkbootstrap
        self.root.title(APP_TITLE)
        self.root.geometry("1000x600")
        try:
            self.root.iconbitmap(base64.b64decode(ICON_BASE64))
        except:
            pass

        WDX_DIR.mkdir(exist_ok=True)
        self.projects = []
        self.load_projects()

        # Hauptfenster GUI
        self.main_frame = ttk.Frame(self.root, padding="20", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Header mit Buttons
        header_frame = ttk.Frame(self.main_frame, padding="10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)

        ttk.Button(header_frame, text="Neues Projekt", command=self.create_project, bootstyle=(PRIMARY, OUTLINE), width=15).grid(row=0, column=0, padx=5)
        ttk.Button(header_frame, text="Projekt importieren", command=self.import_project, bootstyle=(SECONDARY, OUTLINE), width=15).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text=APP_TITLE, font=("Helvetica", 16, "bold"), bootstyle="inverse-primary").grid(row=0, column=2, sticky=tk.E)

        # Projektkacheln in Scrollable Frame
        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.project_frame = ttk.Frame(self.canvas, padding="10")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        self.project_window = self.canvas.create_window((0, 0), window=self.project_frame, anchor="nw")
        self.project_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._resize_canvas)

        self.update_project_tiles()

        # HTTP-Server starten
        self.start_http_server()

    def start_http_server(self):
        """Startet den HTTP-Server für die Chrome-Erweiterung."""
        handler = lambda *args, **kwargs: WdxHTTPRequestHandler(*args, app=self, **kwargs)
        self.httpd = socketserver.TCPServer(("", PORT), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def _resize_canvas(self, event):
        """Passt die Breite des Canvas-Fensters an."""
        self.canvas.itemconfig(self.project_window, width=event.width)

    def load_projects(self):
        """Lädt Projekte aus projects.json."""
        self.projects = []
        if PROJECTS_FILE.exists():
            try:
                with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                    projects_data = json.load(f)
                for project in projects_data:
                    project_path = Path(project["path"])
                    data_file = Path(project["data_file"])
                    if data_file.exists():
                        with open(data_file, "r", encoding="utf-8") as f:
                            project["data"] = json.load(f)
                        project["path"] = project_path
                        project["data_file"] = data_file
                        self.projects.append(project)
            except json.JSONDecodeError:
                messagebox.showwarning("Warnung", "projects.json ist beschädigt. Initialisiere neue Datei.")
                self.projects = []
                self.save_projects()

    def save_projects(self):
        """Speichert Projekte in projects.json."""
        projects_data = []
        for project in self.projects:
            project_data = {
                "name": project["name"],
                "description": project["description"],
                "created": project["created"],
                "last_modified": project["last_modified"],
                "path": str(project["path"]),
                "data_file": str(project["data_file"]),
                "data": project["data"]
            }
            projects_data.append(project_data)
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects_data, f, indent=4)

    def update_project_tiles(self):
        """Aktualisiert die Projektkacheln."""
        for widget in self.project_frame.winfo_children():
            widget.destroy()
        for idx, project in enumerate(self.projects):
            tile = ttk.Frame(self.project_frame, padding="15", bootstyle="info", relief="flat", borderwidth=2)
            tile.grid(row=idx, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
            tile.columnconfigure(0, weight=1)

            ttk.Label(tile, text=f"📋 {project['name']}", font=("Helvetica", 14, "bold"), bootstyle="inverse-info").grid(row=0, column=0, sticky=tk.W, pady=2)
            ttk.Label(tile, text=project["description"], wraplength=400, font=("Helvetica", 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
            ttk.Label(tile, text=f"📅 Erstellt: {project['created']}", font=("Helvetica", 10)).grid(row=2, column=0, sticky=tk.W, pady=2)
            last_modified = datetime.datetime.fromisoformat(project["last_modified"])
            now = datetime.datetime.now()
            minutes = (now - last_modified).total_seconds() / 60
            time_str = f"{int(minutes)} Minuten" if minutes < 60 else f"{int(minutes // 60)} Stunden"
            ttk.Label(tile, text=f"🕒 Bearbeitet: {time_str}", font=("Helvetica", 10)).grid(row=3, column=0, sticky=tk.W, pady=2)

            menu_button = ttk.Menubutton(tile, text="⋮", bootstyle=(DARK, OUTLINE), width=3)
            menu_button.grid(row=0, column=1, sticky=tk.E)
            menu = tk.Menu(menu_button, tearoff=0, font=("Helvetica", 10))
            menu.add_command(label="Umbenennen", command=lambda p=project: self.rename_project(p))
            menu.add_command(label="Bearbeiten", command=lambda p=project: self.edit_project(p))
            menu.add_command(label="Löschen", command=lambda p=project: self.delete_project(p))
            menu.add_command(label="Exportieren", command=lambda p=project: self.export_project(p))
            menu_button["menu"] = menu

            tile.bind("<Double-1>", lambda e, p=project: self.open_project(p))
            for child in tile.winfo_children():
                child.bind("<Double-1>", lambda e, p=project: self.open_project(p))

    def create_project(self):
        """Erstellt ein neues Projekt."""
        name = simpledialog.askstring("Neues Projekt", "Projektname:", parent=self.root)
        if not name:
            return
        if re.search(INVALID_CHARS, name):
            messagebox.showerror("Fehler", "Ungültige Zeichen im Projektnamen!")
            return
        description = simpledialog.askstring("Neues Projekt", "Projektbeschreibung:", parent=self.root)
        if not description:
            return
        project_path = WDX_DIR / name
        if project_path.exists():
            messagebox.showerror("Fehler", "Projekt existiert bereits!")
            return
        project_path.mkdir()
        (project_path / "images").mkdir()
        (project_path / "sites").mkdir()
        project_data = {
            "name": name,
            "description": description,
            "sources": [],
            "created": datetime.datetime.now().isoformat()
        }
        data_file = project_path / "project.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4)
        self.projects.append({
            "name": name,
            "description": description,
            "created": project_data["created"],
            "last_modified": project_data["created"],
            "path": project_path,
            "data_file": data_file,
            "data": project_data
        })
        self.save_projects()
        self.update_project_tiles()

    def import_project(self):
        """Importiert ein Projekt aus einer .wdx-Datei."""
        file_path = filedialog.askopenfilename(filetypes=[("WDX Files", "*.wdx")])
        if file_path:
            with ZipFile(file_path, "r") as zip_ref:
                temp_dir = WDX_DIR / "temp_import"
                temp_dir.mkdir(exist_ok=True)
                zip_ref.extractall(temp_dir)
                project_json = temp_dir / "project.json"
                if not project_json.exists():
                    messagebox.showerror("Fehler", "Ungültige WDX-Datei!")
                    shutil.rmtree(temp_dir)
                    return
                with open(project_json, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                project_name = project_data["name"]
                if re.search(INVALID_CHARS, project_name):
                    messagebox.showerror("Fehler", "Ungültige Zeichen im importierten Projektnamen!")
                    shutil.rmtree(temp_dir)
                    return
                project_path = WDX_DIR / project_name
                if project_path.exists():
                    messagebox.showerror("Fehler", "Projekt existiert bereits!")
                    shutil.rmtree(temp_dir)
                    return
                shutil.move(temp_dir, project_path)
                self.projects.append({
                    "name": project_name,
                    "description": project_data["description"],
                    "created": project_data["created"],
                    "last_modified": datetime.datetime.now().isoformat(),
                    "path": project_path,
                    "data_file": project_path / "project.json",
                    "data": project_data
                })
                self.save_projects()
                self.update_project_tiles()

    def rename_project(self, project):
        """Benennt ein Projekt um."""
        new_name = simpledialog.askstring("Umbenennen", "Neuer Projektname:", initialvalue=project["name"], parent=self.root)
        if new_name and new_name != project["name"]:
            if re.search(INVALID_CHARS, new_name):
                messagebox.showerror("Fehler", "Ungültige Zeichen im Projektnamen!")
                return
            new_path = WDX_DIR / new_name
            if new_path.exists():
                messagebox.showerror("Fehler", "Projektname existiert bereits!")
                return
            project["path"].rename(new_path)
            project["name"] = new_name
            project["path"] = new_path
            project["data_file"] = new_path / "project.json"
            project["data"]["name"] = new_name
            with open(project["data_file"], "w", encoding="utf-8") as f:
                json.dump(project["data"], f, indent=4)
            self.save_projects()
            self.update_project_tiles()

    def edit_project(self, project):
        """Bearbeitet die Projektbeschreibung."""
        new_desc = simpledialog.askstring("Bearbeiten", "Neue Projektbeschreibung:", initialvalue=project["description"], parent=self.root)
        if new_desc:
            project["description"] = new_desc
            project["data"]["description"] = new_desc
            project["last_modified"] = datetime.datetime.now().isoformat()
            with open(project["data_file"], "w", encoding="utf-8") as f:
                json.dump(project["data"], f, indent=4)
            self.save_projects()
            self.update_project_tiles()

    def delete_project(self, project):
        """Löscht ein Projekt."""
        if messagebox.askyesno("Bestätigen", f"Projekt '{project['name']}' löschen?", parent=self.root):
            shutil.rmtree(project["path"])
            self.projects.remove(project)
            self.save_projects()
            self.update_project_tiles()

    def export_project(self, project):
        """Exportiert ein Projekt als .wdx-Datei."""
        file_path = filedialog.asksaveasfilename(defaultextension=".wdx", filetypes=[("WDX Files", "*.wdx")], initialfile=f"{project['name']}.wdx")
        if file_path:
            with ZipFile(file_path, "w") as zip_ref:
                for file in project["path"].rglob("*"):
                    zip_ref.write(file, file.relative_to(project["path"]))
            messagebox.showinfo("Erfolg", f"Projekt als '{file_path}' exportiert.")

    def open_project(self, project):
        """Öffnet ein Projektfenster."""
        project["last_modified"] = datetime.datetime.now().isoformat()
        self.save_projects()
        ProjectWindow(self.root, project)
        self.update_project_tiles()

    def handle_communication(self, data):
        """Verarbeitet eingehende Quellen/Texte von der Chrome-Erweiterung."""
        self.root.deiconify()
        self.root.lift()
        project_names = [p["name"] for p in self.projects]
        if not project_names:
            messagebox.showerror("Fehler", "Keine Projekte vorhanden. Bitte erstellen Sie ein Projekt.")
            return
        project_name = simpledialog.askstring("Projekt wählen", "In welches Projekt speichern?", parent=self.root)
        if not project_name or project_name not in project_names:
            messagebox.showerror("Fehler", "Ungültiger Projektname!")
            return
        project = next(p for p in self.projects if p["name"] == project_name)
        source = {
            "url": data["url"],
            "title": data.get("title", ""),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        project["data"]["sources"].append(source)
        project["last_modified"] = datetime.datetime.now().isoformat()
        with open(project["data_file"], "w", encoding="utf-8") as f:
            json.dump(project["data"], f, indent=4)
        self.save_projects()
        messagebox.showinfo("Erfolg", f"Quelle '{source['url']}' in Projekt '{project_name}' gespeichert.")

class ProjectWindow:
    def __init__(self, parent, project):
        self.project = project
        self.window = tk.Toplevel(parent)
        self.style = ttk.Style("flatly")
        self.window.title(f"Projekt: {project['name']}")
        self.window.geometry("900x700")
        self.window.transient(parent)
        self.window.grab_set()

        self.main_frame = ttk.Frame(self.window, padding="20", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        header_frame = ttk.Frame(self.main_frame, padding="10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)
        ttk.Label(header_frame, text=f"Projekt: {project['name']}", font=("Helvetica", 16, "bold"), bootstyle="inverse-primary").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(header_frame, text=f"📋 {project['description']}", font=("Helvetica", 10)).grid(row=0, column=1, sticky=tk.E)

        search_frame = ttk.Frame(self.main_frame, padding="10")
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        ttk.Label(search_frame, text="🔍 Suche:", font=("Helvetica", 10)).grid(row=0, column=0, sticky=tk.W)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50, bootstyle="info")
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=10)
        search_frame.columnconfigure(1, weight=1)
        self.search_var.trace("w", self.update_source_list)

        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0, bootstyle="light")
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.source_frame = ttk.Frame(self.canvas, padding="10")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)

        self.source_window = self.canvas.create_window((0, 0), window=self.source_frame, anchor="nw")
        self.source_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.source_window, width=e.width))

        button_frame = ttk.Frame(self.main_frame, padding="10")
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=20)
        ttk.Button(button_frame, text="Quelle hinzufügen", command=self.add_source, bootstyle=(PRIMARY, OUTLINE), width=15).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Schließen", command=self.window.destroy, bootstyle=(SECONDARY, OUTLINE), width=15).grid(row=0, column=1, padx=5)

        self.context_menu = tk.Menu(self.window, tearoff=0, font=("Helvetica", 10))
        self.context_menu.add_command(label="Löschen", command=self.delete_source)
        self.context_menu.add_command(label="Quellenangabe erstellen", command=self.create_citation)

        self.update_source_list()

    def update_source_list(self, *args):
        """Aktualisiert die Quellenliste basierend auf der Suche."""
        for widget in self.source_frame.winfo_children():
            widget.destroy()
        search_term = self.search_var.get().lower()
        for idx, source in enumerate(self.project["data"]["sources"]):
            if not search_term or search_term in source["url"].lower() or search_term in source.get("keywords", "").lower():
                source_frame = ttk.Frame(self.source_frame, padding="10", bootstyle="secondary", relief="flat", borderwidth=1)
                source_frame.grid(row=idx, column=0, sticky=(tk.W, tk.E), pady=5)
                source_frame.columnconfigure(0, weight=1)

                display_text = f"🌐 {source['url']} (Hinzugefügt: {source['added']})"
                if source["title"]:
                    display_text = f"🌐 {source['title']}\n{source['url']} (Hinzugefügt: {source['added']})"
                if source["text"]:
                    display_text += f"\n📝 Text: {source['text'][:50]}..."
                ttk.Label(source_frame, text=display_text, wraplength=600, font=("Helvetica", 10)).grid(row=0, column=0, sticky=tk.W)
                ttk.Label(source_frame, text=f"🏷 Schlagworte: {source['keywords']}", font=("Helvetica", 9), bootstyle="secondary").grid(row=1, column=0, sticky=tk.W)

                source_frame.bind("<Button-3>", lambda e, i=idx: self.show_context_menu(e, i))
                for child in source_frame.winfo_children():
                    child.bind("<Button-3>", lambda e, i=idx: self.show_context_menu(e, i))

    def add_source(self):
        """Fügt eine neue Quelle hinzu."""
        url = simpledialog.askstring("Neue Quelle", "URL der Quelle eingeben:", parent=self.window)
        if url:
            keywords = simpledialog.askstring("Schlagworte", "Schlagworte (durch Kommas getrennt):", parent=self.window)
            source = {
                "url": url,
                "title": "",
                "text": "",
                "keywords": keywords or "",
                "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.project["data"]["sources"].append(source)
            self.project["last_modified"] = datetime.datetime.now().isoformat()
            self.save_project()
            self.update_source_list()
            messagebox.showinfo("Erfolg", f"Quelle '{url}' hinzugefügt.")

    def save_project(self):
        """Speichert die Projektdaten."""
        with open(self.project["data_file"], "w", encoding="utf-8") as f:
            json.dump(self.project["data"], f, indent=4)

    def show_context_menu(self, event, index):
        """Zeigt das Kontextmenü für die Quellenliste."""
        self.selected_source_index = index
        self.context_menu.post(event.x_root, event.y_root)

    def delete_source(self):
        """Löscht die ausgewählte Quelle."""
        if hasattr(self, "selected_source_index"):
            source = self.project["data"]["sources"][self.selected_source_index]
            if messagebox.askyesno("Bestätigen", f"Quelle '{source['url']}' löschen?", parent=self.window):
                self.project["data"]["sources"].pop(self.selected_source_index)
                self.project["last_modified"] = datetime.datetime.now().isoformat()
                self.save_project()
                self.update_source_list()

    def create_citation(self):
        """Kopiert die Quellenangabe in die Zwischenablage."""
        if hasattr(self, "selected_source_index"):
            source = self.project["data"]["sources"][self.selected_source_index]
            citation = f"{source['url']}, zuletzt aufgerufen am {source['added']}"
            pyperclip.copy(citation)
            messagebox.showinfo("Erfolg", "Quellenangabe in die Zwischenablage kopiert.")

if __name__ == "__main__":
    root = ttk.Window()
    app = WdxApp(root)
    try:
        root.mainloop()
    finally:
        if hasattr(app, "httpd"):
            app.httpd.shutdown()
            app.httpd.server_close()