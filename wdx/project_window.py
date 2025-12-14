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
import threading 
import concurrent.futures 

# NEUE HILFSFUNKTION FÜR KONTRAST-TEXTFARBE
def get_contrast_color(hex_color):
    """Gibt Weiß (#ffffff) oder Schwarz (#000000) zurück, abhängig von der Helligkeit der Hex-Farbe."""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    
    # Konvertiere Hex zu RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        # Fallback für ungültige Hex-Werte, um Abstürze zu verhindern
        return "#000000" 

    # Berechne Leuchtdichte (Luminosity, ITU BT.709)
    # Wenn die Leuchtdichte unter 128 (Mittelwert) liegt, ist die Farbe dunkel -> verwende weißen Text
    # Formel: 0.2126 * R + 0.7152 * G + 0.0722 * B
    luminosity = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    
    return "#000000" if luminosity > 128 else "#ffffff"

class ProjectWindow:
    
    # Neue Konstanten für das Farbsystem und die Auswahl
    DEFAULT_SELECT_BORDER_WIDTH = 5
    DEFAULT_SELECT_BORDER_COLOR = "primary" # Dies steuert die Borderfarbe (blau/dunkelblau)
    
    # Theme-abhängige Farben für unkolorierte Karten (Light Mode Defaults)
    DEFAULT_SOURCE_BG = "#ffffff"   
    DEFAULT_HEADING_BG = "#e9ecef"
    
    def __init__(self, root, project, app):
        self.project = project
        self.root = root
        self.app = app
        self.source_frames = {} 
        self.card_widgets = {}  
        self.selected_source_id = None
        # Wird die effektive Farbe der Karte speichern, BEVOR der Auswahl-Bootstyle angewendet wird
        self.selected_card_original_color = None 
        self.dragging_card = False
        self.dragging_canvas = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.canvas_start_x = 0
        self.canvas_start_y = 0

        self.last_file_mtime = 0
        self.update_last_mtime()

        # Thread-Pool für Multicore/I/O
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4)

        # Zoom-Einstellungen
        self.zoom_level = self.project["data"].get("canvas_zoom_level", 1.0) 
        self.max_zoom = 2.0
        self.min_zoom = 0.1
        self.zoom_factor = 1.2 
        # Basis-Fonts für Skalierung
        self.base_font_title = ("Helvetica", 12, "bold")
        self.base_font_heading = ("Helvetica", 16, "bold")
        self.base_font_default = ("Helvetica", 9)
        self.base_icon_size = 20 
        self.base_favicon_subsample = 2 
        
        # Minimap-Einstellungen
        self.minimap_canvas = None
        self.viewport_rect_id = None
        self._minimap_params = {}

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
        # NEU: Zoom Reset Button
        ttk.Button(btn_frame, text="🔍", width=3, bootstyle="outline-secondary", command=self.reset_zoom).pack(side="left", padx=2)
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
        self.canvas.config(xscrollincrement=1, yscrollincrement=1) 
        h_scroll.grid(row=2, column=0, sticky=(tk.W, tk.E))
        v_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))

        self.add_menu = tk.Menu(self.root, tearoff=0)
        self.add_menu.add_command(label="Quelle hinzufügen", command=self.add_source)
        self.add_menu.add_command(label="Überschrift hinzufügen", command=self.add_heading)

        self.add_button = ttk.Button(self.main_frame, text="+", width=4,
                                     command=self.show_add_menu,
                                     bootstyle="primary-outline-toolbutton")
        self.add_button.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        
        # NEU: Minimap Canvas
        self.minimap_canvas = tk.Canvas(self.main_frame, width=200, height=150, 
                                        bg="#f5f7fa", highlightthickness=1, highlightbackground="#cccccc")
        self.minimap_canvas.place(relx=1.0, rely=1.0, x=-70, y=-70, anchor="se")
        self.minimap_canvas.bind("<ButtonPress-1>", self.on_minimap_click)


        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Helvetica", 10))

        # Startet den I/O-Ladevorgang asynchron
        self.load_items_on_canvas()

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        self._bind_zoom_events()

        self.start_auto_refresh()

    # --- MULTICORE & ERROR FIX ---

    def _process_item_data(self, item):
        """Worker-Funktion, die in einem Hintergrund-Thread läuft. Führt I/O-Prüfungen durch."""
        if item.get("type") == "heading":
            return {"item": item, "is_source": False, "favicon_path": None}

        favicon_path = None
        if item.get("favicon"):
            check_path = Path(self.project["path"]) / "images" / item["favicon"]
            if check_path.exists():
                favicon_path = check_path 
        
        return {"item": item, "is_source": True, "favicon_path": favicon_path}


    def load_items_on_canvas(self):
        """Startet den synchronisierten Ladevorgang."""
        items_to_process = self.project["data"]["items"]
        threading.Thread(target=self._concurrent_load_worker, args=(items_to_process,), daemon=True).start()
        
    def _concurrent_load_worker(self, items_to_process):
        """Blockiert im Hintergrund, um alle I/O-Aufgaben gleichzeitig zu erledigen."""
        try:
            processed_results = list(self.executor.map(self._process_item_data, items_to_process))
            
            if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
                self.root.after(0, self._create_all_cards_in_gui_thread, processed_results)
            
        except concurrent.futures.CancelledError:
            pass 
        except Exception as e:
            print(f"Fehler im Concurrent Load Worker: {e}")
            if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
                self.root.after(0, lambda: messagebox.showerror("Fehler", "Fehler beim parallelen Laden der Kartendaten."))


    def _create_all_cards_in_gui_thread(self, processed_results):
        """Erstellt die Widgets aller Karten schnell und sequenziell im Main-Thread."""
        
        # Alte Karten löschen
        for frame, item_id in list(self.source_frames.values()):
            self.canvas.delete(item_id)
            frame.destroy()
        self.source_frames.clear()
        self.card_widgets.clear() 

        for result in processed_results:
            item = result["item"]
            if result["is_source"]:
                self._create_source_card_gui(item, result["favicon_path"])
            else:
                self._create_heading_card_gui(item)
                
        self.update_scrollregion()
        self._update_minimap() # NEU: Minimap nach dem Laden aktualisieren

    # --- COLOR HELPERS ---

    def _get_effective_bg_color(self, item):
        """Ermittelt die effektive Hintergrundfarbe: gewählte Farbe oder Theme-Standard."""
        custom_color = item.get("color", "").strip()
        if custom_color:
            return custom_color
        
        # Verwende Theme-abhängige Farben für unkolorierte Karten
        if item["type"] == "source":
            # Nutzt die Standard-Hintergrundfarbe des aktuellen Themes
            return self.app.style.lookup('TFrame', 'background') 
        else: # heading
            # Nutzt eine leicht abgedunkelte/aufgehellte Farbe des aktuellen Themes
            return self.app.style.lookup('TLabel', 'background')
    
    def _get_default_border_width(self, item):
        """Gibt die Standard-Randbreite basierend auf dem Item-Typ zurück."""
        return 2 if item["type"] == "source" else 0
        
    # --- ZOOM & SCALING ---

    def _bind_zoom_events(self):
        """Bindet plattformspezifische Mausrad-Events für das Zoomen."""
        self.canvas.bind("<MouseWheel>", self._on_mousewheel) 
        self.canvas.bind("<Button-4>", lambda event: self._on_mousewheel(event, up=True)) 
        self.canvas.bind("<Button-5>", lambda event: self._on_mousewheel(event, up=False)) 

    def _on_mousewheel(self, event, up=None):
        """Behandelt das Mausrad-Ereignis für das Zoomen."""
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
        """Skaliert den Canvas-Inhalt und aktualisiert den Zoom-Level."""
        new_zoom = self.zoom_level * factor
        
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return 

        self.canvas.scale("all", x, y, factor, factor)
        self.zoom_level = new_zoom
        
        self._update_card_content_scale()
        
        self.update_scrollregion()
        self._update_minimap() # NEU: Minimap aktualisieren
        
    def reset_zoom(self):
        """Setzt den Zoom-Level auf 1.0 zurück (NEU)."""
        if self.zoom_level == 1.0:
            return

        # Berechne den Skalierungsfaktor relativ zum Ursprung (0,0)
        factor = 1.0 / self.zoom_level
        self.canvas.scale("all", 0, 0, factor, factor)
        
        self.zoom_level = 1.0
        
        self._update_card_content_scale()
        self.update_scrollregion()
        self._update_minimap() # WICHTIG: Minimap aktualisieren

    def _update_card_content_scale(self):
        """Skaliert die Fonts und Bilder in allen Karten basierend auf dem Zoom-Level."""
        
        title_size = max(int(self.base_font_title[1] * self.zoom_level), 5)
        heading_size = max(int(self.base_font_heading[1] * self.zoom_level), 8)
        default_size = max(int(self.base_font_default[1] * self.zoom_level), 5)
        icon_size = max(int(self.base_icon_size * self.zoom_level), 10)
        
        for item_id, refs in self.card_widgets.items():
            
            # --- Fonts skalieren ---
            if 'title_label' in refs:
                refs['title_label'].config(font=("Helvetica", title_size, "bold"))
            if 'url_label' in refs:
                refs['url_label'].config(font=("Helvetica", default_size))
            if 'text_label' in refs:
                refs['text_label'].config(font=("Helvetica", default_size))
            if 'keywords_label' in refs:
                refs['keywords_label'].config(font=("Helvetica", default_size))
            if 'added_label' in refs:
                refs['added_label'].config(font=("Helvetica", max(int(8 * self.zoom_level), 5)))

            if 'heading_label' in refs:
                refs['heading_label'].config(font=("Helvetica", heading_size, "bold"))

            # --- Icon skalieren ---
            if 'icon_label' in refs:
                if 'original_icon_data' in refs and refs['original_icon_data']['is_favicon']:
                    original_img = refs['original_icon_data']['original_img']
                    new_subsample = max(1, int(self.base_favicon_subsample / self.zoom_level))
                    
                    try:
                        new_img = original_img.subsample(new_subsample, new_subsample)
                        refs['icon_label'].config(image=new_img)
                        refs['icon_label'].image = new_img
                    except tk.TclError:
                        pass 
                else:
                    refs['icon_label'].config(font=("Helvetica", icon_size))


    def _create_source_card_gui(self, source, favicon_path):
        """Erstellt die GUI-Elemente für eine Quelle (muss im Main-Thread sein)."""
        
        color = self._get_effective_bg_color(source)
        # NEU: Kontrastfarbe bestimmen
        text_color = get_contrast_color(color) 
        source["effective_color"] = color 
        item_id = source["id"]
        
        # FIX 1: Einzigartiger Style-Name, um die Hintergrundfarbe nur für diese Karte zu ändern
        style_name = f"Source.{item_id}.TFrame"
        self.card_widgets[item_id] = {}

        # 1. Style konfigurieren
        try:
             self.root.style.configure(style_name, background=color)
        except tk.TclError:
             self.root.style.configure(style_name, relief="raised", borderwidth=self._get_default_border_width(source))


        # 2. Frame erstellen und Style zuweisen
        # OPTIK: Erhöhe Padding für abgerundeten Look
        frame = ttk.Frame(self.canvas, padding="15")
        frame.item_data = source
        frame.unique_style_name = style_name 
        
        frame.configure(style=style_name)
        
        # OPTIK: Subtiler Schatten
        default_border = self._get_default_border_width(source)
        frame.config(relief="raised", borderwidth=default_border)

        # OPTIK: Hover-Effekt hinzufügen
        def on_enter(e, f=frame):
             # Erhöht den Rand leicht, um einen Schatteneffekt zu simulieren
             f.config(borderwidth=default_border + 1, relief="ridge") 
        def on_leave(e, f=frame):
             f.config(borderwidth=default_border, relief="raised") 
        
        
        # --- Favicon/Globus ---
        if favicon_path:
            try:
                original_img = tk.PhotoImage(file=favicon_path)
                self.card_widgets[item_id]['original_icon_data'] = {'original_img': original_img, 'is_favicon': True}
                favicon_img = original_img.subsample(self.base_favicon_subsample, self.base_favicon_subsample)
                # Verwende tk.Label, um die Hintergrundfarbe zu garantieren
                favicon_label = tk.Label(frame, image=favicon_img, bg=color) 
                favicon_label.image = favicon_img 
                favicon_label.pack(anchor="w")
                self.card_widgets[item_id]['icon_label'] = favicon_label
            except Exception:
                globe_label = tk.Label(frame, text="🌐", font=("Helvetica", self.base_icon_size), bg=color, fg=text_color)
                globe_label.pack(anchor="w")
                self.card_widgets[item_id]['icon_label'] = globe_label
        else:
            globe_label = tk.Label(frame, text="🌐", font=("Helvetica", self.base_icon_size), bg=color, fg=text_color)
            globe_label.pack(anchor="w")
            self.card_widgets[item_id]['icon_label'] = globe_label

        # --- Labels ---
        title_text = source.get("title") or source["url"]
        # OPTIK: Textfarbe auf Kontrast setzen
        title_label = ttk.Label(frame, text=title_text, font=self.base_font_title, foreground=text_color, wraplength=320)
        title_label.pack(anchor="w")
        self.card_widgets[item_id]['title_label'] = title_label

        if source.get("title"):
            # OPTIK: Textfarbe auf Kontrast setzen
            url_label = ttk.Label(frame, text=source["url"], font=self.base_font_default, foreground=text_color, wraplength=350)
            url_label.pack(anchor="w")
            self.card_widgets[item_id]['url_label'] = url_label

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            # OPTIK: Textfarbe auf Kontrast setzen
            text_label = ttk.Label(frame, text=f"📝 {preview}", font=self.base_font_default, foreground=text_color, wraplength=350)
            text_label.pack(anchor="w", pady=(6,0))
            self.card_widgets[item_id]['text_label'] = text_label

        if source["keywords"]:
            # OPTIK: Textfarbe auf Kontrast setzen
            keywords_label = ttk.Label(frame, text=f"🏷 {source['keywords']}", font=self.base_font_default, bootstyle="info", foreground=text_color)
            keywords_label.pack(anchor="w", pady=(4,0))
            self.card_widgets[item_id]['keywords_label'] = keywords_label

        # OPTIK: Textfarbe auf Kontrast setzen
        added_label = ttk.Label(frame, text=f"📅 {source['added']}", font=("Helvetica", 8), foreground=text_color)
        added_label.pack(anchor="w", pady=(8,0))
        self.card_widgets[item_id]['added_label'] = added_label 

        ttk.Button(frame, text="🔗 Original öffnen", bootstyle="success-outline", width=20,
                   command=lambda url=source["url"]: webbrowser.open(url)).pack(pady=(4,0))
        
        # --- Binden und Platzieren ---
        frame.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))
        frame.bind("<Enter>", on_enter) # Hover-Binding für Frame
        frame.bind("<Leave>", on_leave) # Hover-Binding für Frame

        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))
            # OPTIK: Hover-Binding für alle Kinder
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            
            # WICHTIG: Manuelle Konfiguration der Label-Hintergründe und Vordergründe 
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

        # 4. Selektionsstatus prüfen und anwenden (Initial-Load)
        if self.selected_source_id == item_id:
            self.select_card(item_id, initial_load=True) 
            
        if self.zoom_level != 1.0:
            self.canvas.scale(window_id, x, y, self.zoom_level, self.zoom_level)
            self._update_card_content_scale()


    def _create_heading_card_gui(self, heading):
        """Erstellt die GUI-Elemente für eine Überschrift (muss im Main-Thread sein)."""
        
        color = self._get_effective_bg_color(heading)
        # NEU: Kontrastfarbe bestimmen
        text_color = get_contrast_color(color) 
        heading["effective_color"] = color 
        
        item_id = heading["id"]
        
        # FIX 1: Einzigartiger Style-Name
        style_name = f"Heading.{item_id}.TFrame"
        
        self.card_widgets[item_id] = {}

        # 1. Style konfigurieren
        try:
             self.root.style.configure(style_name, background=color)
        except tk.TclError:
             self.root.style.configure(style_name, relief="flat", borderwidth=self._get_default_border_width(heading))

        # 2. Frame erstellen und Style zuweisen
        # OPTIK: Erhöhe Padding für schickeren Look
        frame = ttk.Frame(self.canvas, padding="15 20")
        frame.item_data = heading
        frame.unique_style_name = style_name 
        frame.configure(style=style_name)
        
        # OPTIK: Subtiler Schatten
        default_border = self._get_default_border_width(heading)
        frame.config(relief="flat", borderwidth=default_border)

        # OPTIK: Hover-Effekt hinzufügen
        def on_enter(e, f=frame):
             # Leichter Groove-Effekt bei Hover
             f.config(borderwidth=2, relief="groove")
        def on_leave(e, f=frame):
             f.config(borderwidth=default_border, relief="flat") 

        # OPTIK: Textfarbe auf Kontrast setzen
        # Verwende tk.Label, um die Hintergrundfarbe zu garantieren
        label = tk.Label(frame, text=heading["text"], font=self.base_font_heading, fg=text_color, bg=color)
        label.pack()
        self.card_widgets[item_id]['heading_label'] = label

        frame.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))
        frame.bind("<Enter>", on_enter) # Hover-Binding für Frame
        frame.bind("<Leave>", on_leave) # Hover-Binding für Frame
        
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))
            # OPTIK: Hover-Binding für alle Kinder
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)
            
            # WICHTIG: Manuelle Konfiguration der Label-Hintergründe und Vordergründe 
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
            self.select_card(item_id, initial_load=True) 

        if self.zoom_level != 1.0:
            self.canvas.scale(window_id, x, y, self.zoom_level, self.zoom_level)
            self._update_card_content_scale()
            
    # --- MINIMAP LOGIC (NEU) ---
    
    def _update_minimap(self):
        """Zeichnet alle Karten auf der Minimap und aktualisiert den Viewport-Rechteck."""
        
        if not self.minimap_canvas or not self.minimap_canvas.winfo_exists():
            return
            
        self.minimap_canvas.delete("all")
        
        # 1. Bestimme die Gesamtgröße des Inhalts
        # Ermittelt die Bounding Box aller Elemente auf dem Haupt-Canvas (bereits gezoomt)
        bbox_all = self.canvas.bbox("all") 
        if not bbox_all:
             self.viewport_rect_id = None
             self._update_minimap_viewport()
             return

        x1_main, y1_main, x2_main, y2_main = bbox_all
        # Füge einen kleinen Puffer hinzu
        buffer = 50 * self.zoom_level
        x1_main -= buffer
        y1_main -= buffer
        x2_main += buffer
        y2_main += buffer
        
        content_width = x2_main - x1_main
        content_height = y2_main - y1_main

        # 2. Skalierungsfaktor für Minimap bestimmen
        map_w = self.minimap_canvas.winfo_width()
        map_h = self.minimap_canvas.winfo_height()
        
        # Wähle den kleineren Faktor, um alles in die Minimap zu quetschen
        # Verwende 90% der verfügbaren Fläche
        if content_width > 0 and content_height > 0:
            scale_x = map_w / content_width
            scale_y = map_h / content_height
            minimap_scale = min(scale_x, scale_y) * 0.9 
        else:
            minimap_scale = 1.0 # Fallback
            
        # Berechne den Versatz, um den Inhalt in der Minimap zu zentrieren
        center_x_map = map_w / 2
        center_y_map = map_h / 2
        
        offset_x = center_x_map - (x1_main + content_width / 2) * minimap_scale
        offset_y = center_y_map - (y1_main + content_height / 2) * minimap_scale

        # 3. Karten zeichnen
        for item_id, (frame, window_id) in self.source_frames.items():
            item = frame.item_data
            
            coords = self.canvas.coords(window_id)
            if not coords: continue
            
            # Holen der aktuellen, skalierten Widget-Größe
            frame_width = frame.winfo_reqwidth()
            frame_height = frame.winfo_reqheight()

            # Skalierte Positionen auf der Minimap
            x_map_start = coords[0] * minimap_scale + offset_x
            y_map_start = coords[1] * minimap_scale + offset_y
            x_map_end = x_map_start + frame_width * minimap_scale
            y_map_end = y_map_start + frame_height * minimap_scale

            # Farbe verwenden
            color = item.get("effective_color", "#cccccc")
            outline_color = "#333333" if item["type"] == "source" else "" 
            
            self.minimap_canvas.create_rectangle(
                x_map_start, y_map_start, x_map_end, y_map_end,
                fill=color,
                outline=outline_color,
                width=1,
                tags=("card_rect", item_id) 
            )

        # Speichern der Skalierungs- und Versatzparameter für die Viewport-Berechnung
        self._minimap_params = {
            "x1_main": x1_main, "y1_main": y1_main, "x2_main": x2_main, "y2_main": y2_main,
            "minimap_scale": minimap_scale,
            "offset_x": offset_x, "offset_y": offset_y
        }
        
        # 4. Viewport-Rechteck zeichnen/aktualisieren
        self._update_minimap_viewport()

    def _update_minimap_viewport(self):
        """Aktualisiert das Viewport-Rechteck auf der Minimap."""
        
        if not self.minimap_canvas or not self.minimap_canvas.winfo_exists() or not hasattr(self, '_minimap_params'):
            return

        params = self._minimap_params
        minimap_scale = params["minimap_scale"]
        offset_x = params["offset_x"]
        offset_y = params["offset_y"]

        # Gezoomte Haupt-Canvas Koordinaten des oberen linken Ecks des Viewports
        x_start_zoomed = self.canvas.canvasx(0) 
        y_start_zoomed = self.canvas.canvasy(0)

        # Größe des Viewports in gezoomten Koordinaten
        viewport_w_zoomed = self.canvas.winfo_width()
        viewport_h_zoomed = self.canvas.winfo_height()

        # Skalierte Positionen auf der Minimap
        x_map_start = x_start_zoomed * minimap_scale + offset_x
        y_map_start = y_start_zoomed * minimap_scale + offset_y
        x_map_end = x_map_start + viewport_w_zoomed * minimap_scale
        y_map_end = y_map_start + viewport_h_zoomed * minimap_scale
        
        # 3. Rechteck zeichnen/aktualisieren
        if self.viewport_rect_id and self.minimap_canvas.find_withtag(self.viewport_rect_id):
            self.minimap_canvas.coords(self.viewport_rect_id, x_map_start, y_map_start, x_map_end, y_map_end)
            self.minimap_canvas.tag_raise(self.viewport_rect_id) 
        else:
            self.viewport_rect_id = self.minimap_canvas.create_rectangle(
                x_map_start, y_map_start, x_map_end, y_map_end,
                outline="#333333",
                fill="", 
                width=2,
                stipple="gray50" # Grau-durchsichtig-Effekt
            )

    def on_minimap_click(self, event):
        """Scrollt den Haupt-Canvas zur geklickten Position auf der Minimap."""
        
        if not hasattr(self, '_minimap_params'):
            return

        params = self._minimap_params
        minimap_scale = params["minimap_scale"]
        offset_x = params["offset_x"]
        offset_y = params["offset_y"]
        x1_main, y1_main, x2_main, y2_main = params["x1_main"], params["y1_main"], params["x2_main"], params["y2_main"]
        
        total_width = x2_main - x1_main
        total_height = y2_main - y1_main
        if total_width <= 0 or total_height <= 0: return # Schutz vor Division durch Null

        # 1. Klickposition auf der Minimap in Haupt-Canvas-Koordinaten umrechnen (gezoomt)
        target_x_zoomed = (event.x - offset_x) / minimap_scale
        target_y_zoomed = (event.y - offset_y) / minimap_scale
        
        # 2. Den Viewport so positionieren, dass der Klickpunkt im Zentrum ist.
        center_x_zoomed = self.canvas.winfo_width() / 2
        center_y_zoomed = self.canvas.winfo_height() / 2
        
        new_x_start_zoomed = target_x_zoomed - center_x_zoomed
        new_y_start_zoomed = target_y_zoomed - center_y_zoomed

        # 3. Scrolle den Canvas
        x_fraction = (new_x_start_zoomed - x1_main) / total_width
        y_fraction = (new_y_start_zoomed - y1_main) / total_height
        
        # Begrenze die Fraktionen auf [0, 1] 
        x_fraction = max(0.0, min(1.0, x_fraction))
        y_fraction = max(0.0, min(1.0, y_fraction))

        self.canvas.xview_moveto(x_fraction)
        self.canvas.yview_moveto(y_fraction)
        
        self._update_minimap_viewport()

    # --- WEITERE METHODEN ---

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
        """Startet den Reload-Prozess in einem Hintergrund-Thread."""
        threading.Thread(target=self._reload_worker, args=(source,), daemon=True).start()

    def _reload_worker(self, source):
        """Führt den Ladevorgang im Hintergrund-Thread (Netzwerk-I/O) aus."""
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
            if favicon_response.status_code == 200 and "image" in favicon_response.headers.get("Content-Type", ""):
                favicon_filename = f"favicon_{source['id']}_{timestamp}.ico"
                favicon_path = images_dir / favicon_filename
                with open(favicon_path, "wb") as f:
                    f.write(favicon_response.content)
                new_favicon_name = favicon_filename 

            self.root.after(0, self._finalize_reload, source["id"], filename, timestamp, new_favicon_name)

        except requests.exceptions.Timeout:
            self.root.after(0, lambda: messagebox.showerror("Fehler", "Download-Timeout: Die Seite hat zu lange gebraucht.", parent=self.root))
        except requests.exceptions.RequestException as e:
            self.root.after(0, lambda: messagebox.showerror("Fehler", f"Download-Fehler: {e}", parent=self.root))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}", parent=self.root))

    def _finalize_reload(self, source_id, filename, timestamp, new_favicon_name):
        """Führt UI-Updates und Speicherung im Main-Thread aus."""
        source = next((item for item in self.project["data"].get("items", []) if item.get("id") == source_id and item.get("type") == "source"), None)
        
        if not source:
            messagebox.showerror("Fehler", "Quelle zum Aktualisieren nicht im Projekt gefunden.", parent=self.root)
            return

        if "saved_pages" not in source:
            source["saved_pages"] = []
            
        source["saved_pages"].append({
            "file": filename,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if new_favicon_name:
            source["favicon"] = new_favicon_name

        self.save_project()
        
        # Visuelles Update der Karte (neu erstellen)
        if source_id in self.source_frames:
            frame, item_id = self.source_frames[source_id]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[source_id]
            del self.card_widgets[source_id] 
            
            threading.Thread(target=self._concurrent_reload_single_card, args=(source,), daemon=True).start()
            

    def _concurrent_reload_single_card(self, source):
        """Worker für das Neuladen einer einzelnen Karte."""
        try:
            result = self._process_item_data(source)
            self.root.after(0, self._create_source_card_gui, source, result["favicon_path"])
        except Exception as e:
            print(f"Fehler beim Neuladen der Einzelkarte: {e}")

    def show_context_menu(self, event, item):
        self.context_menu.delete(0, tk.END)
        self.context_menu.add_command(label="Löschen", command=lambda: self.delete_item(item))
        
        if item["type"] == "heading":
            self.context_menu.add_command(label="Umbenennen", command=lambda: self.rename_heading(item))
            self.context_menu.add_command(label="Farbe ändern", command=lambda: self.change_heading_color(item))
        else:
            if item.get("saved_pages") and len(item["saved_pages"]) > 0:
                self.context_menu.add_command(label="Gespeicherte Versionen anzeigen", command=lambda: self.show_saved_pages_popup(item)) 
                self.context_menu.add_separator() 
                
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
            del self.card_widgets[heading["id"]]
            self._create_heading_card_gui(heading) 
            self.save_project()
            self.update_last_mtime()
            self._update_minimap()

    def change_heading_color(self, heading):
        color = colorchooser.askcolor(title="Farbe wählen", initialcolor=heading["color"] or self.DEFAULT_HEADING_BG)[1]
        
        if color and color != heading.get("color", ""):
            heading["color"] = "" if color == self.DEFAULT_HEADING_BG else color
            
            frame, item_id = self.source_frames[heading["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[heading["id"]]
            del self.card_widgets[heading["id"]]
            self._create_heading_card_gui(heading) 
            self.save_project()
            self.update_last_mtime()
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
            if self.selected_source_id == item_id:
                self.deselect_card()
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
            self._update_minimap()

    def add_heading(self):
        text = simpledialog.askstring("Überschrift hinzufügen", "Text der Überschrift:", parent=self.root)
        if not text:
            return

        color = colorchooser.askcolor(title="Farbe wählen", initialcolor=self.DEFAULT_HEADING_BG)[1]
        
        color_to_save = "" if not color or color == self.DEFAULT_HEADING_BG else color

        new_heading = {
            "id": str(uuid.uuid4()),
            "type": "heading",
            "text": text,
            "color": color_to_save,
            "pos_x": 300,
            "pos_y": 300
        }

        self.project["data"]["items"].append(new_heading)
        self._create_heading_card_gui(new_heading) 
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self._update_minimap()

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
            
            threading.Thread(target=self._concurrent_reload_single_card, args=(new_source,), daemon=True).start()
            
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
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
            self._update_minimap()

    # --- SELECTION LOGIC ---
    
    def select_card(self, source_id, initial_load=False):
        """Wählt eine Karte aus und wendet den Auswahl-Border an."""
        
        # Deselektiere die vorherige Karte, um den Border zu entfernen
        if self.selected_source_id and self.selected_source_id != source_id:
            self.deselect_card()

        frame = self.source_frames[source_id][0]
        item = frame.item_data
        
        # Speichere die ursprüngliche Farbe, falls noch nicht geschehen
        if not self.selected_card_original_color:
            self.selected_card_original_color = item.get('effective_color')

        self.selected_source_id = source_id
        
        # Hole die Kontrastfarbe der Originalfarbe, da der primary-Bootstyle 
        # eine eigene Textfarbe mitbringt, die wir nicht wollen.
        text_color = get_contrast_color(self.selected_card_original_color)

        # Wende den 'primary' Bootstyle für den Rand an und setze den dicken Rand
        frame.config(
            borderwidth=self.DEFAULT_SELECT_BORDER_WIDTH, 
            bootstyle=self.DEFAULT_SELECT_BORDER_COLOR, # Primary Bootstyle für Randfarbe
            relief="raised" 
        )
        
        # Setze die Label-Hintergründe und -Vordergründe explizit
        for child in frame.winfo_children():
            try:
                if isinstance(child, (ttk.Label, tk.Label)):
                    child.config(background=self.selected_card_original_color, foreground=text_color)
            except Exception:
                pass


    def deselect_card(self):
        """Deselektiert die aktuelle Karte, entfernt den Border und stellt die Originalfarbe wieder her."""
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            frame = self.source_frames[self.selected_source_id][0]
            item = frame.item_data
            
            # 1. Ursprünglichen Rand wiederherstellen
            border = self._get_default_border_width(item)
            
            # 2. Ursprüngliche Hintergrundfarbe wiederherstellen (verwenden des einzigartigen Style-Namens)
            original_style_name = frame.unique_style_name
            original_color = item.get('effective_color')
            
            # Kontrastfarbe für Labels
            text_color = get_contrast_color(original_color)
            
            # Konfiguriert den ursprünglichen Style mit der Originalfarbe
            self.root.style.configure(original_style_name, background=original_color) 
            
            # Setzt den Frame auf den ursprünglichen Style zurück und entfernt den Bootstyle/Rand
            frame.configure(
                style=original_style_name, 
                bootstyle=None, # Wichtig, um den Primary-Bootstyle zu entfernen
                borderwidth=border,
                relief="raised" if item["type"] == "source" else "flat"
            )
            
            # Setze die Label-Hintergründe auf die Originalfarbe zurück
            for child in frame.winfo_children():
                try:
                    if isinstance(child, (ttk.Label, tk.Label)):
                        child.config(background=original_color, foreground=text_color)
                except Exception:
                    pass
            
        self.selected_source_id = None
        self.selected_card_original_color = None

    def on_card_press(self, event, item_id):
        if item_id != self.selected_source_id:
            self.select_card(item_id) 

        self.dragging_card = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.canvas.tag_raise(self.source_frames[item_id][1])

    def on_card_motion(self, event):
        if self.dragging_card:
            dx = (event.x_root - self.drag_start_x) / self.zoom_level
            dy = (event.y_root - self.drag_start_y) / self.zoom_level
            
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
            self._update_minimap() # NEU: Minimap aktualisieren

    def on_canvas_press(self, event):
        # FIX: Vergrößere den Suchbereich, um sicherzustellen, dass nur direkte Klicks auf Karten 
        # die Bewegung des Canvas verhindern.
        
        # Konvertiere Mauskoordinaten zu Canvas-Koordinaten
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # Verwende einen kleinen, aber angemessenen Radius (z.B. 2 Pixel)
        search_radius = 2 
        
        items = self.canvas.find_overlapping(x - search_radius, y - search_radius, x + search_radius, y + search_radius)
        
        card_items = [wid for _, wid in self.source_frames.values()]
        
        # Prüfe, ob das Event (Mausklick) auf einem Karten-Element (window) stattfand
        if any(item in card_items for item in items):
            # Es wurde eine Karte getroffen -> Canvas-Verschiebung verhindern
            return

        # Keine Karte wurde getroffen -> Canvas-Verschiebung erlauben
        self.dragging_canvas = True
        self.canvas_start_x = event.x
        self.canvas_start_y = event.y
        self.canvas.config(cursor="fleur")

    def on_canvas_motion(self, event):
        if self.dragging_canvas:
            # FIX 3: Dämpfungsfaktor (z.B. 0.7) für weniger aggressives Scrollen
            damping = 0.7 
            dx = int((event.x - self.canvas_start_x) * damping)
            dy = int((event.y - self.canvas_start_y) * damping)
            
            # xview_scroll verwendet die definierten Scroll-Einheiten. 
            # Mit int(dx*damping) wird der Scrollweg reduziert.
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            self.canvas_start_x = event.x
            self.canvas_start_y = event.y
            
            # NEU: Minimap Viewport aktualisieren
            self._update_minimap_viewport()

    def on_canvas_release(self, event):
        if self.dragging_canvas:
            self.dragging_canvas = False
            self.canvas.config(cursor="")
            self.update_scrollregion() # Nach dem Verschieben Scrollregion aktualisieren (wg. padding)

    def create_citation(self, source):
        citation = f"{source['url']}, zuletzt aufgerufen am {source['added']}"
        pyperclip.copy(citation)
        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")

    def update_scrollregion(self):
        """Aktualisiert die Scrollregion und fügt Polsterung hinzu, um das Scrollen in leere Bereiche zu ermöglichen (NEU)."""
        self.canvas.update_idletasks()
        
        bbox = self.canvas.bbox("all")
        
        if bbox:
            # Füge Polsterung (z.B. 500px) hinzu, um Scrollen in den leeren Hintergrund zu ermöglichen
            padding = 500
            x1, y1, x2, y2 = bbox
            new_scrollregion = (
                x1 - padding, 
                y1 - padding, 
                x2 + padding, 
                y2 + padding
            )
            self.canvas.configure(scrollregion=new_scrollregion)
        else:
            # Standardmäßig eine Mindest-Scrollregion, falls keine Elemente vorhanden sind
            self.canvas.configure(scrollregion=(-500, -500, 1000, 1000))
            
        # Wenn die Scrollregion aktualisiert wird, muss auch die Minimap neu gezeichnet werden.
        # Dies wird hier aufgerufen, da die bbox sich ändern kann.
        self._update_minimap()

    def save_project(self):
        self.project["data"]["canvas_zoom_level"] = self.zoom_level 
        
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

            self.zoom_level = updated_data.get("canvas_zoom_level", 1.0)
            
            items = updated_data.get("items", [])
            self.project["data"]["items"] = items
            
            self.project["data"]["canvas_zoom_level"] = self.zoom_level

            self.load_items_on_canvas()
            
        except Exception as e:
            print("Reload-Fehler:", e)
    
    def back_to_projects(self):
        self.save_project()
        self.executor.shutdown(wait=False) 
        self.main_frame.destroy()
        self.app.close_project()