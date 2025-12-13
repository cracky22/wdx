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
import pyperclip
from zipfile import ZipFile
import threading
import http.server
import socketserver
import webbrowser
import uuid

# ========= KONFIG =========
VERSION = "1.0.0 devbeta"
APP_TITLE = f"WDX {VERSION}"
ICON_BASE64 = "BASE64BILD"  # Platzhalter für Base64-Icon
WDX_DIR = Path(os.path.expanduser("~/Documents/wdx"))
PROJECTS_FILE = WDX_DIR / "projects.json"
PORT = 8765

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
        self.style = ttk.Style("flatly")
        self.root.title(APP_TITLE)
        self.root.geometry("1200x800")
        try:
            self.root.iconbitmap(base64.b64decode(ICON_BASE64))
        except:
            pass

        WDX_DIR.mkdir(exist_ok=True)
        self.projects = []
        self.load_projects()

        self.last_connection = None
        self.connection_count = 0

        self.main_frame = ttk.Frame(self.root, padding="20", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header_frame = ttk.Frame(self.main_frame, padding="10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)

        ttk.Button(header_frame, text="Neues Projekt", command=self.create_project, bootstyle=(PRIMARY, OUTLINE), width=15).grid(row=0, column=0, padx=5)
        ttk.Button(header_frame, text="Projekt importieren", command=self.import_project, bootstyle=(SECONDARY, OUTLINE), width=15).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text=APP_TITLE, font=("Helvetica", 16, "bold"), bootstyle="inverse-primary").grid(row=0, column=2, sticky=tk.E)

        self.status_label = ttk.Label(header_frame, text="Keine Browser-Verbindung", font=("Helvetica", 10), bootstyle="danger")
        self.status_label.grid(row=1, column=2, sticky=tk.E, pady=5)

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

        self.start_http_server()
        self.update_connection_status()

    def start_http_server(self):
        handler = lambda *args, **kwargs: WdxHTTPRequestHandler(*args, app=self, **kwargs)
        self.httpd = socketserver.TCPServer(("", PORT), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def _resize_canvas(self, event):
        self.canvas.itemconfig(self.project_window, width=event.width)

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
        if self.status_label.winfo_exists():
            self.status_label.config(text=text, bootstyle=style)
        self.root.after(30000, self.update_connection_status)

    def load_projects(self):
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
                self.save_projects()

    def save_projects(self):
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
            ttk.Label(tile, text=f"🕒 Bearbeitet: {time_str} her", font=("Helvetica", 10)).grid(row=3, column=0, sticky=tk.W, pady=2)

            menu_button = ttk.Menubutton(tile, text="⋮", bootstyle=(DARK, OUTLINE), width=3)
            menu_button.grid(row=0, column=1, sticky=tk.E)
            menu = tk.Menu(menu_button, tearoff=0, font=("Helvetica", 10))
            menu.add_command(label="✏️ Umbenennen", command=lambda p=project: self.rename_project(p))
            menu.add_command(label="📝 Bearbeiten", command=lambda p=project: self.edit_project(p))
            menu.add_command(label="💾 Exportieren", command=lambda p=project: self.export_project(p))
            menu.add_command(label="🗑️ Löschen", command=lambda p=project: self.delete_project(p))
            menu_button["menu"] = menu

            tile.bind("<Double-1>", lambda e, p=project: self.open_project(p))
            for child in tile.winfo_children():
                child.bind("<Double-1>", lambda e, p=project: self.open_project(p))

    def create_project(self):
        name = simpledialog.askstring("Neues Projekt", "Projektname:", parent=self.root)
        if not name:
            return
        if re.search(INVALID_CHARS, name):
            messagebox.showerror("Fehler", "Ungültige Zeichen im Projektnamen!")
            return
        description = simpledialog.askstring("Neues Projekt", "Projektbeschreibung:", parent=self.root)
        if description is None:
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
            "description": description or "",
            "sources": [],
            "created": datetime.datetime.now().isoformat()
        }
        data_file = project_path / "project.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4)
        self.projects.append({
            "name": name,
            "description": description or "",
            "created": project_data["created"],
            "last_modified": project_data["created"],
            "path": project_path,
            "data_file": data_file,
            "data": project_data
        })
        self.save_projects()
        self.update_project_tiles()

    def import_project(self):
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
                    "description": project_data.get("description", ""),
                    "created": project_data.get("created", datetime.datetime.now().isoformat()),
                    "last_modified": datetime.datetime.now().isoformat(),
                    "path": project_path,
                    "data_file": project_path / "project.json",
                    "data": project_data
                })
                self.save_projects()
                self.update_project_tiles()

    def rename_project(self, project):
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
        new_desc = simpledialog.askstring("Bearbeiten", "Neue Projektbeschreibung:", initialvalue=project["description"], parent=self.root)
        if new_desc is not None:
            project["description"] = new_desc
            project["data"]["description"] = new_desc
            project["last_modified"] = datetime.datetime.now().isoformat()
            with open(project["data_file"], "w", encoding="utf-8") as f:
                json.dump(project["data"], f, indent=4)
            self.save_projects()
            self.update_project_tiles()

    def delete_project(self, project):
        if messagebox.askyesno("Bestätigen", f"Projekt '{project['name']}' löschen?", parent=self.root):
            shutil.rmtree(project["path"])
            self.projects.remove(project)
            self.save_projects()
            self.update_project_tiles()

    def export_project(self, project):
        file_path = filedialog.asksaveasfilename(defaultextension=".wdx", filetypes=[("WDX Files", "*.wdx")], initialfile=f"{project['name']}.wdx")
        if file_path:
            with ZipFile(file_path, "w") as zip_ref:
                for file in project["path"].rglob("*"):
                    zip_ref.write(file, file.relative_to(project["path"]))
            messagebox.showinfo("Erfolg", f"Projekt als '{os.path.basename(file_path)}' exportiert.")

    def open_project(self, project):
        project["last_modified"] = datetime.datetime.now().isoformat()
        self.save_projects()
        self.main_frame.grid_remove()
        ProjectWindow(self.root, project, self)

    def handle_communication(self, data):
        self.last_connection = datetime.datetime.now()
        self.connection_count += 1

        self.root.deiconify()
        self.root.lift()
        project_names = [p["name"] for p in self.projects]
        if not project_names:
            messagebox.showerror("Fehler", "Keine Projekte vorhanden.")
            return
        project_name = simpledialog.askstring("Projekt wählen", "In welches Projekt speichern?\n\n" + "\n".join(project_names), parent=self.root)
        if not project_name or project_name not in project_names:
            messagebox.showerror("Fehler", "Ungültiger Projektname!")
            return
        project = next(p for p in self.projects if p["name"] == project_name)

        source = {
            "id": str(uuid.uuid4()),
            "url": data["url"],
            "title": data.get("title", ""),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 300,
            "pos_y": 300
        }
        project["data"]["sources"].append(source)
        project["last_modified"] = datetime.datetime.now().isoformat()
        with open(project["data_file"], "w", encoding="utf-8") as f:
            json.dump(project["data"], f, indent=4)
        self.save_projects()
        messagebox.showinfo("Erfolg", f"Quelle in '{project_name}' gespeichert.")

