import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox
from dialogs import SourceDialog
import datetime
import uuid
import webbrowser
import pyperclip
import json
import os

class ProjectWindow:
    def __init__(self, root, project, app):
        self.project = project
        self.root = root
        self.app = app
        self.source_frames = {}
        self.selected_source_id = None
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.last_file_mtime = 0
        self.update_last_mtime()

        self.main_frame = ttk.Frame(self.root, padding="0", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header_frame = ttk.Frame(self.main_frame, padding="15 10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)

        ttk.Button(header_frame, text="← Zurück zu Projekten", command=self.back_to_projects, bootstyle="secondary-outline").grid(row=0, column=0, sticky=tk.W, padx=10)
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
                                     bootstyle="primary-outline-toolbutton", width=20)
        self.add_button.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")

        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Helvetica", 10))

        self.load_sources_on_canvas()

        self.canvas.bind("<ButtonPress-1>", self.on_press)

        self.start_auto_refresh()

    def update_last_mtime(self):
        if os.path.exists(self.project["data_file"]):
            self.last_file_mtime = os.path.getmtime(self.project["data_file"])
        else:
            self.last_file_mtime = 0

    def load_sources_on_canvas(self):
        for source in self.project["data"]["sources"]:
            if "id" not in source:
                source["id"] = str(uuid.uuid4())
            if "color" not in source:
                source["color"] = "#ffffff"
            if "pos_x" not in source:
                source["pos_x"] = 300
                source["pos_y"] = 300
            self.create_source_card(source)
        self.update_scrollregion()

    def create_source_card(self, source):
        color = source.get("color", "#ffffff")

        # Karte mit Hintergrundfarbe, aber neutralem Rahmen
        frame = ttk.Frame(self.canvas, padding="15", relief="raised", borderwidth=2)
        frame.source_data = source
        frame.configure(style="Card.TFrame")
        self.root.style.configure("Card.TFrame", background=color)
        frame.configure(style="Card.TFrame")

        # Titel
        title_text = source.get("title") or source["url"]
        title_label = ttk.Label(frame, text=f"🌐 {title_text}", font=("Helvetica", 12, "bold"), foreground="#2c3e50", wraplength=320, background=color)
        title_label.pack(anchor="w")

        if source.get("title"):
            ttk.Label(frame, text=source["url"], font=("Helvetica", 9), foreground="#7f8c8d", wraplength=350, background=color).pack(anchor="w")

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            ttk.Label(frame, text=f"📝 {preview}", font=("Helvetica", 9), foreground="#34495e", wraplength=350, background=color).pack(anchor="w", pady=(6,0))

        if source["keywords"]:
            ttk.Label(frame, text=f"🏷 {source['keywords']}", font=("Helvetica", 9), bootstyle="info", background=color).pack(anchor="w", pady=(4,0))

        ttk.Label(frame, text=f"📅 {source['added']}", font=("Helvetica", 8), foreground="#95a5a6", background=color).pack(anchor="w", pady=(8,0))

        ttk.Button(frame, text="🔗 Öffnen", bootstyle="success-outline", width=15,
                   command=lambda url=source["url"]: webbrowser.open(url)).pack(pady=(4,0))

        # NEU: Auswahl-Button mit Fadenkreuz-Icon oben rechts
        select_btn = ttk.Button(frame, text="🎯", width=3, bootstyle="outline-secondary",
                                command=lambda sid=source["id"]: self.toggle_select_card(sid))
        select_btn.place(relx=1.0, rely=0, x=-10, y=10, anchor="ne")

        # Rechtsklick-Menü
        frame.bind("<Button-3>", lambda e, s=source: self.show_context_menu(e, s))
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, s=source: self.show_context_menu(e, s))

        # Drag & Drop
        frame.bind("<ButtonPress-1>", lambda e: self.on_frame_press(e, source["id"]))
        frame.bind("<B1-Motion>", lambda e: self.on_frame_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_frame_release(e))

        x, y = source.get("pos_x", 300), source.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[source["id"]] = (frame, window_id)

        # Rahmen aktualisieren, falls diese Karte ausgewählt ist
        if self.selected_source_id == source["id"]:
            frame.config(borderwidth=5, bootstyle="primary")

        self.update_scrollregion()

    def toggle_select_card(self, source_id):
        if self.selected_source_id == source_id:
            self.deselect_card()
        else:
            self.select_card(source_id)

    def show_context_menu(self, event, source):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="Löschen", command=lambda: self.delete_source(source))
        self.context_menu.add_command(label="Quellenangabe erstellen", command=lambda: self.create_citation(source))
        self.context_menu.add_command(label="Karte bearbeiten", command=lambda: self.edit_source(source))

        self.context_menu.post(event.x_root, event.y_root)

    def add_source(self):
        dialog = SourceDialog(self.root, self)
        if dialog.result:
            new_source = {
                "id": str(uuid.uuid4()),
                "url": dialog.result["url"],
                "title": dialog.result["title"],
                "text": dialog.result["text"],
                "keywords": dialog.result["keywords"],
                "color": dialog.result["color"],
                "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pos_x": 300 + len(self.project["data"]["sources"]) * 80,
                "pos_y": 300
            }
            self.project["data"]["sources"].append(new_source)
            self.create_source_card(new_source)
            self.save_project()
            self.update_last_mtime()

    def edit_source(self, source):
        dialog = SourceDialog(self.root, self, source)
        if dialog.result:
            source["url"] = dialog.result["url"]
            source["title"] = dialog.result["title"]
            source["text"] = dialog.result["text"]
            source["keywords"] = dialog.result["keywords"]
            source["color"] = dialog.result["color"]
            frame, item_id = self.source_frames[source["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[source["id"]]
            self.create_source_card(source)
            self.save_project()
            self.update_last_mtime()

    def select_card(self, source_id):
        # Alten Rahmen zurücksetzen
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            old_frame = self.source_frames[self.selected_source_id][0]
            old_frame.config(borderwidth=2, bootstyle="")

        self.selected_source_id = source_id
        frame = self.source_frames[source_id][0]
        frame.config(borderwidth=5, bootstyle="primary")

    def deselect_card(self):
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            frame = self.source_frames[self.selected_source_id][0]
            frame.config(borderwidth=2, bootstyle="")
        self.selected_source_id = None

    def on_frame_press(self, event, source_id):
        if source_id == self.selected_source_id:
            self.dragging = True
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
            self.canvas.tag_raise(self.source_frames[source_id][1])

    def on_frame_motion(self, event):
        if self.dragging:
            dx = event.x_root - self.drag_start_x
            dy = event.y_root - self.drag_start_y
            self.canvas.move(self.source_frames[self.selected_source_id][1], dx, dy)
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root

    def on_frame_release(self, event):
        if self.dragging:
            coords = self.canvas.coords(self.source_frames[self.selected_source_id][1])
            source = next(s for s in self.project["data"]["sources"] if s["id"] == self.selected_source_id)
            source["pos_x"] = coords[0]
            source["pos_y"] = coords[1]
            self.save_project()
            self.update_last_mtime()
            self.dragging = False
            self.update_scrollregion()

    def on_press(self, event):
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        if not items or items[-1] not in [wid for _, wid in self.source_frames.values()]:
            self.deselect_card()

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
            self.update_last_mtime()

    def create_citation(self, source):
        citation = f"{source['url']}, zuletzt aufgerufen am {source['added']}"
        pyperclip.copy(citation)
        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")

    def update_scrollregion(self):
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def save_project(self):
        with open(self.project["data_file"], "w", encoding="utf-8") as f:
            json.dump(self.project["data"], f, indent=4)
        self.project["last_modified"] = datetime.datetime.now().isoformat()
        self.app.project_manager.save_projects()

    def start_auto_refresh(self):
        try:
            if os.path.exists(self.project["data_file"]):
                current_mtime = os.path.getmtime(self.project["data_file"])
            else:
                current_mtime = 0

            if current_mtime > self.last_file_mtime:
                self.reload_sources()
                self.last_file_mtime = current_mtime
        except Exception as e:
            print("Auto-Refresh Fehler:", e)

        self.root.after(3000, self.start_auto_refresh)

    def reload_sources(self):
        try:
            with open(self.project["data_file"], "r", encoding="utf-8") as f:
                updated_data = json.load(f)

            for frame, item_id in list(self.source_frames.values()):
                self.canvas.delete(item_id)
                frame.destroy()
            self.source_frames.clear()

            self.project["data"]["sources"] = updated_data.get("sources", [])

            self.load_sources_on_canvas()
        except Exception as e:
            print("Reload-Fehler:", e)

    def back_to_projects(self):
        self.save_project()
        self.main_frame.destroy()
        self.app.main_window.show()