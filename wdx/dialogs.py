import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import pyperclip
from ttkbootstrap.constants import *

class SourceDialog(tk.Toplevel):
    def __init__(self, parent, project_window, source=None):
        super().__init__(parent)
        self.project_window = project_window
        self.source = source or {}
        self.result = None
        self.title("Quelle bearbeiten" if source else "Neue Quelle hinzufügen")
        self.geometry("550x890")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.iconbitmap("icon128.ico")

        main = ttk.Frame(self, padding="20")
        main.pack(fill="both", expand=True)

        # --- URL ---
        url_frame = ttk.Frame(main)
        url_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(url_frame, text="URL:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        
        url_entry_frame = ttk.Frame(url_frame)
        url_entry_frame.pack(fill="x")
        self.url_var = tk.StringVar(value=self.source.get("url", ""))
        self.url_entry = ttk.Entry(url_entry_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side="left", fill="x", expand=True)
        
        paste_btn = ttk.Button(url_entry_frame, text="📋", width=3, command=self.paste_clipboard)
        paste_btn.pack(side="right", padx=(5, 0))

        # --- Titel ---
        ttk.Label(main, text="Titel:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.title_var = tk.StringVar(value=self.source.get("title", ""))
        self.title_entry = ttk.Entry(main, textvariable=self.title_var)
        self.title_entry.pack(fill="x", pady=(0, 10))

        # --- Text ---
        ttk.Label(main, text="Text:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        text_frame = ttk.Frame(main)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.text_text = tk.Text(text_frame, height=10, wrap="word")
        self.text_text.pack(fill="both", expand=True)
        self.text_text.insert("1.0", self.source.get("text", ""))

        # --- Schlagworte ---
        ttk.Label(main, text="Schlagworte:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.keywords_var = tk.StringVar(value=self.source.get("keywords", ""))
        self.keywords_entry = ttk.Entry(main, textvariable=self.keywords_var)
        self.keywords_entry.pack(fill="x", pady=(0, 10))

        # --- Farbe ---
        ttk.Label(main, text="Farbe:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        color_frame = ttk.Frame(main)
        color_frame.pack(fill="x", pady=(0, 15))
        self.color_var = tk.StringVar(value=self.source.get("color", "#ffffff"))
        self.selected_color_swatch = tk.Label(color_frame, bg=self.color_var.get(), width=3, relief="solid", borderwidth=1)
        self.selected_color_swatch.pack(side="left", padx=(0, 5))
        ttk.Entry(color_frame, textvariable=self.color_var, width=15).pack(side="left")
        ttk.Button(color_frame, text="Wählen", command=self.choose_color).pack(side="left", padx=(5, 0))
        self.color_var.trace_add("write", self.update_color_swatch)

        # --- Palette (bestehende Farben) ---
        all_items = project_window.project["data"].get("items", [])
        used_colors = list({item.get("color").strip() for item in all_items if item.get("color") and item.get("color").strip()})

        if used_colors:
            ttk.Label(main, text="Bereits verwendete Farben:", font=("Helvetica", 9)).pack(anchor="w")
            palette = ttk.Frame(main)
            palette.pack(fill="x", pady=(0, 15))
            for col in used_colors:
                lbl = tk.Label(palette, width=3, height=1, relief="flat", borderwidth=1, cursor="hand2", highlightbackground="#AAAAAA", highlightthickness=1)
                lbl.config(bg=col)
                lbl.bind("<Button-1>", lambda e, c=col: self.color_var.set(c))
                lbl.pack(side="left", padx=2)

        # --- Bindings & Buttons ---
        self.setup_bindings()

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy, bootstyle="secondary-outline").pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Speichern", command=self.save, bootstyle="primary", width=15).pack(side="right")
        
        #self.url_entry.focus_set()
        self.text_text.focus_set()
        self.wait_window()

    def update_color_swatch(self, *args):
        color = self.color_var.get().strip()
        if color:
            try:
                self.selected_color_swatch.config(bg=color)
            except tk.TclError:
                pass

    def paste_clipboard(self):
        try:
            clip = pyperclip.paste()
            if clip:
                self.url_var.set(clip.strip())
        except:
            pass

    def choose_color(self):
        result = colorchooser.askcolor(initialcolor=self.color_var.get())
        if result and result[1]:
            self.color_var.set(result[1])

    def save(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Fehler", "URL ist erforderlich!")
            return
        self.result = {
            "url": url,
            "title": self.title_var.get().strip(),
            "text": self.text_text.get("1.0", "end").strip(),
            "keywords": self.keywords_var.get().strip(),
            "color": self.color_var.get().strip() or "#ffffff",
        }
        self.destroy()
        
        
    def setup_bindings(self):
        self.bind("<Control-Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())
        
        widgets = [self.url_entry, self.title_entry, self.text_text, self.keywords_entry]
        for w in widgets:
            # Strg + Entf (Wort rechts löschen)
            w.bind("<Control-Delete>", self.delete_word_forward)
            w.bind("<Control-KP_Delete>", self.delete_word_forward)
            # Strg + Rücktaste (Wort links löschen)
            w.bind("<Control-BackSpace>", self.delete_word_backward)
            w.bind("<Control-Key-BackSpace>", self.delete_word_backward)

    def delete_word_forward(self, event):
        widget = event.widget
        # "insert wordend" findet das Ende des aktuellen Wortes ab Cursor
        widget.delete("insert", "insert wordend")
        return "break"

    def delete_word_backward(self, event):
        widget = event.widget
        # "insert-1c wordstart" findet den Anfang des Wortes vor dem Cursor
        widget.delete("insert wordstart", "insert")
        return "break"