class ProjectWindow:
    def __init__(self, root, project, app):
        self.project = project
        self.root = root
        self.app = app
        self.source_frames = {}
        self.selected_source_id = None  # ID der ausgewählten Karte
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.main_frame = ttk.Frame(self.root, padding="0", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header_frame = ttk.Frame(self.main_frame, padding="15 10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)

        ttk.Button(header_frame, text="← Zurück zu Projekten", command=self.back_to_projects, bootstyle=(SECONDARY, OUTLINE)).grid(row=0, column=0, sticky=tk.W, padx=10)
        ttk.Label(header_frame, text=f"Mindmap: {project['name']}", font=("Helvetica", 18, "bold"), bootstyle="inverse-primary").grid(row=0, column=1, sticky=tk.W, padx=20)
        ttk.Label(header_frame, text=f"📋 {project['description']}", font=("Helvetica", 11)).grid(row=0, column=2, sticky=tk.E, padx=20)

        self.canvas = tk.Canvas(self.main_frame, bg="#f5f7fa", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        h_scroll = ttk.Scrollbar(self.main_frame, orient="horizontal", command=self.canvas.xview, bootstyle="round")
        v_scroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        h_scroll.grid(row=2, column=0, sticky=(tk.W, tk.E))
        v_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))

        self.add_button = ttk.Button(self.main_frame, text="+ Quelle hinzufügen", command=self.add_source,
                                     bootstyle=(PRIMARY, "outline-toolbutton"), width=20)
        self.add_button.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")

        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Helvetica", 10))

        self.load_sources_on_canvas()

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def load_sources_on_canvas(self):
        for source in self.project["data"]["sources"]:
            if "id" not in source:
                source["id"] = str(uuid.uuid4())
            if "pos_x" not in source:
                source["pos_x"] = 300
                source["pos_y"] = 300
            self.create_source_card(source)
        self.update_scrollregion()

    def create_source_card(self, source):
        frame = ttk.Frame(self.canvas, padding="15", bootstyle="secondary", relief="raised", borderwidth=2)
        frame.source_data = source

        title_text = source.get("title") or source["url"]
        ttk.Label(frame, text=f"🌐 {title_text}", font=("Helvetica", 12, "bold"), foreground="#2c3e50", wraplength=320).pack(anchor="w")

        if source.get("title"):
            ttk.Label(frame, text=source["url"], font=("Helvetica", 9), foreground="#7f8c8d", wraplength=350).pack(anchor="w")

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            ttk.Label(frame, text=f"📝 {preview}", font=("Helvetica", 9), foreground="#34495e", wraplength=350).pack(anchor="w", pady=(6,0))

        if source["keywords"]:
            ttk.Label(frame, text=f"🏷 {source['keywords']}", font=("Helvetica", 9), bootstyle="info").pack(anchor="w", pady=(4,0))

        ttk.Label(frame, text=f"📅 {source['added']}", font=("Helvetica", 8), foreground="#95a5a6").pack(anchor="w", pady=(8,0))

        ttk.Button(frame, text="🔗 Öffnen", bootstyle="success-outline", width=15,
                   command=lambda url=source["url"]: webbrowser.open(url)).pack(pady=(4,0))

        # Rechtsklick-Menü dynamisch bauen
        frame.bind("<Button-3>", lambda e, s=source: self.show_context_menu(e, s))

        x, y = source.get("pos_x", 300), source.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[source["id"]] = (frame, window_id)

        self.update_scrollregion()

    def show_context_menu(self, event, source):
        self.context_menu.delete(0, tk.END)  # Menü leeren
        self.context_menu.add_command(label="Löschen", command=lambda: self.delete_source(source))
        self.context_menu.add_command(label="Quellenangabe erstellen", command=lambda: self.create_citation(source))

        if self.selected_source_id == source["id"]:
            self.context_menu.add_command(label="Karte abwählen", command=lambda: self.deselect_card())
        else:
            self.context_menu.add_command(label="Karte wählen", command=lambda: self.select_card(source["id"]))

        self.context_menu.post(event.x_root, event.y_root)

    def select_card(self, source_id):
        # Alte Auswahl entfernen
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            old_frame = self.source_frames[self.selected_source_id][0]
            old_frame.config(borderwidth=2, bootstyle="secondary")

        # Neue Auswahl
        self.selected_source_id = source_id
        frame = self.source_frames[source_id][0]
        frame.config(borderwidth=5, bootstyle="primary", relief="solid")

    def deselect_card(self):
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            frame = self.source_frames[self.selected_source_id][0]
            frame.config(borderwidth=2, bootstyle="secondary")
        self.selected_source_id = None

    def on_press(self, event):
        items = self.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)
        if items:
            item_id = items[-1]
            for src_id, (_, wid) in self.source_frames.items():
                if wid == item_id and src_id == self.selected_source_id:
                    self.dragging = True
                    self.drag_start_x = event.x
                    self.drag_start_y = event.y
                    self.canvas.tag_raise(item_id)
                    break

    def on_motion(self, event):
        if self.dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            self.canvas.move(self.source_frames[self.selected_source_id][1], dx, dy)
            self.drag_start_x = event.x
            self.drag_start_y = event.y

    def on_release(self, event):
        if self.dragging:
            coords = self.canvas.coords(self.source_frames[self.selected_source_id][1])
            source = next(s for s in self.project["data"]["sources"] if s["id"] == self.selected_source_id)
            source["pos_x"] = coords[0]
            source["pos_y"] = coords[1]
            self.save_project()
            self.dragging = False
            self.update_scrollregion()

    def delete_source(self, source):
        if messagebox.askyesno("Bestätigen", f"Quelle '{source['url']}' löschen?", parent=self.root):
            self.project["data"]["sources"].remove(source)
            frame, item_id = self.source_frames[source["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[source["id"]]
            if self.selected_source_id == source["id"]:
                self.selected_source_id = None
            self.save_project()
            self.update_scrollregion()

    def create_citation(self, source):
        citation = f"{source['url']}, zuletzt aufgerufen am {source['added']}"
        pyperclip.copy(citation)
        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")

    def update_scrollregion(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def add_source(self):
        url = simpledialog.askstring("Neue Quelle", "URL eingeben:", parent=self.root)
        if not url:
            return
        keywords = simpledialog.askstring("Schlagworte", "Schlagworte (Kommas getrennt):", parent=self.root)
        source = {
            "id": str(uuid.uuid4()),
            "url": url,
            "title": "",
            "text": "",
            "keywords": keywords or "",
            "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 300 + len(self.project["data"]["sources"]) * 80,
            "pos_y": 300
        }
        self.project["data"]["sources"].append(source)
        self.create_source_card(source)
        self.save_project()
        messagebox.showinfo("Erfolg", "Quelle zur Mindmap hinzugefügt.")

    def save_project(self):
        with open(self.project["data_file"], "w", encoding="utf-8") as f:
            json.dump(self.project["data"], f, indent=4)
        self.project["last_modified"] = datetime.datetime.now().isoformat()

    def back_to_projects(self):
        self.save_project()
        self.main_frame.destroy()
        self.app.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.app.update_project_tiles()

if __name__ == "__main__":
    root = ttk.Window()
    app = WdxApp(root)
    try:
        root.mainloop()
    finally:
        if hasattr(app, "httpd"):
            app.httpd.shutdown()
            app.httpd.server_close()