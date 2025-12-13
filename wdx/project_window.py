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

class ProjectWindow:
    def __init__(self, root, project, app):
        self.project = project
        self.root = root
        self.app = app
        self.source_frames = {} # Speichert (Frame, Canvas_ID)
        self.card_widgets = {}  # Speichert Widget-Referenzen für dynamische Skalierung: {id: {label_ref: ..., original_font_size: ...}}
        self.selected_source_id = None
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
        self.zoom_level = 1.0
        self.max_zoom = 2.0
        self.min_zoom = 0.5
        self.zoom_factor = 1.2 
        # Basis-Fonts für Skalierung
        self.base_font_title = ("Helvetica", 12, "bold")
        self.base_font_heading = ("Helvetica", 16, "bold")
        self.base_font_default = ("Helvetica", 9)
        self.base_icon_size = 20 # Font size for default globe icon
        self.base_favicon_subsample = 2 # Original subsample factor for favicons

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
        original_favicon_img = None
        if item.get("favicon"):
            check_path = Path(self.project["path"]) / "images" / item["favicon"]
            if check_path.exists():
                favicon_path = check_path 
                # Das PhotoImage Objekt MUSS im Main-Thread erstellt werden. 
                # Wir geben nur den Pfad zurück.
        
        return {"item": item, "is_source": True, "favicon_path": favicon_path}


    def load_items_on_canvas(self):
        """Startet den synchronisierten Ladevorgang."""
        items_to_process = self.project["data"]["items"]
        threading.Thread(target=self._concurrent_load_worker, args=(items_to_process,), daemon=True).start()
        
    def _concurrent_load_worker(self, items_to_process):
        """Blockiert im Hintergrund, um alle I/O-Aufgaben gleichzeitig zu erledigen."""
        try:
            processed_results = list(self.executor.map(self._process_item_data, items_to_process))
            
            # Nachdem alle Ergebnisse gesammelt sind, zurück in den Main-Thread
            if hasattr(self, 'main_frame') and self.main_frame.winfo_exists():
                self.root.after(0, self._create_all_cards_in_gui_thread, processed_results)
            
        except concurrent.futures.CancelledError:
            # FIX: Fehler wird stumm geschaltet, da dies beim Executor-Shutdown erwartet wird
            pass 
        except Exception as e:
            # Nur unerwartete Fehler anzeigen, wenn das Fenster noch existiert
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
        self.card_widgets.clear() # Wichtig: Skalierungs-Cache leeren

        for result in processed_results:
            item = result["item"]
            if result["is_source"]:
                self._create_source_card_gui(item, result["favicon_path"])
            else:
                self._create_heading_card_gui(item)
                
        # Scrollregion nur einmal am Ende aktualisieren
        self.update_scrollregion()

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

        # Skaliert Positionen und Bounding Boxes der Canvas-Elemente
        self.canvas.scale("all", x, y, factor, factor)
        self.zoom_level = new_zoom
        
        # Manuell die Inhalte (Fonts/Bilder) der Karten skalieren
        self._update_card_content_scale()
        
        self.update_scrollregion()

    def _update_card_content_scale(self):
        """Skaliert die Fonts und Bilder in allen Karten basierend auf dem Zoom-Level."""
        
        # Berechnet die neuen Font-Größen (mit Minimum 5, um Lesbarkeit zu gewährleisten)
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
                refs['added_label'].config(font=("Helvetica", default_size))

            if 'heading_label' in refs:
                refs['heading_label'].config(font=("Helvetica", heading_size, "bold"))

            # --- Icon skalieren ---
            if 'icon_label' in refs:
                # Prüfen, ob es ein Favicon oder ein Globus ist
                if 'original_icon_data' in refs and refs['original_icon_data']['is_favicon']:
                    # Favicon: Muss neu gesampled werden
                    original_img = refs['original_icon_data']['original_img']
                    new_subsample = max(1, int(self.base_favicon_subsample / self.zoom_level))
                    
                    # WICHTIG: Tkinter speichert PhotoImage-Referenzen. 
                    # Wir müssen die Referenz des Labels aktualisieren.
                    try:
                        new_img = original_img.subsample(new_subsample, new_subsample)
                        refs['icon_label'].config(image=new_img)
                        refs['icon_label'].image = new_img
                    except tk.TclError:
                        # Kann bei extremen Zoom-Werten passieren
                        pass 
                else:
                    # Globus-Icon (Text)
                    refs['icon_label'].config(font=("Helvetica", icon_size))


    def _create_source_card_gui(self, source, favicon_path):
        """Erstellt die GUI-Elemente für eine Quelle (muss im Main-Thread sein)."""
        color = source.get("color", DEFAULT_COLOR)
        item_id = source["id"]
        
        # Initialisiert den Widget-Speicher für diese Karte
        self.card_widgets[item_id] = {}

        frame = ttk.Frame(self.canvas, padding="15", relief="raised", borderwidth=2)
        frame.item_data = source
        frame.configure(style="Card.TFrame")
        self.root.style.configure("Card.TFrame", background=color)
        frame.configure(style="Card.TFrame")

        # --- Favicon/Globus ---
        if favicon_path:
            try:
                # PhotoImage MUSS im Main-Thread erstellt werden
                original_img = tk.PhotoImage(file=favicon_path)
                
                # Speichere das Originalbild und den initialen subsample-Faktor
                self.card_widgets[item_id]['original_icon_data'] = {
                    'original_img': original_img,
                    'is_favicon': True
                }
                
                # Erstellt das Label mit dem initial gesampelten Bild (entspricht zoom_level=1.0)
                favicon_img = original_img.subsample(self.base_favicon_subsample, self.base_favicon_subsample)
                favicon_label = ttk.Label(frame, image=favicon_img, background=color)
                favicon_label.image = favicon_img # Wichtig: Referenz halten
                favicon_label.pack(anchor="w")
                self.card_widgets[item_id]['icon_label'] = favicon_label
            except Exception:
                # Falls das Bild defekt ist, auf Globus zurückfallen
                globe_label = ttk.Label(frame, text="🌐", font=("Helvetica", self.base_icon_size), background=color)
                globe_label.pack(anchor="w")
                self.card_widgets[item_id]['icon_label'] = globe_label
        else:
            globe_label = ttk.Label(frame, text="🌐", font=("Helvetica", self.base_icon_size), background=color)
            globe_label.pack(anchor="w")
            self.card_widgets[item_id]['icon_label'] = globe_label

        # --- Labels ---
        title_text = source.get("title") or source["url"]
        title_label = ttk.Label(frame, text=title_text, font=self.base_font_title, foreground="#2c3e50", wraplength=320, background=color)
        title_label.pack(anchor="w")
        self.card_widgets[item_id]['title_label'] = title_label

        if source.get("title"):
            url_label = ttk.Label(frame, text=source["url"], font=self.base_font_default, foreground="#7f8c8d", wraplength=350, background=color)
            url_label.pack(anchor="w")
            self.card_widgets[item_id]['url_label'] = url_label

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            text_label = ttk.Label(frame, text=f"📝 {preview}", font=self.base_font_default, foreground="#34495e", wraplength=350, background=color)
            text_label.pack(anchor="w", pady=(6,0))
            self.card_widgets[item_id]['text_label'] = text_label

        if source["keywords"]:
            keywords_label = ttk.Label(frame, text=f"🏷 {source['keywords']}", font=self.base_font_default, bootstyle="info", background=color)
            keywords_label.pack(anchor="w", pady=(4,0))
            self.card_widgets[item_id]['keywords_label'] = keywords_label

        added_label = ttk.Label(frame, text=f"📅 {source['added']}", font=("Helvetica", 8), foreground="#95a5a6", background=color)
        added_label.pack(anchor="w", pady=(8,0))
        self.card_widgets[item_id]['added_label'] = added_label # Speichern, auch wenn nicht im base_font_default

        # Buttons ... (werden nicht skaliert)

        ttk.Button(frame, text="🔗 Original öffnen", bootstyle="success-outline", width=20,
                   command=lambda url=source["url"]: webbrowser.open(url)).pack(pady=(4,0))
        
        # --- Binden und Platzieren ---
        frame.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=source: self.show_context_menu(e, i))

        frame.bind("<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = source.get("pos_x", 300), source.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[item_id] = (frame, window_id)

        if self.selected_source_id == item_id:
            frame.config(borderwidth=5, bootstyle="primary")
        else:
            frame.config(borderwidth=2, bootstyle=None)
            
        # Skaliert die neue Karte, falls bereits gezoomt wurde
        if self.zoom_level != 1.0:
            self.canvas.scale(window_id, x, y, self.zoom_level, self.zoom_level)
            # Wichtig: Inhalt manuell skalieren, da die Karte neu erstellt wurde
            self._update_card_content_scale()


    def _create_heading_card_gui(self, heading):
        """Erstellt die GUI-Elemente für eine Überschrift (muss im Main-Thread sein)."""
        color = heading.get("color", "#e9ecef")
        text_color = "#212529" if color == "#e9ecef" else "#ffffff"
        item_id = heading["id"]
        
        self.card_widgets[item_id] = {}

        frame = ttk.Frame(self.canvas, padding="20", relief="flat", borderwidth=0)
        frame.item_data = heading
        frame.configure(style="Heading.TFrame")
        self.root.style.configure("Heading.TFrame", background=color)
        frame.configure(style="Heading.TFrame")

        label = ttk.Label(frame, text=heading["text"], font=self.base_font_heading, foreground=text_color, background=color)
        label.pack()
        self.card_widgets[item_id]['heading_label'] = label

        frame.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))
        for child in frame.winfo_children():
            child.bind("<Button-3>", lambda e, i=heading: self.show_context_menu(e, i))

        frame.bind("<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = heading.get("pos_x", 300), heading.get("pos_y", 300)
        window_id = self.canvas.create_window(x, y, window=frame, anchor="nw")
        self.source_frames[item_id] = (frame, window_id)

        if self.selected_source_id == item_id:
            frame.config(borderwidth=5, bootstyle="primary")
        else:
            frame.config(borderwidth=0, bootstyle=None)

        if self.zoom_level != 1.0:
            self.canvas.scale(window_id, x, y, self.zoom_level, self.zoom_level)
            self._update_card_content_scale()
    
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
        # ... (Methoden-Code unverändert) ...
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
        """Startet den Reload-Prozess in einem Hintergrund-Thread."""
        self.root.after(0, lambda: messagebox.showinfo("Info", "Seite wird im Hintergrund aktualisiert...", parent=self.root))
        
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
            del self.card_widgets[source_id] # Widget-Cache löschen
            
            # Startet asynchrone I/O-Vorbereitung und anschließende GUI-Erstellung
            threading.Thread(target=self._concurrent_reload_single_card, args=(source,), daemon=True).start()


        messagebox.showinfo("Erfolg", "Aktuelle Seite wurde neu gespeichert!", parent=self.root)

    def _concurrent_reload_single_card(self, source):
        """Worker für das Neuladen einer einzelnen Karte."""
        try:
            # Führt die I/O-Prüfung aus
            result = self._process_item_data(source)
            # Führt die GUI-Erstellung im Main-Thread aus
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

    def change_heading_color(self, heading):
        color = colorchooser.askcolor(title="Farbe wählen", initialcolor=heading["color"])[1]
        if color and color != heading["color"]:
            heading["color"] = color
            frame, item_id = self.source_frames[heading["id"]]
            self.canvas.delete(item_id)
            frame.destroy()
            del self.source_frames[heading["id"]]
            del self.card_widgets[heading["id"]]
            self._create_heading_card_gui(heading) 
            self.save_project()
            self.update_last_mtime()

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
        self._create_heading_card_gui(new_heading) 
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
            
            threading.Thread(target=self._concurrent_reload_single_card, args=(new_source,), daemon=True).start()
            
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
            
            item_id = source["id"]
            frame, item_id_canvas = self.source_frames[item_id]
            self.canvas.delete(item_id_canvas)
            frame.destroy()
            del self.source_frames[item_id]
            del self.card_widgets[item_id]
            
            threading.Thread(target=self._concurrent_reload_single_card, args=(source,), daemon=True).start()
            
            self.save_project()
            self.update_last_mtime()

    def select_card(self, source_id):
        # ... (Methoden-Code unverändert) ...
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            old_frame = self.source_frames[self.selected_source_id][0]
            border = 2 if old_frame.item_data["type"] == "source" else 0
            old_frame.config(borderwidth=border, bootstyle=None)

        self.selected_source_id = source_id
        frame = self.source_frames[source_id][0]
        frame.config(borderwidth=5, bootstyle="primary")

    def deselect_card(self):
        # ... (Methoden-Code unverändert) ...
        if self.selected_source_id and self.selected_source_id in self.source_frames:
            frame = self.source_frames[self.selected_source_id][0]
            border = 2 if frame.item_data["type"] == "source" else 0
            frame.config(borderwidth=border, bootstyle=None)
        self.selected_source_id = None

    def on_card_press(self, event, item_id):
        # ... (Methoden-Code unverändert) ...
        if item_id != self.selected_source_id:
            self.select_card(item_id)

        self.dragging_card = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.canvas.tag_raise(self.source_frames[item_id][1])

    def on_card_motion(self, event):
        # ... (Methoden-Code unverändert) ...
        if self.dragging_card:
            dx = (event.x_root - self.drag_start_x) / self.zoom_level
            dy = (event.y_root - self.drag_start_y) / self.zoom_level
            
            self.canvas.move(self.source_frames[self.selected_source_id][1], dx, dy)
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root

    def on_card_release(self, event):
        # ... (Methoden-Code unverändert) ...
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
        # ... (Methoden-Code unverändert) ...
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        card_items = [wid for _, wid in self.source_frames.values()]
        if any(item in card_items for item in items):
            return

        self.dragging_canvas = True
        self.canvas_start_x = event.x
        self.canvas_start_y = event.y
        self.canvas.config(cursor="fleur")

    def on_canvas_motion(self, event):
        # ... (Methoden-Code unverändert) ...
        if self.dragging_canvas:
            dx = event.x - self.canvas_start_x
            dy = event.y - self.canvas_start_y
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            self.canvas_start_x = event.x
            self.canvas_start_y = event.y

    def on_canvas_release(self, event):
        # ... (Methoden-Code unverändert) ...
        if self.dragging_canvas:
            self.dragging_canvas = False
            self.canvas.config(cursor="")

    def create_citation(self, source):
        # ... (Methoden-Code unverändert) ...
        citation = f"{source['url']}, zuletzt aufgerufen am {source['added']}"
        pyperclip.copy(citation)
        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")

    def update_scrollregion(self):
        # ... (Methoden-Code unverändert) ...
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def save_project(self):
        # ... (Methoden-Code unverändert) ...
        with open(self.project["data_file"], "w", encoding="utf-8") as f:
            json.dump(self.project["data"], f, indent=4)
        self.project["last_modified"] = datetime.datetime.now().isoformat()
        self.app.project_manager.save_projects()

    def start_auto_refresh(self):
        # ... (Methoden-Code unverändert) ...
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
        # ... (Methode unverändert - nutzt load_items_on_canvas) ...
        try:
            with open(self.project["data_file"], "r", encoding="utf-8") as f:
                updated_data = json.load(f)

            items = updated_data.get("items", [])
            self.project["data"]["items"] = items

            self.load_items_on_canvas()
            
        except Exception as e:
            print("Reload-Fehler:", e)

    def back_to_projects(self):
        self.save_project()
        # Wichtig: Thread-Pool sauber beenden (shutdown ohne wait=False, 
        # damit _concurrent_load_worker einen CancelledError wirft und stumm schaltet)
        self.executor.shutdown(wait=False) 
        self.main_frame.destroy()
        self.app.close_project()