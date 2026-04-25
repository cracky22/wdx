import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
import pyperclip
from ttkbootstrap.constants import *


class SourceDialog(tk.Toplevel):
    def __init__(self, parent, project_window, source=None):
        super().__init__(parent)
        self.project_window = project_window
        self.source = source or {}
        self.result = None
        self.title("Quelle bearbeiten" if source else "Neue Quelle hinzufügen")
        self.geometry("620x920")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        try:
            self.iconbitmap("icon128.ico")
        except Exception:
            pass

        main = ttk.Frame(self, padding="20")
        main.pack(fill="both", expand=True)

        url_frame = ttk.Frame(main)
        url_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(url_frame, text="URL:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        url_entry_frame = ttk.Frame(url_frame)
        url_entry_frame.pack(fill="x")
        self.url_var = tk.StringVar(value=self.source.get("url", ""))
        self.url_entry = ttk.Entry(url_entry_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(url_entry_frame, text="📋", width=3, command=self.paste_clipboard).pack(side="right", padx=(5, 0))

        ttk.Label(main, text="Titel:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.title_var = tk.StringVar(value=self.source.get("title", ""))
        self.title_entry = ttk.Entry(main, textvariable=self.title_var)
        self.title_entry.pack(fill="x", pady=(0, 10))

        text_header = ttk.Frame(main)
        text_header.pack(fill="x")
        ttk.Label(text_header, text="Text (Markdown):", font=("Helvetica", 10, "bold")).pack(side="left", anchor="w")
        ttk.Button(text_header, text="🖼 Bild einfügen", bootstyle="info-outline",
                   width=14, command=self._insert_image_markdown).pack(side="right")

        text_frame = ttk.Frame(main)
        text_frame.pack(fill="both", expand=True, pady=(4, 4))
        self.text_text = tk.Text(text_frame, height=10, wrap="word")
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_text.yview)
        self.text_text.configure(yscrollcommand=text_scroll.set)
        self.text_text.pack(side="left", fill="both", expand=True)
        text_scroll.pack(side="right", fill="y")
        self.text_text.insert("1.0", self.source.get("text", ""))
        ttk.Label(main,
                  text="Markdown wird im Reader (Strg+I) gerendert.  Bilder: ![Alt](pfad/bild.png)",
                  font=("Helvetica", 8), foreground="gray").pack(anchor="w", pady=(0, 6))

        ttk.Label(main, text="Schlagwörter:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.keywords_var = tk.StringVar(value=self.source.get("keywords", ""))
        self.keywords_entry = ttk.Entry(main, textvariable=self.keywords_var)
        self.keywords_entry.pack(fill="x", pady=(0, 10))

        ttk.Label(main, text="Farbe:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        color_frame = ttk.Frame(main)
        color_frame.pack(fill="x", pady=(0, 10))
        self.color_var = tk.StringVar(value=self.source.get("color", "#ffffff"))
        self.selected_color_swatch = tk.Label(color_frame, bg=self.color_var.get(),
                                               width=3, relief="solid", borderwidth=1)
        self.selected_color_swatch.pack(side="left", padx=(0, 5))
        ttk.Entry(color_frame, textvariable=self.color_var, width=15).pack(side="left")
        ttk.Button(color_frame, text="Farbwähler", command=self.choose_color).pack(side="left", padx=(5, 0))
        self.color_var.trace_add("write", self.update_color_swatch)

        all_items = project_window.project["data"].get("items", [])
        used_colors = list({item.get("color").strip() for item in all_items
                            if item.get("color") and item.get("color").strip()})
        if used_colors:
            ttk.Label(main, text="Bereits verwendete Farben:", font=("Helvetica", 9)).pack(anchor="w")
            palette = ttk.Frame(main)
            palette.pack(fill="x", pady=(0, 12))
            for col in used_colors:
                lbl = tk.Label(palette, width=3, height=1, relief="flat", borderwidth=1,
                               cursor="hand2", highlightbackground="#AAAAAA", highlightthickness=1)
                lbl.config(bg=col)
                lbl.bind("<Button-1>", lambda e, c=col: self.color_var.set(c))
                lbl.pack(side="left", padx=2)

        self.setup_bindings()

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy,
                   bootstyle="secondary-outline").pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Speichern", command=self.save,
                   bootstyle="primary", width=15).pack(side="right")

        self.text_text.focus_set()
        self.wait_window()

    def _insert_image_markdown(self):
        path = filedialog.askopenfilename(
            title="Bilddatei auswählen",
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg"),
                       ("Alle Dateien", "*.*")],
            parent=self,
        )
        if not path:
            return
        path_str = path.replace("\\", "/")
        snippet = f"![Bildbeschreibung]({path_str})"
        self.text_text.insert(tk.INSERT, snippet)
        self.text_text.focus_set()

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
        except Exception:
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
            w.bind("<Control-Delete>", self.delete_word_forward)
            w.bind("<Control-KP_Delete>", self.delete_word_forward)
            w.bind("<Control-BackSpace>", self.delete_word_backward)
            w.bind("<Control-Key-BackSpace>", self.delete_word_backward)

    def delete_word_forward(self, event):
        widget = event.widget
        if isinstance(widget, tk.Text):
            widget.delete("insert", "insert wordend")
        else:
            pos = widget.index(tk.INSERT)
            text = widget.get()
            end = pos
            while end < len(text) and text[end] == " ":
                end += 1
            while end < len(text) and text[end] != " ":
                end += 1
            widget.delete(pos, end)
        return "break"

    def delete_word_backward(self, event):
        widget = event.widget
        if isinstance(widget, tk.Text):
            widget.delete("insert -1c wordstart", "insert")
        else:
            pos = widget.index(tk.INSERT)
            text = widget.get()
            start = pos
            while start > 0 and text[start - 1] == " ":
                start -= 1
            while start > 0 and text[start - 1] != " ":
                start -= 1
            widget.delete(start, pos)
        return "break"


class HeadingDialog(tk.Toplevel):
    DEFAULT_HEADING_BG = "#e9ecef"

    def __init__(self, parent, heading=None):
        super().__init__(parent)
        self.heading = heading or {}
        self.result = None
        self.title("Überschrift bearbeiten" if heading else "Überschrift hinzufügen")
        self.geometry("400x250")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        try:
            self.iconbitmap("icon128.ico")
        except Exception:
            pass

        main = ttk.Frame(self, padding="20")
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Titel:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.text_var = tk.StringVar(value=self.heading.get("text", ""))
        self.text_entry = ttk.Entry(main, textvariable=self.text_var, width=45)
        self.text_entry.pack(fill="x", pady=(0, 15))

        ttk.Label(main, text="Farbe:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        color_frame = ttk.Frame(main)
        color_frame.pack(fill="x", pady=(0, 20))
        self.color_var = tk.StringVar(value=self.heading.get("color") or self.DEFAULT_HEADING_BG)
        self.color_swatch = tk.Label(color_frame, bg=self.color_var.get(), width=3,
                                      relief="solid", borderwidth=1)
        self.color_swatch.pack(side="left", padx=(0, 5))
        ttk.Entry(color_frame, textvariable=self.color_var, width=15).pack(side="left")
        ttk.Button(color_frame, text="Farbwähler", command=self.choose_color).pack(side="left", padx=(5, 0))
        self.color_var.trace_add("write", self.update_swatch)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy,
                   bootstyle="secondary-outline").pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Speichern", command=self.save,
                   bootstyle="primary", width=15).pack(side="right")

        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.text_entry.focus_set()
        self.wait_window()

    def update_swatch(self, *args):
        color = self.color_var.get().strip()
        if color:
            try:
                self.color_swatch.config(bg=color)
            except tk.TclError:
                pass

    def choose_color(self):
        result = colorchooser.askcolor(initialcolor=self.color_var.get())
        if result and result[1]:
            self.color_var.set(result[1])

    def save(self):
        text = self.text_var.get().strip()
        if not text:
            messagebox.showerror("Fehler", "Titel ist erforderlich!")
            return
        color = self.color_var.get().strip() or self.DEFAULT_HEADING_BG
        self.result = {
            "text": text,
            "color": "" if color == self.DEFAULT_HEADING_BG else color,
        }
        self.destroy()


