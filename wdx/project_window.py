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
from pathlib import Path
from constants import DEFAULT_COLOR
import requests
from urllib.parse import urlparse

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

        if "items" not in self.project["data"]:
            if "sources" in self.project["data"]:
                self.project["data"]["items"] = [{"type": "source", **s} for s in self.project["data"]["sources"]]
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

    def manual_export(self):
        success, file_path = self.app.project_manager.export_project(self.project)
        if success:
            messagebox.showinfo("Exportiert", f"Projekt als '{file_path}' exportiert.")

    def manual_reload(self):
        self.reload_items()

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

        # Favicon oder Globus
        favicon_path = Path(self.project["path"]) / "images" / source.get("favicon", "")
        if source.get("favicon") and favicon_path.exists():
            try:
                favicon_img = tk.PhotoImage(file=favicon_path)
                favicon_img = favicon_img.subsample(2, 2)
                favicon_label = ttk.Label(frame, image=favicon_img, background=color)
                favicon_label.image = favicon_img
                favicon_label.pack(anchor="w")
            except:
                ttk.Label(frame, text="🌐", font=("Helvetica", 20), background=color).pack(anchor="w")
        else:
            ttk.Label(frame, text="🌐", font=("Helvetica", 20), background=color).pack(anchor="w")

        title_text = source.get("title") or source["url"]
        ttk.Label(frame, text=title_text, font=("Helvetica", 12, "bold"), foreground="#2c3e50", wraplength=320, background=color).pack(anchor="w")

        if source.get("title"):
            ttk.Label(frame, text=source["url"], font=("Helvetica", 9), foreground="#7f8c8d", wraplength=350, background=color).pack(anchor="w")

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            ttk.Label(frame, text=f"📝 {preview}", font=("Helvetica", 9), foreground="#34495e", wraplength=350, background=color).pack(anchor="w", pady=(6,0))

        if source["keywords"]:
            ttk.Label(frame, text=f"🏷 {source['keywords']}", font=("Helvetica", 9), bootstyle="info", background=color).pack(anchor="w", pady=(4,0))

        ttk.Label(frame, text=f"📅 {source['added']}", font=("Helvetica", 8), foreground="#95a5a6", background=color).pack(anchor="w", pady=(8,0))

        
        if source.get("saved_pages", []):
            ttk.Button(frame, text="📄 Gespeicherte Seiten öffnen", bootstyle="info-outline", width=28,
                       command=lambda s=source: self.show_saved_pages_popup(s)).pack(pady=(4,0))

        ttk.Button(frame, text="🔗 Original öffnen", bootstyle="success-outline", width=20,
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

    def show_saved_pages_popup(self, source):
        if not source.get("saved_pages"):
            messagebox.showinfo("Keine Versionen", "Es gibt keine gespeicherten Versionen dieser Seite.")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Gespeicherte Versionen")
        popup.geometry("500x400")
        popup.transient(self.root)
        popup.grab_set()

        ttk.Label(popup, text=f"Gespeicherte Versionen von:\n{source['url']}", font=("Helvetica", 12, "bold")).pack(pady=10)

        listbox = tk.Listbox(popup, height=15)
        listbox.pack(fill="both", expand=True, padx=20, pady=10)

        sites_dir = Path(self.project["path"]) / "sites"
        self.current_source_for_popup = source
        self.current_listbox = listbox
        self.current_sites_dir = sites_dir

        for saved in source["saved_pages"]:
            timestamp = saved["timestamp"]
            filename = saved["file"]
            listbox.insert(tk.END, f"{timestamp} – {filename}")


        listbox.bind("<Double-Button-1>", lambda e: self.open_selected_version_from_popup())

        def open_selected():
            self.open_selected_version_from_popup()
            popup.destroy()

        ttk.Button(popup, text="Ausgewählte öffnen", command=open_selected, bootstyle="primary").pack(pady=10)
        ttk.Button(popup, text="Schließen", command=popup.destroy, bootstyle="secondary").pack(pady=5)

    def open_selected_version_from_popup(self):
        selection = self.current_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        saved_file = self.current_source_for_popup["saved_pages"][index]["file"]
        file_path = self.current_sites_dir / saved_file
        if file_path.exists():
            webbrowser.open(f"file://{file_path}")

    def reload_current_page(self, source):
        sites_dir = Path(self.project["path"]) / "sites"
        images_dir = Path(self.project["path"]) / "images"
        sites_dir.mkdir(exist_ok=True)
        images_dir.mkdir(exist_ok=True)

        try:
            response = requests.get(source["url"], timeout=15)
            if response.status_code == 200:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"page_{source['id']}_{timestamp}.html"
                file_path = sites_dir / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)

                
                parsed = urlparse(source["url"])
                favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
                favicon_response = requests.get(favicon_url, timeout=5)
                if favicon_response.status_code == 200 and "image" in favicon_response.headers.get("Content-Type", ""):
                    favicon_filename = f"favicon_{source['id']}_{timestamp}.ico"
                    favicon_path = images_dir / favicon_filename
                    with open(favicon_path, "wb") as f:
                        f.write(favicon_response.content)
                    source["favicon"] = favicon_filename


                if "saved_pages" not in source:
                    source["saved_pages"] = []
                source["saved_pages"].append({
                    "file": filename,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                
                frame, item_id = self.source_frames[source["id"]]
                self.canvas.delete(item_id)
                frame.destroy()
                del self.source_frames[source["id"]]
                self.create_source_card(source)

                self.save_project()
                messagebox.showinfo("Erfolg", "Aktuelle Seite wurde neu gespeichert!")
            else:
                messagebox.showerror("Fehler", f"HTTP {response.status_code}: Seite konnte nicht geladen werden.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden: {str(e)}")

    def show_context_menu(self, event, item):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="Löschen", command=lambda: self.delete_item(item))
        if item["type"] == "heading":
            self.context_menu.add_command(label="Umbenennen", command=lambda: self.rename_heading(item))
            self.context_menu.add_command(label="Farbe ändern", command=lambda: self.change_heading_color(item))
        else:
            self.context_menu.add_command(label="Quellenangabe erstellen", command=lambda: self.create_citation(item))
            self.context_menu.add_command(label="Karte bearbeiten", command=lambda: self.edit_source(item))
            self.context_menu.add_command(label="Aktuelle Seite neu laden", command=lambda: self.reload_current_page(item))

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
                "pos_y": 300,
                "favicon": "",
                "saved_pages": []
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

            for frame, item_id in list(self.source_frames.values()):
                self.canvas.delete(item_id)
                frame.destroy()
            self.source_frames.clear()

            items = updated_data.get("items", [])
            self.project["data"]["items"] = items

            self.load_items_on_canvas()
        except Exception as e:
            print("Reload-Fehler:", e)

    def back_to_projects(self):
        self.save_project()
        self.main_frame.destroy()
        self.app.main_window.show()