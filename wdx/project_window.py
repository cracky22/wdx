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
import requests
from urllib.parse import urlparse, urljoin
import threading
import concurrent.futures


def get_contrast_color(hex_color):
    if hex_color.startswith("#"):
        hex_color = hex_color[1:]

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return "#000000"

    luminosity = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if luminosity > 128 else "#ffffff"


class ProjectWindow:
    DEFAULT_SELECT_BORDER_WIDTH = 5
    DEFAULT_SELECT_BORDER_COLOR = "primary"
    DEFAULT_SOURCE_BG = "#ffffff"
    DEFAULT_HEADING_BG = "#e9ecef"

    def __init__(self, root, project, app):
        self.project = project
        self.root = root
        self.app = app
        self.source_frames = {}
        self.card_widgets = {}
        self.selected_source_id = None
        self.dragging_card = False
        self.dragging_canvas = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.canvas_start_x = 0
        self.canvas_start_y = 0
        self.selected_source_ids = set()
        self.card_original_colors = {}
        self.clipboard = None
        self.paste_offset_x = 50
        self.paste_offset_y = 50
        self.last_file_mtime = 0
        self.update_last_mtime()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4)
        self.shutting_down = False
        self.zoom_level = self.project["data"].get("canvas_zoom_level", 1.0)
        self.max_zoom = 2.0
        self.min_zoom = 0.1
        self.zoom_factor = 1.2
        self.base_font_title = ("Helvetica", 13, "bold")
        self.base_font_heading = ("Helvetica", 17, "bold")
        self.base_font_default = ("Helvetica", 10)
        self.base_icon_size = 20
        self.base_favicon_subsample = 2
        self.minimap_canvas = None
        self.viewport_rect_id = None
        self._minimap_params = {}

        if "items" not in self.project["data"]:
            if "sources" in self.project["data"]:
                self.project["data"]["items"] = [
                    {"type": "source", **s} for s in self.project["data"]["sources"]
                ]
            else:
                self.project["data"]["items"] = []

        self.main_frame = ttk.Frame(self.root, padding="0", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        header_frame = ttk.Frame(self.main_frame, padding="15 10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(1, weight=1)
        ttk.Button(header_frame, text="← Zurück zu Projekten", command=self.back_to_projects, bootstyle="info-outline").grid(row=0, column=0, sticky=tk.W, padx=10)
        btn_frame = ttk.Frame(header_frame)
        btn_frame.grid(row=0, column=2, sticky=tk.E, padx=20)
        ttk.Button(btn_frame, text="💾", width=3, bootstyle="info-outline", command=self.manual_save).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="🔍", width=3, bootstyle="info-outline", command=self.reset_zoom).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="📥", width=3, bootstyle="info-outline", command=self.manual_export).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="🔄", width=3, bootstyle="info-outline", command=self.manual_reload).pack(side="left", padx=2)
        ttk.Label(header_frame, text=f"Mindmap: {project['name']}", font=("Helvetica", 18, "bold"), bootstyle="inverse-primary").grid(row=0, column=1, sticky=tk.W, padx=20)
        ttk.Label(header_frame, text=f"📋 {project['description']}", font=("Helvetica", 11)).grid(row=1, column=1, sticky=tk.W, padx=20, columnspan=2)
        self.canvas = tk.Canvas(self.main_frame, bg="#f5f7fa", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        h_scroll = ttk.Scrollbar(self.main_frame, orient="horizontal", command=self.canvas.xview, bootstyle="round")
        v_scroll = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.canvas.config(xscrollincrement=1, yscrollincrement=1)
        h_scroll.grid(row=2, column=0, sticky=(tk.W, tk.E))
        v_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))

        self.add_menu = tk.Menu(self.root, tearoff=0)
        self.add_menu.add_command(label="Überschrift (Strg+u)", command=self.add_heading)
        self.add_menu.add_command(label="Quellenangabe (Strg+n)", command=self.add_source)
        self.add_button = ttk.Button(self.main_frame, text="+", width=4, command=self.show_add_menu, bootstyle="primary-outline-toolbutton")
        self.add_button.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        self.minimap_canvas = tk.Canvas(self.main_frame, width=200, height=150, bg="#f5f7fa", highlightthickness=1, highlightbackground="#cccccc")
        self.minimap_canvas.place(relx=1.0, rely=1.0, x=-70, y=-70, anchor="se")
        self.minimap_canvas.bind("<ButtonPress-1>", self.on_minimap_click)
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Helvetica", 10))
        self.load_items_on_canvas()
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self._bind_zoom_events()
        self._bind_shortcuts()
        self.start_auto_refresh()

    def _bind_shortcuts(self):
        self.root.bind("<Control-s>", lambda e: self.manual_save())
        self.root.bind("<Command-s>", lambda e: self.manual_save())

        self.root.bind("<Control-q>", lambda e: self.shortcut_citation())
        self.root.bind("<Command-q>", lambda e: self.shortcut_citation())
        
        self.root.bind("<Delete>", lambda e: self.delete_shortcut())
        
        self.root.bind("<Control-h>", lambda e: self.show_saved_shortcut())
        self.root.bind("<Command-h>", lambda e: self.show_saved_shortcut())
        
        self.root.bind("<Control-l>", lambda e: self.reload_current_page_shortcut())
        self.root.bind("<Command-l>", lambda e: self.reload_current_page_shortcut())
        
        self.root.bind("<Control-e>", lambda e: self.edit_shortcut())
        self.root.bind("<Command-e>", lambda e: self.edit_shortcut())
        
        self.root.bind("<Control-w>", lambda e: self.back_to_projects())
        self.root.bind("<Command-w>", lambda e: self.back_to_projects())
        
        self.root.bind("<Control-r>", lambda e: self.reset_zoom())
        self.root.bind("<Command-r>", lambda e: self.reset_zoom())

        self.root.bind("<Control-p>", lambda e: self.manual_export())
        self.root.bind("<Command-p>", lambda e: self.manual_export())

        self.root.bind("<Control-b>", lambda e: self.manual_reload())
        self.root.bind("<Command-b>", lambda e: self.manual_reload())

        self.root.bind("<Control-d>", self._handle_duplicate_shortcut)
        self.root.bind("<Command-d>", self._handle_duplicate_shortcut)

        self.root.bind("<Control-c>", self._handle_copy_shortcut)
        self.root.bind("<Command-c>", self._handle_copy_shortcut)

        self.root.bind("<Control-v>", self._handle_paste_shortcut)
        self.root.bind("<Command-v>", self._handle_paste_shortcut)
        
        self.root.bind("<Control-u>", lambda e: self.add_heading())
        self.root.bind("<Command-u>", lambda e: self.add_heading())
        
        self.root.bind("<Control-n>", lambda e: self.add_source())
        self.root.bind("<Command-n>", lambda e: self.add_source())

    def _handle_duplicate_shortcut(self, event):
        if self.selected_source_ids:
            self.duplicate_selected_items()

    def _handle_copy_shortcut(self, event):
        if self.selected_source_ids:
            item_id = next(iter(self.selected_source_ids))
            item = next(
                (i for i in self.project["data"]["items"] if i["id"] == item_id), None
            )
            if item:
                self.copy_card(item)

    def _handle_paste_shortcut(self, event):
        if self.clipboard:
            self.paste_card()

    def _process_item_data(self, item):
        if item.get("type") == "heading":
            return {"item": item, "is_source": False, "favicon_path": None}

        favicon_path = None
        if item.get("favicon"):
            check_path = Path(self.project["path"]) / "images" / item["favicon"]
            if check_path.exists():
                favicon_path = str(check_path)

        return {"item": item, "is_source": True, "favicon_path": favicon_path}

    def load_items_on_canvas(self):
        items_to_process = self.project["data"]["items"]
        threading.Thread(target=self._concurrent_load_worker, args=(items_to_process,), daemon=True).start()

    def _concurrent_load_worker(self, items_to_process):
        try:
            if self.shutting_down: return
            processed_results = list(self.executor.map(self._process_item_data, items_to_process))

            if hasattr(self, "main_frame") and self.main_frame.winfo_exists() and not self.shutting_down:
                self.root.after(0, self._create_all_cards_in_gui_thread, processed_results)

        except concurrent.futures.CancelledError:
            pass
        except Exception as e:
            if not self.shutting_down:
                print(f"Fehler im Concurrent Load Worker: {e}")
                if hasattr(self, "main_frame") and self.main_frame.winfo_exists():
                    self.root.after(0, lambda: messagebox.showerror("Fehler", "Fehler beim parallelen Laden der Kartendaten."))

    def _create_all_cards_in_gui_thread(self, processed_results):
        if self.shutting_down: return
        for frame, item_id in list(self.source_frames.values()):
            self.canvas.delete(item_id)
            frame.destroy()
        self.source_frames.clear()
        self.card_widgets.clear()

        for result in processed_results:
            item = result["item"]
            if self.project["data"].get("selected_source_id") == item["id"]:
                self.selected_source_id = item["id"]

            if result["is_source"]:
                self._create_source_card_gui(item, result["favicon_path"])
            else:
                self._create_heading_card_gui(item)

        self.update_scrollregion()
        self._update_minimap()

    def _get_effective_bg_color(self, item):
        custom_color = item.get("color", "").strip()
        if custom_color:
            return custom_color

        if item["type"] == "source":
            return self.app.style.lookup("TFrame", "background")
        else:
            return self.app.style.lookup("TLabel", "background")

    def _get_default_border_width(self, item):
        return 2 if item["type"] == "source" else 0

    def _bind_zoom_events(self):
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self._on_mousewheel(event, up=True))
        self.canvas.bind("<Button-5>", lambda event: self._on_mousewheel(event, up=False))

    def _on_mousewheel(self, event, up=None):
        if self.dragging_canvas or self.dragging_card:
            return

        if up is None:
            direction = 1 if event.delta > 0 else -1
        else:
            direction = 1 if up else -1

        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        if direction > 0:
            self.zoom(self.zoom_factor, x, y)
        else:
            self.zoom(1 / self.zoom_factor, x, y)

    def zoom(self, factor, x, y):
        new_zoom = self.zoom_level * factor

        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        self.canvas.scale("all", x, y, factor, factor)
        self.zoom_level = new_zoom
        self._update_card_content_scale()
        self.update_scrollregion()
        self._update_minimap()

    def reset_zoom(self):
        if self.zoom_level == 1.0:
            return

        factor = 1.0 / self.zoom_level
        self.canvas.scale("all", 0, 0, factor, factor)
        self.zoom_level = 1.0
        self._update_card_content_scale()
        self.update_scrollregion()
        self._update_minimap()

    def _update_card_content_scale(self):
        title_size = max(int(self.base_font_title[1] * self.zoom_level), 5)
        heading_size = max(int(self.base_font_heading[1] * self.zoom_level), 8)
        default_size = max(int(self.base_font_default[1] * self.zoom_level), 5)
        icon_size = max(int(self.base_icon_size * self.zoom_level), 10)
        for item_id, refs in self.card_widgets.items():
            if "title_label" in refs:
                refs["title_label"].config(font=("Helvetica", title_size, "bold"))
            if "url_label" in refs:
                refs["url_label"].config(font=("Helvetica", default_size))
            if "text_label" in refs:
                refs["text_label"].config(font=("Helvetica", default_size))
            if "keywords_label" in refs:
                refs["keywords_label"].config(font=("Helvetica", default_size))
            if "added_label" in refs:
                refs["added_label"].config(font=("Helvetica", max(int(8 * self.zoom_level), 5)))

            if "heading_label" in refs:
                refs["heading_label"].config(font=("Helvetica", heading_size, "bold"))

            if "icon_label" in refs:
                if ("original_icon_data" in refs and refs["original_icon_data"]["is_favicon"]):
                    original_img = refs["original_icon_data"]["original_img"]
                    new_subsample = max(1, int(self.base_favicon_subsample / self.zoom_level))
                    try:
                        new_img = original_img.subsample(new_subsample, new_subsample)
                        refs["icon_label"].config(image=new_img)
                        refs["icon_label"].image = new_img
                    except tk.TclError:
                        pass
                else:
                    refs["icon_label"].config(font=("Helvetica", icon_size))

    def _create_source_card_gui(self, source, favicon_path):
        color = self._get_effective_bg_color(source)
        text_color = get_contrast_color(color)
        source["effective_color"] = color
        item_id = source["id"]
        style_name = f"Source.{item_id}.TFrame"
        self.card_widgets[item_id] = {}
        try:
            self.root.style.configure(style_name, background=color)
        except tk.TclError:
            self.root.style.configure(style_name, relief="raised", borderwidth=self._get_default_border_width(source))

        frame = ttk.Frame(self.canvas, padding="15")
        frame.item_data = source
        frame.unique_style_name = style_name
        frame.configure(style=style_name)
        default_border = self._get_default_border_width(source)
        frame.config(relief="raised", borderwidth=default_border)
        def on_enter(e, f=frame):
            if f.item_data["id"] not in self.selected_source_ids:
                f.config(borderwidth=default_border + 1, relief="ridge")

        def on_leave(e, f=frame):
            if f.item_data["id"] not in self.selected_source_ids:
                f.config(borderwidth=default_border, relief="raised")

        if favicon_path:
            try:
                original_img = tk.PhotoImage(file=favicon_path)
                self.card_widgets[item_id]["original_icon_data"] = {"original_img": original_img, "is_favicon": True}
                favicon_img = original_img.subsample(self.base_favicon_subsample, self.base_favicon_subsample)
                favicon_label = tk.Label(frame, image=favicon_img, bg=color)
                favicon_label.image = favicon_img
                favicon_label.pack(anchor="w")
                self.card_widgets[item_id]["icon_label"] = favicon_label
            except Exception:
                globe_label = tk.Label(frame, text="🌐", font=("Helvetica", self.base_icon_size), bg=color, fg=text_color)
                globe_label.pack(anchor="w")
                self.card_widgets[item_id]["icon_label"] = globe_label
        else:
            globe_label = tk.Label(frame, text="🌐", font=("Helvetica", self.base_icon_size), bg=color, fg=text_color)
            globe_label.pack(anchor="w")
            self.card_widgets[item_id]["icon_label"] = globe_label

        title_text = source.get("title") or source["url"]
        title_label = ttk.Label(frame, text=title_text, font=self.base_font_title, foreground=text_color, wraplength=320)
        title_label.pack(anchor="w")
        self.card_widgets[item_id]["title_label"] = title_label

        if source.get("title"):
            url_label = ttk.Label(frame, text=source["url"], font=self.base_font_default, foreground=text_color, wraplength=350)
            url_label.pack(anchor="w")
            self.card_widgets[item_id]["url_label"] = url_label

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            text_label = ttk.Label(frame, text=f"📝 {preview}", font=self.base_font_default, foreground=text_color, wraplength=350)
            text_label.pack(anchor="w", pady=(6, 0))
            self.card_widgets[item_id]["text_label"] = text_label

        if source["keywords"]:
            keywords_label = ttk.Label(frame, text=f"🏷 {source['keywords']}", font=self.base_font_default, bootstyle="info", foreground=text_color)
            keywords_label.pack(anchor="w", pady=(4, 0))
            self.card_widgets[item_id]["keywords_label"] = keywords_label

        added_label = ttk.Label(frame, text=f"📅 {source['added']}", font=("Helvetica", 8), foreground=text_color)
        added_label.pack(anchor="w", pady=(8, 0))
        self.card_widgets[item_id]["added_label"] = added_label

        ttk.Button(frame, text="🔗 Original öffnen", bootstyle="success-outline",width=20,command=lambda url=source["url"]: webbrowser.open(url)).pack(pady=(4, 0))

        frame.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

            try:
                if isinstance(child, (ttk.Label, tk.Label)):
                    child.config(background=color, foreground=text_color)
            except Exception:
                pass

        frame.bind("<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = source.get("pos_x", 300), source.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[item_id] = (frame, window_id)

        if self.selected_source_id == item_id:
            self.selected_source_ids.add(item_id)
            self.card_original_colors[item_id] = color
            self._apply_selection_style(item_id, color)
            self.selected_source_id = None

        if self.zoom_level != 1.0:
            self.canvas.scale(window_id, x, y, self.zoom_level, self.zoom_level)
            self._update_card_content_scale()

    def _create_heading_card_gui(self, heading):
        color = self._get_effective_bg_color(heading)
        text_color = get_contrast_color(color)
        heading["effective_color"] = color
        item_id = heading["id"]
        style_name = f"Heading.{item_id}.TFrame"
        self.card_widgets[item_id] = {}

        try:
            self.root.style.configure(style_name, background=color)
        except tk.TclError:
            self.root.style.configure(style_name, relief="flat", borderwidth=self._get_default_border_width(heading))

        frame = ttk.Frame(self.canvas, padding="15 20")
        frame.item_data = heading
        frame.unique_style_name = style_name
        frame.configure(style=style_name)
        default_border = self._get_default_border_width(heading)
        frame.config(relief="flat", borderwidth=default_border)

        def on_enter(e, f=frame):
            if f.item_data["id"] not in self.selected_source_ids:
                f.config(borderwidth=2, relief="groove")

        def on_leave(e, f=frame):
            if f.item_data["id"] not in self.selected_source_ids:
                f.config(borderwidth=default_border, relief="flat")

        label = tk.Label(frame, text=heading["text"], font=self.base_font_heading, fg=text_color, bg=color)
        label.pack()
        self.card_widgets[item_id]["heading_label"] = label
        frame.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))
        frame.bind("<Enter>", on_enter)
        frame.bind("<Leave>", on_leave)
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            try:
                if isinstance(child, (ttk.Label, tk.Label)):
                    child.config(background=color, foreground=text_color)
            except Exception:
                pass

        frame.bind("<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = heading.get("pos_x", 300), heading.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[item_id] = (frame, window_id)
        if self.selected_source_id == item_id:
            self.selected_source_ids.add(item_id)
            self.card_original_colors[item_id] = color
            self._apply_selection_style(item_id, color)
            self.selected_source_id = None

        if self.zoom_level != 1.0:
            self.canvas.scale(window_id, x, y, self.zoom_level, self.zoom_level)
            self._update_card_content_scale()

    def _update_minimap(self):
        if not self.minimap_canvas or not self.minimap_canvas.winfo_exists():
            return

        self.minimap_canvas.delete("all")
        bbox_all = self.canvas.bbox("all")
        if not bbox_all:
            self.viewport_rect_id = None
            self._update_minimap_viewport()
            return

        x1_main, y1_main, x2_main, y2_main = bbox_all
        buffer = 50 * self.zoom_level
        x1_main -= buffer
        y1_main -= buffer
        x2_main += buffer
        y2_main += buffer

        content_width = x2_main - x1_main
        content_height = y2_main - y1_main
        map_w = self.minimap_canvas.winfo_width()
        map_h = self.minimap_canvas.winfo_height()
        if content_width > 0 and content_height > 0:
            scale_x = map_w / content_width
            scale_y = map_h / content_height
            minimap_scale = min(scale_x, scale_y) * 0.9
        else:
            minimap_scale = 1.0

        center_x_map = map_w / 2
        center_y_map = map_h / 2
        offset_x = center_x_map - (x1_main + content_width / 2) * minimap_scale
        offset_y = center_y_map - (y1_main + content_height / 2) * minimap_scale

        for item_id, (frame, window_id) in self.source_frames.items():
            item = frame.item_data

            coords = self.canvas.coords(window_id)
            if not coords:
                continue
            frame_width = frame.winfo_reqwidth()
            frame_height = frame.winfo_reqheight()
            x_map_start = coords[0] * minimap_scale + offset_x
            y_map_start = coords[1] * minimap_scale + offset_y
            x_map_end = x_map_start + frame_width * minimap_scale
            y_map_end = y_map_start + frame_height * minimap_scale
            color = item.get("effective_color", "#cccccc")
            outline_color = "#333333" if item["type"] == "source" else ""
            self.minimap_canvas.create_rectangle(x_map_start, y_map_start, x_map_end, y_map_end, fill=color, outline=outline_color, width=1, tags=("card_rect", item_id))

        self._minimap_params = {"x1_main": x1_main, "y1_main": y1_main, "x2_main": x2_main, "y2_main": y2_main, "minimap_scale": minimap_scale, "offset_x": offset_x, "offset_y": offset_y}
        self._update_minimap_viewport()

    def _update_minimap_viewport(self):
        if (not self.minimap_canvas or not self.minimap_canvas.winfo_exists() or not hasattr(self, "_minimap_params")):
            return

        params = self._minimap_params
        minimap_scale = params["minimap_scale"]
        offset_x = params["offset_x"]
        offset_y = params["offset_y"]
        x_start_zoomed = self.canvas.canvasx(0)
        y_start_zoomed = self.canvas.canvasy(0)
        viewport_w_zoomed = self.canvas.winfo_width()
        viewport_h_zoomed = self.canvas.winfo_height()
        x_map_start = x_start_zoomed * minimap_scale + offset_x
        y_map_start = y_start_zoomed * minimap_scale + offset_y
        x_map_end = x_map_start + viewport_w_zoomed * minimap_scale
        y_map_end = y_map_start + viewport_h_zoomed * minimap_scale
        if self.viewport_rect_id and self.minimap_canvas.find_withtag(self.viewport_rect_id):
            self.minimap_canvas.coords(self.viewport_rect_id, x_map_start, y_map_start, x_map_end, y_map_end)
            self.minimap_canvas.tag_raise(self.viewport_rect_id)
        else:
            self.viewport_rect_id = self.minimap_canvas.create_rectangle(x_map_start, y_map_start, x_map_end, y_map_end, outline="#333333", fill="", width=2, stipple="gray50")

    def on_minimap_click(self, event):
        if not hasattr(self, "_minimap_params"):
            return

        params = self._minimap_params
        minimap_scale = params["minimap_scale"]
        offset_x = params["offset_x"]
        offset_y = params["offset_y"]
        x1_main, y1_main, x2_main, y2_main = (params["x1_main"], params["y1_main"], params["x2_main"], params["y2_main"])
        total_width = x2_main - x1_main
        total_height = y2_main - y1_main
        if total_width <= 0 or total_height <= 0:
            return
        target_x_zoomed = (event.x - offset_x) / minimap_scale
        target_y_zoomed = (event.y - offset_y) / minimap_scale
        center_x_zoomed = self.canvas.winfo_width() / 2
        center_y_zoomed = self.canvas.winfo_height() / 2
        new_x_start_zoomed = target_x_zoomed - center_x_zoomed
        new_y_start_zoomed = target_y_zoomed - center_y_zoomed
        x_fraction = (new_x_start_zoomed - x1_main) / total_width
        y_fraction = (new_y_start_zoomed - y1_main) / total_height
        x_fraction = max(0.0, min(1.0, x_fraction))
        y_fraction = max(0.0, min(1.0, y_fraction))
        self.canvas.xview_moveto(x_fraction)
        self.canvas.yview_moveto(y_fraction)
        self._update_minimap_viewport()

    def _apply_selection_style(self, item_id, color):
        if item_id in self.source_frames:
            frame = self.source_frames[item_id][0]
            text_color = get_contrast_color(color)
            frame.config(borderwidth=self.DEFAULT_SELECT_BORDER_WIDTH, bootstyle=self.DEFAULT_SELECT_BORDER_COLOR, relief="raised")
            for child in frame.winfo_children():
                try:
                    if isinstance(child, (ttk.Label, tk.Label)):
                        child.config(background=color, foreground=text_color)
                except Exception:
                    pass

    def _remove_selection_style(self, item_id, original_color, item_type):
        if item_id in self.source_frames:
            frame = self.source_frames[item_id][0]
            item = frame.item_data
            border = self._get_default_border_width(item)
            original_style_name = frame.unique_style_name
            text_color = get_contrast_color(original_color)
            self.root.style.configure(original_style_name, background=original_color)
            frame.configure(style=original_style_name, bootstyle=None, borderwidth=border, relief="raised" if item_type == "source" else "flat")
            for child in frame.winfo_children():
                try:
                    if isinstance(child, (ttk.Label, tk.Label)):
                        child.config(background=original_color, foreground=text_color)
                except Exception:
                    pass

    def handle_card_selection(self, item_id, event=None):
        frame = self.source_frames[item_id][0]
        item = frame.item_data
        ctrl_pressed = event and (event.state & 0x4)
        original_color = item.get("effective_color")
        if item_id not in self.card_original_colors:
            self.card_original_colors[item_id] = original_color

        if ctrl_pressed:
            if item_id in self.selected_source_ids:
                self.selected_source_ids.remove(item_id)
                self._remove_selection_style(item_id, original_color, item["type"])
                self.card_original_colors.pop(item_id, None)
            else:
                self.selected_source_ids.add(item_id)
                self._apply_selection_style(item_id, original_color)
        else:
            if (
                item_id in self.selected_source_ids
                and len(self.selected_source_ids) > 1
            ):
                pass
            elif item_id not in self.selected_source_ids:
                self.deselect_all_cards(exclude_id=item_id)
                self.selected_source_ids.add(item_id)
                self._apply_selection_style(item_id, original_color)

    def deselect_all_cards(self, exclude_id=None):
        ids_to_remove = list(self.selected_source_ids)
        for item_id in ids_to_remove:
            if item_id != exclude_id and item_id in self.source_frames:
                frame = self.source_frames[item_id][0]
                item = frame.item_data
                original_color = self.card_original_colors.pop(
                    item_id, item.get("effective_color", "#ffffff")
                )
                self._remove_selection_style(item_id, original_color, item["type"])
                self.selected_source_ids.remove(item_id)

    def deselect_card(self):
        self.deselect_all_cards()

    def deselect_card_from_context(self, item_id):
        if item_id in self.selected_source_ids:
            frame = self.source_frames[item_id][0]
            item = frame.item_data
            original_color = self.card_original_colors.pop(item_id, item.get("effective_color", "#ffffff"))
            self._remove_selection_style(item_id, original_color, item["type"])
            self.selected_source_ids.remove(item_id)

    def on_card_press(self, event, item_id):
        self.handle_card_selection(item_id, event)
        if item_id in self.selected_source_ids:
            self.dragging_card = True
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
            for selected_id in self.selected_source_ids:
                if selected_id in self.source_frames:
                    self.canvas.tag_raise(self.source_frames[selected_id][1])

    def on_card_motion(self, event):
        if self.dragging_card:
            dx = (event.x_root - self.drag_start_x) / self.zoom_level
            dy = (event.y_root - self.drag_start_y) / self.zoom_level
            for item_id in self.selected_source_ids:
                if item_id in self.source_frames:
                    window_id = self.source_frames[item_id][1]
                    self.canvas.move(window_id, dx, dy)

            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root

    def on_card_release(self, event):
        if self.dragging_card:
            for item_id in self.selected_source_ids:
                if item_id in self.source_frames:
                    coords = self.canvas.coords(self.source_frames[item_id][1])
                    item = next(i for i in self.project["data"]["items"] if i["id"] == item_id)

                    item["pos_x"] = coords[0]
                    item["pos_y"] = coords[1]

            self.save_project()
            self.update_last_mtime()
            self.dragging_card = False
            self.update_scrollregion()
            self._update_minimap()

    def on_canvas_press(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        search_radius = 2
        items = self.canvas.find_overlapping(x - search_radius, y - search_radius, x + search_radius, y + search_radius)
        card_items = [wid for _, wid in self.source_frames.values()]
        if any(item in card_items for item in items):
            return

        self.deselect_all_cards()
        self.dragging_canvas = True
        self.canvas_start_x = event.x
        self.canvas_start_y = event.y
        self.canvas.config(cursor="fleur")

    def on_canvas_motion(self, event):
        if self.dragging_canvas:
            self.canvas.xview_scroll(int(-1 * (event.x - self.canvas_start_x) / self.zoom_level), "units")
            self.canvas.yview_scroll(int(-1 * (event.y - self.canvas_start_y) / self.zoom_level), "units")
            self.canvas_start_x = event.x
            self.canvas_start_y = event.y
            self._update_minimap_viewport()

    def on_canvas_release(self, event):
        if self.dragging_canvas:
            self.dragging_canvas = False
            self.canvas.config(cursor="")
            self._update_minimap_viewport()

    def _create_new_item_from_existing(self, original_item, new_x_offset, new_y_offset):
        new_item = original_item.copy()
        new_item["id"] = str(uuid.uuid4())
        new_item["pos_x"] = original_item["pos_x"] + new_x_offset
        new_item["pos_y"] = original_item["pos_y"] + new_y_offset
        if new_item["type"] == "source":
            new_item["added"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            new_item.pop("effective_color", None)

        return new_item

    def duplicate_item(self, item):
        self.deselect_all_cards()
        new_item = self._create_new_item_from_existing(item, self.paste_offset_x, self.paste_offset_y)
        self.project["data"]["items"].append(new_item)
        if new_item["type"] == "source":
            threading.Thread(target=self._concurrent_reload_single_card, args=(new_item,), daemon=True).start()
        else:
            self._create_heading_card_gui(new_item)

        self.selected_source_ids.add(new_item["id"])

        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()

    def duplicate_selected_items(self):
        if not self.selected_source_ids:
            return

        new_ids = []
        items_to_process = []
        original_items = [
            next(i for i in self.project["data"]["items"] if i["id"] == item_id)
            for item_id in list(self.selected_source_ids)
        ]

        self.deselect_all_cards()

        for original_item in original_items:
            new_item = self._create_new_item_from_existing(original_item, self.paste_offset_x, self.paste_offset_y)

            self.project["data"]["items"].append(new_item)
            items_to_process.append(new_item)
            new_ids.append(new_item["id"])

        self.selected_source_ids.update(new_ids)
        self._concurrent_load_worker(items_to_process)

        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()
        self.paste_offset_x += 20
        self.paste_offset_y += 20
        if self.paste_offset_x > 100:
            self.paste_offset_x = 50
        if self.paste_offset_y > 100:
            self.paste_offset_y = 50

    def copy_card(self, item):
        self.clipboard = item.copy()
        self.clipboard.pop("effective_color", None)
        self.paste_offset_x = 50
        self.paste_offset_y = 50

    def paste_card(self):
        if not self.clipboard:
            return

        original_item = self.clipboard
        new_item = self._create_new_item_from_existing(original_item, self.paste_offset_x, self.paste_offset_y)
        self.project["data"]["items"].append(new_item)
        if new_item["type"] == "source":
            threading.Thread(target=self._concurrent_reload_single_card, args=(new_item,), daemon=True).start()
        else:
            self._create_heading_card_gui(new_item)

        self.deselect_all_cards()
        self.selected_source_ids.add(new_item["id"])
        self.paste_offset_x += 20
        self.paste_offset_y += 20
        if self.paste_offset_x > 100:
            self.paste_offset_x = 50
        if self.paste_offset_y > 100:
            self.paste_offset_y = 50
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()

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

    def show_saved_pages_popup(self, source):
        if not source.get("saved_pages"):
            messagebox.showinfo("Keine Versionen", "Es gibt keine gespeicherten Versionen dieser Seite.")
            return

        popup = tk.Toplevel(self.root)
        popup.title("Gespeicherte Versionen")
        popup.iconbitmap("icon128.ico")
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

        ttk.Button(popup, text="Ausgewählte öffnen", command=self.open_selected_version_from_popup, bootstyle="primary").pack(pady=10)
        ttk.Button(popup, text="Schließen", command=popup.destroy, bootstyle="secondary").pack(pady=5)
        
    def show_saved_shortcut(self):
        item_id = next(iter(self.selected_source_ids))
        item = next((i for i in self.project["data"]["items"] if i["id"] == item_id), None)
        self.show_saved_pages_popup(item)

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
        threading.Thread(
            target=self._reload_worker, args=(source,), daemon=True
        ).start()
        
    def reload_current_page_shortcut(self):
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        self.reload_current_page(item)

    def _reload_worker(self, source):
        sites_dir = Path(self.project["path"]) / "sites"
        images_dir = Path(self.project["path"]) / "images"
        sites_dir.mkdir(exist_ok=True)
        images_dir.mkdir(exist_ok=True)
        new_favicon_name = None
        try:
            response = requests.get(source["url"], timeout=15)
            response.raise_for_status()

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_{source['id']}_{timestamp}.html"

            with open(sites_dir / filename, "w", encoding="utf-8") as f:
                f.write(response.text)

            parsed = urlparse(source["url"])
            favicon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
            favicon_response = requests.get(favicon_url, timeout=5)
            if (
                favicon_response.status_code == 200
                and "image" in favicon_response.headers.get("Content-Type", "")
            ):
                favicon_filename = f"favicon_{source['id']}_{timestamp}.ico"
                favicon_path = images_dir / favicon_filename
                with open(favicon_path, "wb") as f:
                    f.write(favicon_response.content)
                new_favicon_name = favicon_filename

            self.root.after(
                0,
                self._finalize_reload,
                source["id"],
                filename,
                timestamp,
                new_favicon_name,
            )

        except requests.exceptions.Timeout:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error 408",
                    "Download Timeout-Fehler",
                    parent=self.root,
                ),
            )
        except requests.exceptions.RequestException as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Fehler", f"Download-Fehler: {e}", parent=self.root
                ),
            )
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Fehler",
                    f"Ein unerwarteter Fehler ist aufgetreten: {e}",
                    parent=self.root,
                ),
            )

    def _finalize_reload(self, source_id, filename, timestamp, new_favicon_name):
        source = next(
            (
                item
                for item in self.project["data"].get("items", [])
                if item.get("id") == source_id and item.get("type") == "source"
            ),
            None,
        )

        if not source:
            messagebox.showerror(
                "Fehler",
                "Quelle zum Aktualisieren nicht im Projekt gefunden.",
                parent=self.root,
            )
            return

        if "saved_pages" not in source:
            source["saved_pages"] = []

        source["saved_pages"].append(
            {
                "file": filename,
                "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            }
        )

        if new_favicon_name:
            source["favicon"] = new_favicon_name

        self.save_project()
        if source_id in self.source_frames:
            frame, item_id_canvas = self.source_frames[source_id]
            self.canvas.delete(item_id_canvas)
            frame.destroy()
            del self.source_frames[source_id]
            del self.card_widgets[source_id]
            threading.Thread(
                target=self._concurrent_reload_single_card, args=(source,), daemon=True
            ).start()

    def _concurrent_reload_single_card(self, source):
        try:
            result = self._process_item_data(source)
            if source["type"] == "source":
                self.root.after(
                    0, self._create_source_card_gui, source, result["favicon_path"]
                )
            else:
                self.root.after(0, self._create_heading_card_gui, source)

        except Exception as e:
            print(f"Fehler beim Neuladen der Einzelkarte: {e}")

    def show_context_menu(self, event, item):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(
            label="Löschen (Entf)", command=lambda: self.delete_item(item)
        )
        item_id = item["id"]
        self.context_menu.add_command(
            label="Duplizieren (Strg+d)", command=lambda: self.duplicate_item(item)
        )
        self.context_menu.add_separator()
        if item["type"] == "heading":
            self.context_menu.add_command(
                label="Umbenennen", command=lambda: self.rename_heading(item)
            )
            self.context_menu.add_command(
                label="Farbe ändern", command=lambda: self.change_heading_color(item)
            )
        else:
            if item.get("saved_pages") and len(item["saved_pages"]) > 0:
                self.context_menu.add_command(
                    label="Gespeicherte Versionen (Strg+h)",
                    command=lambda: self.show_saved_pages_popup(item),
                )
                self.context_menu.add_separator()

            self.context_menu.add_command(
                label="Quellenangabe erstellen (Strg+q)",
                command=lambda: self.create_citation(item),
            )
            self.context_menu.add_command(
                label="Karte bearbeiten (Strg+e)", command=lambda: self.edit_source(item)
            )
            self.context_menu.add_command(
                label="Seite erneut speichern (Strg+l)",
                command=lambda: self.reload_current_page(item),
            )

        if item["type"] == "source":
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Kopieren (Strg+c)", command=lambda: self.copy_card(item)
            )
            if self.clipboard:
                self.context_menu.add_command(
                    label="Einfügen (Strg+v)", command=self.paste_card
                )

        self.context_menu.add_separator()
        if item_id in self.selected_source_ids:
            self.context_menu.add_command(
                label="Karte abwählen",
                command=lambda: self.deselect_card_from_context(item_id),
            )
        else:
            self.context_menu.add_command(
                label="Karte wählen",
                command=lambda: self.deselect_all_cards(exclude_id=item_id)
                or self.handle_card_selection(item_id)
            )

        self.context_menu.post(event.x_root, event.y_root)

    def rename_heading(self, heading):
        new_text = simpledialog.askstring("Umbenennen", "Neuer Text:", initialvalue=heading["text"], parent=self.root)
        if new_text is not None and new_text != heading["text"]:
            heading["text"] = new_text
            frame, item_id = self.source_frames[heading["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[heading["id"]]
            del self.card_widgets[heading["id"]]
            self._create_heading_card_gui(heading)
            self.save_project()
            self.update_last_mtime()
            self.reset_zoom()
            self._update_minimap()

    def change_heading_color(self, heading):
        color_result = colorchooser.askcolor(title="Farbe wählen", initialcolor=heading["color"] or self.DEFAULT_HEADING_BG)
        
        if color_result and color_result[1]:
            color = color_result[1]
            if color != heading.get("color", ""):
                heading["color"] = "" if color == self.DEFAULT_HEADING_BG else color
                frame, item_id = self.source_frames[heading["id"]]
                self.canvas.delete(item_id)
                frame.destroy()
                del self.source_frames[heading["id"]]
                del self.card_widgets[heading["id"]]
                self._create_heading_card_gui(heading)
                self.save_project()
                self.update_last_mtime()
                self.reset_zoom()
                self._update_minimap()

    def delete_item(self, item):
        if messagebox.askyesno("Bestätigen", f"{'Überschrift' if item['type'] == 'heading' else 'Quelle'} löschen?", parent=self.root):
            item_id = item["id"]
            self.project["data"]["items"] = [i for i in self.project["data"]["items"] if i["id"] != item_id]
            frame, item_id_canvas = self.source_frames[item_id]
            self.canvas.delete(item_id_canvas)
            frame.destroy()
            del self.source_frames[item_id]
            del self.card_widgets[item_id]
            if item_id in self.selected_source_ids:
                self.selected_source_ids.remove(item_id)
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
            self.reset_zoom()
            self._update_minimap()
            
    def delete_shortcut(self):
        item_id = next(iter(self.selected_source_ids))
        item = next((i for i in self.project["data"]["items"] if i["id"] == item_id), None)
        self.delete_item(item)

    def add_heading(self):
        text = simpledialog.askstring("Überschrift hinzufügen", "Text der Überschrift:", parent=self.root)
        if not text:
            return

        color_result = colorchooser.askcolor(title="Farbe wählen", initialcolor=self.DEFAULT_HEADING_BG)
        color = color_result[1] if color_result else None
        
        color_to_save = "" if not color or color == self.DEFAULT_HEADING_BG else color
        new_heading = {"id": str(uuid.uuid4()), "type": "heading", "text": text, "color": color_to_save, "pos_x": 300, "pos_y": 300}
        self.project["data"]["items"].append(new_heading)
        self.deselect_all_cards()
        self._create_heading_card_gui(new_heading)
        self.selected_source_ids.add(new_heading["id"])
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()

    def add_source(self):
        dialog = SourceDialog(self.root, self)
        if dialog.result:
            new_source = {"id": str(uuid.uuid4()), "type": "source", "url": dialog.result["url"], "title": dialog.result["title"], "text": dialog.result["text"], "keywords": dialog.result["keywords"], "color": dialog.result["color"], "added": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "pos_x": 300 + len(self.project["data"]["items"]) * 80, "pos_y": 300, "favicon": "", "saved_pages": []}
            self.project["data"]["items"].append(new_source)
            self.deselect_all_cards()
            self.selected_source_ids.add(new_source["id"])
            threading.Thread(target=self._concurrent_reload_single_card, args=(new_source,), daemon=True).start()
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
            self.reset_zoom()
            self._update_minimap()

    def edit_source(self, source):
        dialog = SourceDialog(self.root, self, source)
        if dialog.result:
            source["url"] = dialog.result["url"]
            source["title"] = dialog.result["title"]
            source["text"] = dialog.result["text"]
            source["keywords"] = dialog.result["keywords"]
            source["color"] = dialog.result["color"]
            item_id = source["id"]
            frame, item_id_canvas = self.source_frames[item_id]
            self.canvas.delete(item_id_canvas)
            frame.destroy()
            del self.source_frames[item_id]
            del self.card_widgets[item_id]
            threading.Thread(target=self._concurrent_reload_single_card, args=(source,), daemon=True).start()
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
            self.reset_zoom()
            self._update_minimap()
            
    def edit_shortcut(self):
        item_id = next(iter(self.selected_source_ids))
        item = next((i for i in self.project["data"]["items"] if i["id"] == item_id), None)
        self.edit_source(item)

    def create_citation(self, source):
        #             google.de     , zuletzt aufgerufen am 31.12.2025
        #citation = f"{source['url']}, zuletzt aufgerufen am {source['added']}"
        # NACHNAME, V. (YYYY, DD.MM): TITLE. WSNAME. Abrufdatum, URL.
        citation = f"NACHNAME, V. (YYYY, DD.MM): TITLE. WSNAME. {source['added']}, {source['url']}"
        pyperclip.copy(citation)
        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")
        
    def shortcut_citation(self):
        item_id = next(iter(self.selected_source_ids))
        item = next((i for i in self.project["data"]["items"] if i["id"] == item_id), None)
        self.create_citation(item)

    def update_scrollregion(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 500
            x1, y1, x2, y2 = bbox
            new_scrollregion = (x1 - padding, y1 - padding, x2 + padding, y2 + padding)
            self.canvas.configure(scrollregion=new_scrollregion)
        else:
            self.canvas.configure(scrollregion=(-500, -500, 1000, 1000))

        self._update_minimap()

    def handle_external_data(self, data):
        threading.Thread(target=self._download_and_add_worker, args=(data,), daemon=True).start()

    def _download_and_add_worker(self, data):
        source_id = str(uuid.uuid4())
        new_source = {"id": source_id, "type": "source", "url": data["url"], "title": data.get("title", data["url"]), "text": data.get("text", ""), "keywords": data.get("keywords", ""), "color": "#ffffff", "added": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "pos_x": 300, "pos_y": 300, "favicon": "", "saved_pages": []}
        
        project_dir = Path(self.project["path"])
        images_dir = project_dir / "images"
        sites_dir = project_dir / "sites"
        images_dir.mkdir(exist_ok=True)
        sites_dir.mkdir(exist_ok=True)
        
        try:
            response = requests.get(data["url"], timeout=15)
            if response.status_code == 200:
                html_content = response.text
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                html_filename = f"page_{source_id}_{timestamp}.html"
                with open(sites_dir / html_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                new_source["saved_pages"].append({"file": html_filename, "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")})
                
                try:
                    parsed_uri = urlparse(data["url"])
                    base_url = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)
                    favicon_url = urljoin(base_url, "/favicon.ico")
                    fav_resp = requests.get(favicon_url, timeout=5)
                    if fav_resp.status_code == 200 and fav_resp.content:
                         fav_name = f"favicon_{source_id}.ico"
                         with open(images_dir / fav_name, "wb") as f:
                             f.write(fav_resp.content)
                         new_source["favicon"] = fav_name
                except Exception:
                    pass
        except Exception as e:
            print(f"External Add Error: {e}")

        self.root.after(0, lambda: self._add_external_source_to_gui(new_source))

    def _add_external_source_to_gui(self, new_source):
        self.project["data"]["items"].append(new_source)
        offset = len(self.project["data"]["items"]) * 20
        new_source["pos_x"] = 300 + (offset % 500)
        new_source["pos_y"] = 300 + (offset // 500) * 100
        
        self.deselect_all_cards()
        self.selected_source_ids.add(new_source["id"])
        threading.Thread(target=self._concurrent_reload_single_card, args=(new_source,), daemon=True).start()
        
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()

    def save_project(self):
        self.project["data"]["canvas_zoom_level"] = self.zoom_level
        self.project["data"]["selected_source_id"] = (next(iter(self.selected_source_ids)) if self.selected_source_ids else None)
        self.app.project_manager.save_specific_project_data(self.project)

    def start_auto_refresh(self):
        try:
            if self.shutting_down: return
            if self.dragging_card or self.dragging_canvas:
                self.root.after(3000, self.start_auto_refresh)
                return

            if os.path.exists(self.project["data_file"]):
                current_mtime = os.path.getmtime(self.project["data_file"])
            else:
                current_mtime = 0

            if current_mtime > self.last_file_mtime:
                self.reload_items()
                self.last_file_mtime = current_mtime
        except Exception as e:
            print("Auto-Refresh Fehler:", e)

        if not self.shutting_down:
            self.root.after(3000, self.start_auto_refresh)

    def reload_items(self):
        try:
            with open(self.project["data_file"], "r", encoding="utf-8") as f:
                updated_data = json.load(f)

            self.zoom_level = updated_data.get("canvas_zoom_level", 1.0)
            items = updated_data.get("items", [])
            self.project["data"]["items"] = items
            self.project["data"]["canvas_zoom_level"] = self.zoom_level
            self.selected_source_id = updated_data.get("selected_source_id")
            self.load_items_on_canvas()

        except Exception as e:
            print("Reload-Fehler:", e)

    def back_to_projects(self):
        self.shutting_down = True
        self.save_project()
        self.executor.shutdown(wait=False)
        self.main_frame.destroy()
        self.app.close_project()