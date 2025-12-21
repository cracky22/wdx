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
        self.geometry("540x800")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.iconbitmap("icon128.ico")
        main = ttk.Frame(self, padding="20")
        main.pack(fill="both", expand=True)
        url_frame = ttk.Frame(main)
        url_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(url_frame, text="URL:", font=("Helvetica", 10, "bold")).pack(
            anchor="w"
        )
        url_entry_frame = ttk.Frame(url_frame)
        url_entry_frame.pack(fill="x")
        self.url_var = tk.StringVar(value=self.source.get("url", ""))
        self.url_entry = ttk.Entry(url_entry_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side="left", fill="x", expand=True)
        paste_btn = ttk.Button(
            url_entry_frame, text="📋", width=3, command=self.paste_clipboard
        )
        paste_btn.pack(side="right", padx=(5, 0))
        ttk.Label(main, text="Titel:", font=("Helvetica", 10, "bold")).pack(
            anchor="w", pady=(10, 0)
        )
        self.title_var = tk.StringVar(value=self.source.get("title", ""))
        ttk.Entry(main, textvariable=self.title_var).pack(fill="x", pady=(0, 10))
        ttk.Label(main, text="Text:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        text_frame = ttk.Frame(main)
        text_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.text_text = tk.Text(text_frame, height=10, wrap="word")
        self.text_text.pack(fill="both", expand=True)
        self.text_text.insert("1.0", self.source.get("text", ""))
        ttk.Label(main, text="Schlagworte:", font=("Helvetica", 10, "bold")).pack(
            anchor="w"
        )
        self.keywords_var = tk.StringVar(value=self.source.get("keywords", ""))
        ttk.Entry(main, textvariable=self.keywords_var).pack(fill="x", pady=(0, 10))
        ttk.Label(main, text="Farbe:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        color_frame = ttk.Frame(main)
        color_frame.pack(fill="x", pady=(0, 15))
        self.color_var = tk.StringVar(value=self.source.get("color", "#ffffff"))
        self.selected_color_swatch = tk.Label(
            color_frame, bg=self.color_var.get(), width=3, relief="solid", borderwidth=1
        )
        self.selected_color_swatch.pack(side="left", padx=(0, 5))
        ttk.Entry(color_frame, textvariable=self.color_var, width=15).pack(side="left")
        ttk.Button(color_frame, text="Wählen", command=self.choose_color).pack(
            side="left", padx=(5, 0)
        )
        self.color_var.trace_add("write", self.update_color_swatch)
        all_items = project_window.project["data"].get("items", [])

        custom_colors = {
            item.get("color").strip()
            for item in all_items
            if item.get("color") and item.get("color").strip()
        }

        used_colors = list(custom_colors)
        if used_colors:
            ttk.Label(
                main, text="Bereits verwendete Farben:", font=("Helvetica", 9)
            ).pack(anchor="w")
            palette = ttk.Frame(main)
            palette.pack(fill="x", pady=(0, 15))

            for col in used_colors:
                initial_relief = "flat"
                initial_border = 1
                label = tk.Label(
                    palette,
                    width=3,
                    height=1,
                    relief=initial_relief,
                    borderwidth=initial_border,
                    cursor="hand2",
                    highlightbackground="#AAAAAA",
                    highlightthickness=1,
                )

                self.after(1, lambda l=label, c=col: l.config(bg=c))
                label.bind("<Button-1>", lambda e, c=col: self.color_var.set(c))

                def on_enter(event, l):
                    l.config(
                        relief="raised",
                        borderwidth=2,
                        highlightbackground="#FFFFFF",
                        highlightthickness=2,
                    )

                def on_leave(event, l):
                    l.config(
                        relief=initial_relief,
                        borderwidth=initial_border,
                        highlightbackground="#AAAAAA",
                        highlightthickness=1,
                    )

                label.bind("<Enter>", lambda e, l=label: on_enter(e, l))
                label.bind("<Leave>", lambda e, l=label: on_leave(e, l))
                label.pack(side="left", padx=2)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(
            btn_frame,
            text="Abbrechen",
            command=self.destroy,
            bootstyle="secondary-outline",
        ).pack(side="right", padx=10)
        ttk.Button(
            btn_frame,
            text="Speichern",
            command=self.save,
            bootstyle="primary",
            width=15,
        ).pack(side="right")
        self.url_entry.focus_set()
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