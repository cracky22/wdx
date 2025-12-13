import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser
from dialogs import SourceDialog
import datetime
import uuid
import webbrowser
import pyperclip
import json
import os
from constants import DEFAULT_COLOR

class ProjectWindow:
    def __init__(self, root, project, app):
        self.project = project
        self.root = root
        self.app = app
        self.source_frames = {}
        self.selected_source_id = None
        self.dragging_card = False
        self.dragging_canvas = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.canvas_start_x = 0
        self.canvas_start_y = 0

        self.last_file_mtime = 0
        self.update_last_mtime()

        # Datenstruktur bereinigen: Nur "items" verwenden
        if "items" not in self.project["data"]:
            if "sources" in self.project["data"]:
                self.project["data"]["items"] = [{"type": "source", **s} for s in self.project["data"]["sources"]]
                # Optional: sources entfernen, um sauber zu bleiben
                # del self.project["data"]["sources"]
            else:
                self.project["data"]["items"] = []

        self.main_frame = ttk.Frame(self.root, padding="0", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header_frame = ttk.Frame(self.main_frame, padding="15 10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(1, weight=1)

        ttk.Button(header_frame, text="← Zurück zu Projekten", command=self.back_to_projects, bootstyle="secondary-outline").grid(row=0, column=0, sticky=tk.W, padx=10)

        btn_frame = ttk.Frame(header_frame)
        btn_frame.grid(row=0, column=2, sticky=tk.E, padx=20)
        ttk.Button(btn_frame, text="💾", width=3, bootstyle="outline-secondary", command=self.manual_save).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="📥", width=3, bootstyle="outline-secondary", command=self.manual_export).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="🔄", width=3, bootstyle="outline-secondary", command=self.manual_reload).pack(side="left", padx=2)

        ttk.Label(header_frame, text=f"Mindmap: {project['name']}", font=("Helvetica", 18, "bold"), bootstyle="inverse-primary").grid(row=0, column=1, sticky=tk.W, padx=20)
        ttk.Label(header_frame, text=f"📋 {project['description']}", font=("Helvetica", 11)).grid(row=1, column=1, sticky=tk.W, padx=20, columnspan=2)

        self.canvas = tk.Canvas(self.main_frame, bg="#f5f7fa", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        h_scroll = ttk.Scrollbar(self.main_frame, orient="horizontal", command=self.canvas.xview, bootstyle="round")
        v_scroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        h_scroll.grid(row=2, column=0, sticky=(tk.W, tk.E))
        v_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))

        self.add_menu = tk.Menu(self.root, tearoff=0)
        self.add_menu.add_command(label="Quelle hinzufügen", command=self.add_source)
        self.add_menu.add_command(label="Überschrift hinzufügen", command=self.add_heading)

        self.add_button = ttk.Button(self.main_frame, text="+", width=4,
                                     command=self.show_add_menu,
                                     bootstyle="primary-outline-toolbutton")
        self.add_button.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")

        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Helvetica", 10))

        self.load_items_on_canvas()

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.start_auto_refresh()

    def show_add_menu(self, event=None):
        self.add_menu.post(self.add_button.winfo_rootx(), self.add_button.winfo_rooty() + self.add_button.winfo_height())

    def manual_save(self):
        self.save_project()
        messagebox.showinfo("Gespeichert", "Projekt wurde manuell gespeichert.")

    def manual_export(self):
        success, file_path = self.app.project_manager.export_project(self.project)
        if success:
            messagebox.showinfo("Exportiert", f"Projekt als '{file_path}' exportiert.")

    def manual_reload(self):
        self.reload_items()
        messagebox.showinfo("Neu geladen", "Mindmap wurde aus Datei neu geladen.")

    def update_last_mtime(self):
        if os.path.exists(self.project["data_file"]):
            self.last_file_mtime = os.path.getmtime(self.project["data_file"])
        else:
            self.last_file_mtime = 0

    def load_items_on_canvas(self):
        for item in self.project["data"]["items"]:
            if item.get("type") == "source":
                self.create_source_card(item)
            elif item.get("type") == "heading":
                self.create_heading_card(item)
        self.update_scrollregion()

    def create_source_card(self, source):
        color = source.get("color", DEFAULT_COLOR)

        frame = ttk.Frame(self.canvas, padding="15", relief="raised", borderwidth=2)
        frame.item_data = source
        frame.configure(style="Card.TFrame")
        self.root.style.configure("Card.TFrame", background=color)
        frame.configure(style="Card.TFrame")

        title_text = source.get("title") or source["url"]
        ttk.Label(frame, text=f"🌐 {title_text}", font=("Helvetica", 12, "bold"), foreground="#2c3e50", wraplength=320, background=color).pack(anchor="w")

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

        frame.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))

        frame.bind("<ButtonPress-1>", lambda e, iid=source["id"]: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = source.get("pos_x", 300), source.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[source["id"]] = (frame, window_id)

        if self.selected_source_id == source["id"]:
            frame.config(borderwidth=5, bootstyle="primary")
        else:
            frame.config(borderwidth=2, bootstyle=None)

        self.update_scrollregion()

    def create_heading_card(self, heading):
        color = heading.get("color", "#e9ecef")
        text_color = "#212529" if color == "#e9ecef" else "#ffffff"

        frame = ttk.Frame(self.canvas, padding="20", relief="flat", borderwidth=0)
        frame.item_data = heading
        frame.configure(style="Heading.TFrame")
        self.root.style.configure("Heading.TFrame", background=color)
        frame.configure(style="Heading.TFrame")

        label = ttk.Label(frame, text=heading["text"], font=("Helvetica", 16, "bold"), foreground=text_color, background=color)
        label.pack()

        frame.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))

        frame.bind("<ButtonPress-1>", lambda e, iid=heading["id"]: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = heading.get("pos_x", 300), heading.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[heading["id"]] = (frame, window_id)

        if self.selected_source_id == heading["id"]:
            frame.config(borderwidth=5, bootstyle="primary")
        else:
            frame.config(borderwidth=0, bootstyle=None)

        self.update_scrollregion()

    def add_heading(self):
        text = simpledialog.askstring("Überschrift hinzufügen", "Text der Überschrift:", parent=self.root)
        if not text:
            return

        color = colorchooser.askcolor(title="Farbe wählen", initialcolor="#e9ecef")[1]
        if not color:
            color = "#e9ecef"

        new_heading = {
            "id": str(uuid.uuid4()),
            "type": "heading",
            "text": text,
            "color": color,
            "pos_x": 300,
            "pos_y": 300
        }

        self.project["data"]["items"].append(new_heading)
        self.create_heading_card(new_heading)
        self.save_project()
        self.update_last_mtime()

    def show_context_menu(self, event, item):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="Löschen", command=lambda: self.delete_item(item))
        if item["type"] == "heading":
            self.context_menu.add_command(label="Umbenennen", command=lambda: self.rename_heading(item))
            self.context_menu.add_command(label="Farbe ändern", command=lambda: self.change_heading_color(item))
        else:
            self.context_menu.add_command(label="Quellenangabe erstellen", command=lambda: self.create_citation(item))
            self.context_menu.add_command(label="Karte bearbeiten", command=lambda: self.edit_source(item))

        if self.selected_source_id == item["id"]:
            self.context_menu.add_command(label="Karte abwählen", command=self.deselect_card)
        else:
            self.context_menu.add_command(label="Karte wählen", command=lambda: self.select_card(item["id"]))

        self.context_menu.post(event.x_root, event.y_root)

    def rename_heading(self, heading):
        new_text = simpledialog.askstring("Umbenennen", "Neuer Text:", initialvalue=heading["text"], parent=self.root)
        if new_text is not None and new_text != heading["text"]:
            heading["text"] = new_text
            frame, item_id = self.source_frames[heading["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[heading["id"]]
            self.create_heading_card(heading)
            self.save_project()
            self.update_last_mtime()

    def change_heading_color(self, heading):
        color = colorchooser.askcolor(title="Farbe wählen", initialcolor=heading["color"])[1]
        if color and color != heading["color"]:
            heading["color"] = color
            frame, item_id = self.source_frames[heading["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[heading["id"]]
            self.create_heading_card(heading)
            self.save_project()
            self.update_last_mtime()

    def delete_item(self, item):
        if messagebox.askyesno("Bestätigen", f"{'Überschrift' if item['type'] == 'heading' else 'Quelle'} löschen?", parent=self.root):
            self.project["data"]["items"] = [i for i in self.project["data"]["items"] if i["id"] != item["id"]]

            frame, item_id = self.source_frames[item["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[item["id"]]
            if self.selected_source_id == item["id"]:
                self.deselect_card()
            self.save_project()
            self.update_last_mtime()

    def add_source(self):
        dialog = SourceDialog(self.root, self)
        if dialog.result:
            new_source = {
                "id": str(uuid.uuid4()),
                "type": "source",
                "url": dialog.result["url"],
                "title": dialog.result["title"],
                "text": dialog.result["text"],
                "keywords": dialog.result["keywords"],
                "color": dialog.result["color"],
                "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pos_x": 300 + len(self.project["data"]["items"]) * 80,
                "pos_y": 300
            }
            self.project["data"]["items"].append(new_source)
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
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            old_frame = self.source_frames[self.selected_source_id][0]
            border = 2 if old_frame.item_data["type"] == "source" else 0
            old_frame.config(borderwidth=border, bootstyle=None)

        self.selected_source_id = source_id
        frame = self.source_frames[source_id][0]
        frame.config(borderwidth=5, bootstyle="primary")

    def deselect_card(self):
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            frame = self.source_frames[self.selected_source_id][0]
            border = 2 if frame.item_data["type"] == "source" else 0
            frame.config(borderwidth=border, bootstyle=None)
        self.selected_source_id = None

    def on_card_press(self, event, item_id):
        if item_id != self.selected_source_id:
            self.select_card(item_id)

        self.dragging_card = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.canvas.tag_raise(self.source_frames[item_id][1])

    def on_card_motion(self, event):
        if self.dragging_card:
            dx = event.x_root - self.drag_start_x
            dy = event.y_root - self.drag_start_y
            self.canvas.move(self.source_frames[self.selected_source_id][1], dx, dy)
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root

    def on_card_release(self, event):
        if self.dragging_card:
            coords = self.canvas.coords(self.source_frames[self.selected_source_id][1])
            item = next(i for i in self.project["data"]["items"] if i["id"] == self.selected_source_id)
            item["pos_x"] = coords[0]
            item["pos_y"] = coords[1]
            self.save_project()
            self.update_last_mtime()
            self.dragging_card = False
            self.update_scrollregion()

    def on_canvas_press(self, event):
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        card_items = [wid for _, wid in self.source_frames.values()]
        if any(item in card_items for item in items):
            return

        self.dragging_canvas = True
        self.canvas_start_x = event.x
        self.canvas_start_y = event.y
        self.canvas.config(cursor="fleur")

    def on_canvas_motion(self, event):
        if self.dragging_canvas:
            dx = event.x - self.canvas_start_x
            dy = event.y - self.canvas_start_y
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            self.canvas_start_x = event.x
            self.canvas_start_y = event.y

    def on_canvas_release(self, event):
        if self.dragging_canvas:
            self.dragging_canvas = False
            self.canvas.config(cursor="")

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
                self.reload_items()
                self.last_file_mtime = current_mtime
        except Exception as e:
            print("Auto-Refresh Fehler:", e)

        self.root.after(3000, self.start_auto_refresh)

    def reload_items(self):
        try:
            with open(self.project["data_file"], "r", encoding="utf-8") as f:
                updated_data = json.load(f)

            # Alles entfernen
            for frame, item_id in list(self.source_frames.values()):
                self.canvas.delete(item_id)
                frame.destroy()
            self.source_frames.clear()

            # Items übernehmen (Migration falls nötig)
            items = updated_data.get("items", [])
            if not items and "sources" in updated_data:
                items = [{"type": "source", **s} for s in updated_data["sources"]]

            self.project["data"]["items"] = items

            self.load_items_on_canvas()
        except Exception as e:
            print("Reload-Fehler:", e)

    def back_to_projects(self):
        self.save_project()
        self.main_frame.destroy()
        self.app.main_window.show()