class FileCardDialog(tk.Toplevel):
    """Dialog zum Bearbeiten der Metadaten einer Datei-Kachel."""

    DEFAULT_COLOR = "#e8f4fd"

    def __init__(self, parent, filename: str, existing: dict = None):
        super().__init__(parent)
        self.filename = filename
        self.existing = existing or {}
        self.result = None

        self.title("Datei bearbeiten" if existing else "Datei hinzufügen")
        self.geometry("520x560")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        try:
            self.iconbitmap("icon128.ico")
        except Exception:
            pass

        main = ttk.Frame(self, padding="20")
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Datei:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        ttk.Label(main, text=f"📎  {filename}",
                  font=("Helvetica", 10), foreground="gray").pack(anchor="w", pady=(2, 12))

        ttk.Label(main, text="Titel (optional):", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.title_var = tk.StringVar(value=self.existing.get("title", ""))
        self.title_entry = ttk.Entry(main, textvariable=self.title_var)
        self.title_entry.pack(fill="x", pady=(0, 12))

        text_header = ttk.Frame(main)
        text_header.pack(fill="x")
        ttk.Label(text_header, text="Notizen / Text (Markdown, optional):",
                  font=("Helvetica", 10, "bold")).pack(side="left", anchor="w")
        ttk.Button(text_header, text="🖼 Bild einfügen", bootstyle="info-outline",
                   width=14, command=self._insert_image_markdown).pack(side="right")

        text_frame = ttk.Frame(main)
        text_frame.pack(fill="both", expand=True, pady=(4, 4))
        self.text_text = tk.Text(text_frame, height=8, wrap="word")
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_text.yview)
        self.text_text.configure(yscrollcommand=text_scroll.set)
        self.text_text.pack(side="left", fill="both", expand=True)
        text_scroll.pack(side="right", fill="y")
        self.text_text.insert("1.0", self.existing.get("text", ""))
        ttk.Label(main, text="Im Reader (Strg+I) als formatierter Text sichtbar.",
                  font=("Helvetica", 8), foreground="gray").pack(anchor="w", pady=(0, 6))

        ttk.Label(main, text="Schlagwörter:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.keywords_var = tk.StringVar(value=self.existing.get("keywords", ""))
        self.keywords_entry = ttk.Entry(main, textvariable=self.keywords_var)
        self.keywords_entry.pack(fill="x", pady=(0, 12))

        ttk.Label(main, text="Kartenfarbe:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        color_frame = ttk.Frame(main)
        color_frame.pack(fill="x", pady=(0, 16))
        self.color_var = tk.StringVar(value=self.existing.get("color", self.DEFAULT_COLOR))
        self.color_swatch = tk.Label(color_frame, bg=self.color_var.get(),
                                      width=3, relief="solid", borderwidth=1)
        self.color_swatch.pack(side="left", padx=(0, 5))
        ttk.Entry(color_frame, textvariable=self.color_var, width=15).pack(side="left")
        ttk.Button(color_frame, text="Farbwähler", command=self.choose_color).pack(side="left", padx=(5, 0))
        self.color_var.trace_add("write", self._update_swatch)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_frame, text="Abbrechen", command=self.destroy,
                   bootstyle="secondary-outline").pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Speichern", command=self.save,
                   bootstyle="primary", width=15).pack(side="right")

        self.bind("<Control-Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.title_entry.focus_set()
        self.wait_window()

    def _insert_image_markdown(self):
        path = filedialog.askopenfilename(
            title="Bilddatei auswählen",
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg"),
                       ("Alle Dateien", "*.*")],
            parent=self,
        )
        if not path:
            return
        path_str = path.replace("\\", "/")
        snippet = f"![Bildbeschreibung]({path_str})"
        self.text_text.insert(tk.INSERT, snippet)
        self.text_text.focus_set()

    def _update_swatch(self, *args):
        color = self.color_var.get().strip()
        if color:
            try:
                self.color_swatch.config(bg=color)
            except tk.TclError:
                pass

    def choose_color(self):
        result = colorchooser.askcolor(initialcolor=self.color_var.get())
        if result and result[1]:
            self.color_var.set(result[1])

    def save(self):
        self.result = {
            "title": self.title_var.get().strip(),
            "text": self.text_text.get("1.0", "end").strip(),
            "keywords": self.keywords_var.get().strip(),
            "color": self.color_var.get().strip() or self.DEFAULT_COLOR,
        }
        self.destroy()