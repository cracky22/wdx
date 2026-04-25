import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser, filedialog
from dialogs import SourceDialog, HeadingDialog, FileCardDialog
import datetime
import uuid
import webbrowser
import pyperclip
import json
import os
import re
import shutil
import subprocess
import sys
from bs4 import BeautifulSoup
from pathlib import Path
from PIL import Image, ImageTk
import requests
from urllib.parse import urlparse, urljoin
import threading
import concurrent.futures

from wdx_logger import get_logger

logger = get_logger(__name__)


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


FILE_TYPE_ICONS = {
    ".pdf": "📕", ".doc": "📝", ".docx": "📝", ".odt": "📝",
    ".xls": "📊", ".xlsx": "📊", ".ods": "📊", ".csv": "📊",
    ".ppt": "📽", ".pptx": "📽", ".odp": "📽",
    ".txt": "📄", ".md": "📄", ".rtf": "📄",
    ".jpg": "🖼", ".jpeg": "🖼", ".png": "🖼", ".gif": "🖼",
    ".svg": "🖼", ".webp": "🖼", ".bmp": "🖼",
    ".mp4": "🎬", ".mov": "🎬", ".avi": "🎬", ".mkv": "🎬",
    ".mp3": "🎵", ".wav": "🎵", ".flac": "🎵", ".ogg": "🎵",
    ".zip": "🗜", ".rar": "🗜", ".7z": "🗜", ".tar": "🗜",
    ".py": "🐍", ".js": "⚙", ".html": "🌐", ".css": "🎨",
    ".json": "⚙", ".xml": "⚙",
}

# ─────────────────────────────────────────────────────────────────────────────
# Inline-Markdown-Regex (order matters: most specific first)
# ─────────────────────────────────────────────────────────────────────────────
_INLINE_RE = re.compile(
    r"(!\[(?P<alt>[^\]]*)\]\((?P<imgpath>[^)]+)\))"   # image
    r"|(\[(?P<ltext>[^\]]+)\]\((?P<lurl>[^)]+)\))"     # link
    r"|(\*\*\*(?P<bdi>[^*\n]+?)\*\*\*)"                # ***bold+italic***
    r"|(\*\*(?P<bd>[^*\n]+?)\*\*)"                      # **bold**
    r"|(\*(?P<it>[^*\n]+?)\*)"                          # *italic*
    r"|(`(?P<cd>[^`\n]+)`)"                             # `code`
)


class MarkdownReader(tk.Toplevel):
    """Lesbarer Markdown-Betrachter mit Syntax-Highlighting und Bild-Support."""

    _DARK = dict(
        bg="#1e1e2e", fg="#cdd6f4", code_bg="#313244",
        h1_fg="#cba6f7", h2_fg="#89b4fa", h3_fg="#89dceb",
        link_fg="#89dceb", quote_fg="#a6adc8", quote_bg="#181825",
        hr_fg="#45475a", meta_fg="#6c7086", title_fg="#cba6f7",
        btn_bg="#313244", btn_fg="#cdd6f4", sep_fg="#45475a",
    )
    _LIGHT = dict(
        bg="#ffffff", fg="#1e1e2e", code_bg="#f1f3f4",
        h1_fg="#1a1a2e", h2_fg="#1565c0", h3_fg="#0d47a1",
        link_fg="#1976d2", quote_fg="#555555", quote_bg="#f5f5f5",
        hr_fg="#cccccc", meta_fg="#888888", title_fg="#1a1a2e",
        btn_bg="#e8eaf6", btn_fg="#1e1e2e", sep_fg="#dddddd",
    )

    def __init__(self, parent, item, project_path, app):
        super().__init__(parent)
        self.item = item
        self.project_path = Path(project_path)
        self.app = app
        self.c = self._DARK if app.dark_mode else self._LIGHT
        self._img_refs = []  # prevent GC of PhotoImages

        label = item.get("title") or item.get("filename") or item.get("url", "Reader")
        self.title(f"Reader — {label}")
        self.geometry("860x980")
        self.minsize(500, 400)
        self.configure(bg=self.c["bg"])
        try:
            self.iconbitmap("icon128.ico")
        except Exception:
            pass
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-w>", lambda e: self.destroy())
        self.bind("<Control-i>", lambda e: self.destroy())
        self.focus_set()
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        c = self.c
        item = self.item

        # ── Header ─────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=c["bg"], padx=24, pady=14)
        hdr.pack(fill="x")

        title_text = item.get("title") or item.get("filename") or item.get("url", "")
        tk.Label(
            hdr, text=title_text, font=("Helvetica", 17, "bold"),
            bg=c["bg"], fg=c["title_fg"], wraplength=760, justify="left",
            anchor="w",
        ).pack(anchor="w")

        # URL for source type
        if item.get("type") == "source" and item.get("url"):
            lbl = tk.Label(
                hdr, text=f"🔗 {item['url']}", font=("Helvetica", 9),
                bg=c["bg"], fg=c["link_fg"], cursor="hand2",
                wraplength=760, justify="left", anchor="w",
            )
            lbl.pack(anchor="w", pady=(2, 0))
            lbl.bind("<Button-1>", lambda e: webbrowser.open(item["url"]))

        # File path for file type
        if item.get("type") == "file" and item.get("filename"):
            tk.Label(
                hdr, text=f"📎 {item['filename']}", font=("Helvetica", 9),
                bg=c["bg"], fg=c["meta_fg"], anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        # Meta bar
        meta_parts = []
        if item.get("added"):
            meta_parts.append(f"📅 {item['added']}")
        if item.get("keywords"):
            meta_parts.append(f"🏷 {item['keywords']}")
        if meta_parts:
            tk.Label(
                hdr, text="   ".join(meta_parts), font=("Helvetica", 9),
                bg=c["bg"], fg=c["meta_fg"], anchor="w",
            ).pack(anchor="w", pady=(5, 0))

        # ── Action bar ─────────────────────────────────────────────────────
        bar = tk.Frame(self, bg=c["bg"], padx=24, pady=6)
        bar.pack(fill="x")

        def _btn(parent, text, cmd):
            b = tk.Button(
                parent, text=text, font=("Helvetica", 9),
                bg=c["btn_bg"], fg=c["btn_fg"], relief="flat",
                activebackground=c["sep_fg"], activeforeground=c["fg"],
                padx=9, pady=4, cursor="hand2", bd=0, command=cmd,
            )
            b.pack(side="left", padx=(0, 6))
            return b

        _btn(bar, "📋 Text kopieren", lambda: pyperclip.copy(item.get("text", "")))

        if item.get("type") == "source":
            def _copy_cite():
                fmt = self.app.project_manager.get_setting(
                    "citation_format", "{url}, zuletzt aufgerufen am {added}"
                )
                try:
                    cite = fmt.format_map({
                        "url": item.get("url", ""), "title": item.get("title", ""),
                        "added": item.get("added", ""), "keywords": item.get("keywords", ""),
                        "text": item.get("text", ""),
                    })
                except (KeyError, ValueError):
                    cite = f"{item.get('url','')}, zuletzt aufgerufen am {item.get('added','')}"
                pyperclip.copy(cite)
            _btn(bar, "📎 Quellenangabe", _copy_cite)

        tk.Label(
            bar, text="Esc  ·  Strg+I  zum Schließen",
            font=("Helvetica", 8), bg=c["bg"], fg=c["meta_fg"],
        ).pack(side="right")

        # ── Separator ──────────────────────────────────────────────────────
        tk.Frame(self, bg=c["sep_fg"], height=1).pack(fill="x")

        # ── Scrollable text area ───────────────────────────────────────────
        container = tk.Frame(self, bg=c["bg"])
        container.pack(fill="both", expand=True)

        vscroll = ttk.Scrollbar(container, orient="vertical")
        vscroll.pack(side="right", fill="y")

        self._tw = tk.Text(
            container,
            bg=c["bg"], fg=c["fg"],
            font=("Helvetica", 11),
            wrap="word",
            padx=28, pady=18,
            spacing1=1, spacing2=3, spacing3=1,
            relief="flat", bd=0,
            yscrollcommand=vscroll.set,
            cursor="arrow",
            exportselection=True,
            state="normal",
            insertwidth=0,
        )
        self._tw.pack(fill="both", expand=True)
        vscroll.config(command=self._tw.yview)

        # Mouse wheel
        self._tw.bind("<MouseWheel>", lambda e: self._tw.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))
        self._tw.bind("<Button-4>", lambda e: self._tw.yview_scroll(-1, "units"))
        self._tw.bind("<Button-5>", lambda e: self._tw.yview_scroll(1, "units"))

        self._configure_tags()
        self._render(item.get("text", ""))
        self._tw.config(state="disabled")

    # ── Tag configuration ──────────────────────────────────────────────────

    def _configure_tags(self):
        c = self.c
        tw = self._tw
        tw.tag_configure("h1", font=("Helvetica", 22, "bold"), foreground=c["h1_fg"],
                          spacing1=14, spacing3=6)
        tw.tag_configure("h2", font=("Helvetica", 17, "bold"), foreground=c["h2_fg"],
                          spacing1=11, spacing3=4)
        tw.tag_configure("h3", font=("Helvetica", 14, "bold"), foreground=c["h3_fg"],
                          spacing1=8, spacing3=3)
        tw.tag_configure("bold", font=("Helvetica", 11, "bold"))
        tw.tag_configure("italic", font=("Helvetica", 11, "italic"))
        tw.tag_configure("bolditalic", font=("Helvetica", 11, "bold italic"))
        tw.tag_configure("code_inline", font=("Courier New", 10),
                          background=c["code_bg"], relief="flat")
        tw.tag_configure("code_block", font=("Courier New", 10),
                          background=c["code_bg"], foreground=c["fg"],
                          lmargin1=12, lmargin2=12, spacing1=6, spacing3=6)
        tw.tag_configure("blockquote", lmargin1=28, lmargin2=28,
                          foreground=c["quote_fg"], background=c["quote_bg"],
                          font=("Helvetica", 11, "italic"), spacing1=2, spacing3=2)
        tw.tag_configure("list_item", lmargin1=22, lmargin2=34)
        tw.tag_configure("hr", foreground=c["hr_fg"], font=("Helvetica", 4),
                          spacing1=6, spacing3=6)
        tw.tag_configure("normal", font=("Helvetica", 11))
        tw.tag_configure("meta_text", font=("Helvetica", 9), foreground=c["meta_fg"])
        tw.tag_configure("empty_notice", font=("Helvetica", 11, "italic"),
                          foreground=c["meta_fg"])

    # ── Markdown renderer ─────────────────────────────────────────────────

    def _render(self, text):
        if not text or not text.strip():
            self._tw.insert(tk.END, "(Kein Text vorhanden)", "empty_notice")
            return

        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code block
            if line.startswith("```"):
                i += 1
                code_lines = []
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                self._insert_code_block("\n".join(code_lines))
                i += 1
                continue

            # Horizontal rule
            if re.match(r"^[-*_]{3,}\s*$", line):
                self._tw.insert(tk.END, "\n" + "─" * 68 + "\n\n", "hr")
                i += 1
                continue

            # ATX headings
            m = re.match(r"^(#{1,3})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                tag = ("h1", "h2", "h3")[min(level, 3) - 1]
                self._inline(m.group(2) + "\n", (tag,))
                i += 1
                continue

            # Blockquote
            if line.startswith("> "):
                self._inline(line[2:] + "\n", ("blockquote",))
                i += 1
                continue

            # Unordered list
            if re.match(r"^[-*+] ", line):
                self._inline("• " + line[2:] + "\n", ("list_item",))
                i += 1
                continue

            # Ordered list
            m = re.match(r"^(\d+\.\s+)(.*)", line)
            if m:
                self._inline(m.group(1) + m.group(2) + "\n", ("list_item",))
                i += 1
                continue

            # Empty line
            if not line.strip():
                self._tw.insert(tk.END, "\n", "normal")
                i += 1
                continue

            # Normal paragraph line
            self._inline(line + "\n", ("normal",))
            i += 1

    def _inline(self, text, base_tags=()):
        """Insert text with inline markdown into the text widget."""
        tw = self._tw
        pos = 0
        for m in _INLINE_RE.finditer(text):
            if m.start() > pos:
                tw.insert(tk.END, text[pos:m.start()], base_tags)

            if m.group("imgpath") is not None:
                self._insert_image(m.group("alt") or "", m.group("imgpath"))
            elif m.group("lurl") is not None:
                url = m.group("lurl")
                tag_id = f"lnk_{abs(hash(url + str(m.start())))}"
                tw.tag_configure(tag_id, foreground=self.c["link_fg"],
                                  underline=True, font=("Helvetica", 11))
                tw.tag_bind(tag_id, "<Button-1>", lambda e, u=url: webbrowser.open(u))
                tw.tag_bind(tag_id, "<Enter>", lambda e: tw.config(cursor="hand2"))
                tw.tag_bind(tag_id, "<Leave>", lambda e: tw.config(cursor="arrow"))
                tw.insert(tk.END, m.group("ltext"), (tag_id,) + base_tags)
            elif m.group("bdi") is not None:
                tw.insert(tk.END, m.group("bdi"), ("bolditalic",) + base_tags)
            elif m.group("bd") is not None:
                tw.insert(tk.END, m.group("bd"), ("bold",) + base_tags)
            elif m.group("it") is not None:
                tw.insert(tk.END, m.group("it"), ("italic",) + base_tags)
            elif m.group("cd") is not None:
                tw.insert(tk.END, m.group("cd"), ("code_inline",))

            pos = m.end()

        if pos < len(text):
            tw.insert(tk.END, text[pos:], base_tags)

    def _insert_code_block(self, code_text):
        tw = self._tw
        c = self.c

        frame = tk.Frame(tw, bg=c["code_bg"], padx=10, pady=8)
        copy_btn = tk.Button(
            frame, text="📋", font=("Helvetica", 8),
            bg=c["code_bg"], fg=c["meta_fg"], relief="flat",
            cursor="hand2", padx=3, pady=1, bd=0,
            command=lambda: pyperclip.copy(code_text),
        )
        copy_btn.pack(anchor="ne")
        tk.Label(
            frame, text=code_text or " ",
            font=("Courier New", 10), bg=c["code_bg"], fg=c["fg"],
            justify="left", anchor="w",
        ).pack(fill="x", anchor="w")

        tw.insert(tk.END, "\n")
        tw.window_create(tk.END, window=frame, padx=0, pady=2)
        tw.insert(tk.END, "\n\n")

    def _insert_image(self, alt, path_str):
        tw = self._tw
        path_str = path_str.strip()
        resolved = None

        p = Path(path_str)
        if p.is_absolute() and p.exists():
            resolved = p
        else:
            for base in (
                self.project_path,
                self.project_path / "images",
                self.project_path / "files",
            ):
                candidate = base / path_str
                if candidate.exists():
                    resolved = candidate
                    break

        if resolved:
            try:
                img = Image.open(resolved).convert("RGBA")
                max_w = 720
                if img.width > max_w:
                    ratio = max_w / img.width
                    img = img.resize(
                        (max_w, int(img.height * ratio)),
                        Image.Resampling.LANCZOS,
                    )
                photo = ImageTk.PhotoImage(img)
                self._img_refs.append(photo)
                tw.insert(tk.END, "\n")
                tw.image_create(tk.END, image=photo, padx=0, pady=4)
                if alt:
                    tw.insert(tk.END, f"\n{alt}\n", "meta_text")
                tw.insert(tk.END, "\n")
                return
            except Exception:
                pass

        # Fallback
        tw.insert(tk.END, f"[🖼 {alt or path_str}]", ("italic",))


# ─────────────────────────────────────────────────────────────────────────────


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
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=os.cpu_count() or 4
        )
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
        self.search_results = []
        self.search_result_index = 0
        self.search_highlighted_ids = set()

        if "items" not in self.project["data"]:
            if "sources" in self.project["data"]:
                self.project["data"]["items"] = [
                    {"type": "source", **s}
                    for s in self.project["data"]["sources"]
                ]
            else:
                self.project["data"]["items"] = []

        logger.info("ProjectWindow geöffnet: %s", project["name"])

        self.main_frame = ttk.Frame(self.root, padding="0", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        header_frame = ttk.Frame(self.main_frame, padding="15 10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        header_frame.columnconfigure(1, weight=1)
        ttk.Button(
            header_frame,
            text="← Zurück zu Projekten",
            command=self.back_to_projects,
            bootstyle="info-outline",
        ).grid(row=0, column=0, sticky=tk.W, padx=10)
        btn_frame = ttk.Frame(header_frame)
        btn_frame.grid(row=0, column=2, sticky=tk.E, padx=20)
        ttk.Button(
            btn_frame, text="💾", width=3, bootstyle="info-outline",
            command=self.manual_save,
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="🔍", width=3, bootstyle="info-outline",
            command=self.reset_zoom,
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="📥", width=3, bootstyle="info-outline",
            command=self.manual_export,
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="🔄", width=3, bootstyle="info-outline",
            command=self.manual_reload,
        ).pack(side="left", padx=2)
        ttk.Label(
            header_frame,
            text=f"Mindmap: {project['name']}",
            font=("Helvetica", 18, "bold"),
            bootstyle="inverse-primary",
        ).grid(row=0, column=1, sticky=tk.W, padx=20)
        ttk.Label(
            header_frame,
            text=f"📋 {project['description']}",
            font=("Helvetica", 11),
        ).grid(row=1, column=1, sticky=tk.W, padx=20, columnspan=2)

        search_frame = ttk.Frame(header_frame)
        search_frame.grid(
            row=2, column=0, columnspan=3, sticky=tk.W + tk.E, padx=10, pady=(6, 2)
        )
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text="🔎", font=("Helvetica", 12)).grid(
            row=0, column=0, padx=(0, 6)
        )
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            search_frame, textvariable=self.search_var, width=35, font=("Helvetica", 10)
        )
        self.search_entry.grid(row=0, column=1, sticky=tk.W + tk.E, padx=(0, 8))
        self.search_var.trace_add("write", lambda *_: self._on_search_change())
        self.search_only_keywords_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            search_frame,
            text="Nur Schlagwörter",
            variable=self.search_only_keywords_var,
            bootstyle="round-toggle",
            command=self._on_search_change,
        ).grid(row=0, column=2, padx=(0, 12))
        self.search_prev_btn = ttk.Button(
            search_frame, text="◀", width=3, bootstyle="secondary-outline",
            command=self._search_prev,
        )
        self.search_prev_btn.grid(row=0, column=3, padx=1)
        self.search_next_btn = ttk.Button(
            search_frame, text="▶", width=3, bootstyle="secondary-outline",
            command=self._search_next,
        )
        self.search_next_btn.grid(row=0, column=4, padx=1)
        self.search_status_label = ttk.Label(
            search_frame, text="", font=("Helvetica", 9), width=14
        )
        self.search_status_label.grid(row=0, column=5, padx=(6, 0))

        self.canvas = tk.Canvas(
            self.main_frame, bg="#f5f7fa", highlightthickness=0
        )
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        h_scroll = ttk.Scrollbar(
            self.main_frame, orient="horizontal",
            command=self.canvas.xview, bootstyle="round",
        )
        v_scroll = ttk.Scrollbar(
            self.main_frame, orient="vertical",
            command=self.canvas.yview, bootstyle="round",
        )
        self.canvas.configure(
            xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set
        )
        self.canvas.config(xscrollincrement=1, yscrollincrement=1)
        h_scroll.grid(row=2, column=0, sticky=(tk.W, tk.E))
        v_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))

        self.add_menu = tk.Menu(self.root, tearoff=0)
        self.add_menu.add_command(
            label="Überschrift (Strg+u)", command=self.add_heading
        )
        self.add_menu.add_command(
            label="Quellenangabe (Strg+n)", command=self.add_source
        )
        self.add_button = ttk.Button(
            self.main_frame, text="+", width=4,
            command=self.show_add_menu, bootstyle="primary-outline-toolbutton",
        )
        self.add_button.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        self.minimap_canvas = tk.Canvas(
            self.main_frame, width=200, height=150,
            bg="#f5f7fa", highlightthickness=1, highlightbackground="#cccccc",
        )
        self.minimap_canvas.place(relx=1.0, rely=1.0, x=-70, y=-70, anchor="se")
        self.minimap_canvas.bind("<ButtonPress-1>", self.on_minimap_click)
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Helvetica", 10))
        self.load_items_on_canvas()
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self._bind_shortcuts()
        self.start_auto_refresh()

    
    def _bind_shortcuts(self):
        for modifier in ("<Control-{}>", "<Command-{}>"):
            self.root.bind(modifier.format("s"), lambda e: self.manual_save())
            self.root.bind(modifier.format("q"), lambda e: self.shortcut_citation())
            self.root.bind(modifier.format("h"), lambda e: self.show_saved_shortcut())
            self.root.bind(modifier.format("l"), lambda e: self.reload_current_page_shortcut())
            self.root.bind(modifier.format("e"), lambda e: self.edit_shortcut())
            self.root.bind(modifier.format("w"), lambda e: self.back_to_projects())
            self.root.bind(modifier.format("r"), lambda e: self.reset_zoom())
            self.root.bind(modifier.format("p"), lambda e: self.manual_export())
            self.root.bind(modifier.format("b"), lambda e: self.manual_reload())
            self.root.bind(modifier.format("d"), self._handle_duplicate_shortcut)
            self.root.bind(modifier.format("c"), self._handle_copy_shortcut)
            self.root.bind(modifier.format("v"), self._handle_paste_shortcut)
            self.root.bind(modifier.format("u"), lambda e: self.add_heading())
            self.root.bind(modifier.format("n"), lambda e: self.add_source())
            self.root.bind(modifier.format("f"), lambda e: self._focus_search())
            self.root.bind(modifier.format("o"), lambda e: self.open_original_shortcut())
            self.root.bind(modifier.format("i"), lambda e: self.show_reader())
        self.root.bind("<Delete>", lambda e: self.delete_shortcut())
        self.search_entry.bind("<Return>", lambda e: self._search_next())
        self.search_entry.bind("<Escape>", lambda e: self._clear_search())

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

    
    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)

    def _clear_search(self):
        self.search_var.set("")
        self._remove_search_highlights()
        self.search_results = []
        self.search_result_index = 0
        self.search_status_label.config(text="")

    def _on_search_change(self):
        query = self.search_var.get().strip()
        if not query:
            self._clear_search()
            return
        self._run_search(query)

    def _item_matches(self, item, query_lower, only_keywords):
        if only_keywords:
            return query_lower in item.get("keywords", "").lower()
        if item.get("type") == "heading":
            return query_lower in item.get("text", "").lower()
        return (
            query_lower in item.get("title", "").lower()
            or query_lower in item.get("text", "").lower()
            or query_lower in item.get("keywords", "").lower()
        )

    def _run_search(self, query=None):
        if query is None:
            query = self.search_var.get().strip()
        query_lower = query.lower()
        only_kw = self.search_only_keywords_var.get()

        self._remove_search_highlights()
        self.search_results = []

        for item in self.project["data"]["items"]:
            if self._item_matches(item, query_lower, only_kw):
                self.search_results.append(item["id"])

        if self.search_results:
            self.search_result_index = 0
            self.canvas.update_idletasks()
            self._apply_search_highlights()
            self._jump_to_search_result(self.search_result_index)
            self._update_search_status()
            logger.debug("Suche '%s' — %d Treffer", query, len(self.search_results))
        else:
            self.search_status_label.config(text="Kein Treffer")
            logger.debug("Suche '%s' — kein Treffer", query)

    def _apply_search_highlights(self):
        self.search_highlighted_ids = set(self.search_results)
        for i, item_id in enumerate(self.search_results):
            is_active = i == self.search_result_index
            self._highlight_card(active=is_active, item_id=item_id)

    def _highlight_card(self, active=False, item_id=None):
        if item_id not in self.source_frames:
            return
        frame, canvas_id = self.source_frames[item_id]
        self.canvas.update_idletasks()
        coords = self.canvas.coords(canvas_id)
        if not coords:
            return
        x1, y1 = coords[0], coords[1]
        fw = frame.winfo_width()
        fh = frame.winfo_height()
        if fw <= 1 or fh <= 1:
            fw = frame.winfo_reqwidth()
            fh = frame.winfo_reqheight()
        x2 = x1 + fw
        y2 = y1 + fh
        tag = f"search_glow_{item_id}"
        self.canvas.delete(tag)
        if active:
            pad, color, width, dash = 6, "#f4a12b", 4, (8, 3)
        else:
            pad, color, width, dash = 4, "#6cb4f5", 2, (5, 4)
        self.canvas.create_rectangle(
            x1 - pad, y1 - pad, x2 + pad, y2 + pad,
            outline=color, width=width, dash=dash,
            tags=(tag, "search_glow"),
        )
        self.canvas.tag_raise(tag)
        self.canvas.tag_raise(canvas_id)

    def _remove_search_highlights(self):
        self.canvas.delete("search_glow")
        for item_id in self.search_highlighted_ids:
            if item_id in self.source_frames:
                frame, _ = self.source_frames[item_id]
                try:
                    default_bw = 2 if frame.item_data.get("type") == "source" else 0
                    frame.config(relief="raised", borderwidth=default_bw)
                except Exception as exc:
                    logger.debug("Highlight-Reset fehlgeschlagen (%s): %s", item_id, exc)
        self.search_highlighted_ids = set()

    def _jump_to_search_result(self, index):
        if not self.search_results:
            return
        item_id = self.search_results[index]
        if item_id not in self.source_frames:
            return
        frame, canvas_id = self.source_frames[item_id]
        self.canvas.update_idletasks()
        coords = self.canvas.coords(canvas_id)
        if not coords:
            return
        x1, y1 = coords[0], coords[1]
        fw = frame.winfo_width() or frame.winfo_reqwidth()
        fh = frame.winfo_height() or frame.winfo_reqheight()
        cx = x1 + fw / 2
        cy = y1 + fh / 2
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        bx1, by1, bx2, by2 = bbox
        w = bx2 - bx1
        h = by2 - by1
        if w <= 0 or h <= 0:
            return
        view_w = self.canvas.winfo_width()
        view_h = self.canvas.winfo_height()
        self.canvas.xview_moveto(max(0.0, min(1.0, (cx - bx1 - view_w / 2) / w)))
        self.canvas.yview_moveto(max(0.0, min(1.0, (cy - by1 - view_h / 2) / h)))

    def _update_search_status(self):
        total = len(self.search_results)
        if total == 0:
            self.search_status_label.config(text="Kein Treffer")
        else:
            self.search_status_label.config(
                text=f"{self.search_result_index + 1} / {total}"
            )

    def _search_next(self):
        if not self.search_results:
            self._run_search()
            return
        self.search_result_index = (self.search_result_index + 1) % len(
            self.search_results
        )
        self._apply_search_highlights()
        self._jump_to_search_result(self.search_result_index)
        self._update_search_status()

    def _search_prev(self):
        if not self.search_results:
            return
        self.search_result_index = (self.search_result_index - 1) % len(
            self.search_results
        )
        self._apply_search_highlights()
        self._jump_to_search_result(self.search_result_index)
        self._update_search_status()

    
    def _process_item_data(self, item):
        if item.get("type") == "heading":
            return {"item": item, "kind": "heading", "favicon_path": None}
        if item.get("type") == "file":
            return {"item": item, "kind": "file", "favicon_path": None}
        # source
        favicon_path = None
        if item.get("favicon"):
            check_path = (
                Path(self.project["path"]) / "images" / item["favicon"]
            )
            if check_path.exists():
                favicon_path = str(check_path)
            else:
                logger.debug("Favicon-Datei nicht gefunden: %s", check_path)
        return {"item": item, "kind": "source", "favicon_path": favicon_path}

    def load_items_on_canvas(self):
        items_to_process = self.project["data"]["items"]
        logger.debug("Canvas-Laden gestartet — %d Element(e)", len(items_to_process))
        threading.Thread(
            target=self._concurrent_load_worker,
            args=(items_to_process,),
            daemon=True,
        ).start()

    def _concurrent_load_worker(self, items_to_process):
        try:
            if self.shutting_down:
                return
            processed_results = list(
                self.executor.map(self._process_item_data, items_to_process)
            )
            if (
                hasattr(self, "main_frame")
                and self.main_frame.winfo_exists()
                and not self.shutting_down
            ):
                self.root.after(
                    0, self._create_all_cards_in_gui_thread, processed_results
                )
        except concurrent.futures.CancelledError:
            logger.debug("Concurrent-Load-Worker abgebrochen (CancelledError)")
        except Exception as exc:
            if not self.shutting_down:
                logger.exception("Fehler im Concurrent-Load-Worker: %s", exc)

    def _create_all_cards_in_gui_thread(self, processed_results):
        if self.shutting_down:
            return
        for frame, item_id in list(self.source_frames.values()):
            self.canvas.delete(item_id)
            frame.destroy()
        self.source_frames.clear()
        self.card_widgets.clear()
        self.canvas.delete("search_glow")
        self.search_highlighted_ids = set()

        for result in processed_results:
            item = result["item"]
            if self.project["data"].get("selected_source_id") == item["id"]:
                self.selected_source_id = item["id"]
            kind = result.get("kind")
            if kind == "source":
                self._create_source_card_gui(item, result["favicon_path"])
            elif kind == "file":
                self._create_file_card_gui(item)
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
        return self.app.style.lookup("TLabel", "background")

    def _get_default_border_width(self, item):
        return 2 if item["type"] == "source" else 0

    def _on_mousewheel(self, event, up=None):
        if self.dragging_canvas or self.dragging_card:
            return
        direction = (1 if event.delta > 0 else -1) if up is None else (1 if up else -1)
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.zoom(self.zoom_factor if direction > 0 else 1 / self.zoom_factor, x, y)

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

        for item_id, refs in self.card_widgets.items():
            try:
                if "title_label" in refs:
                    refs["title_label"].config(font=("Helvetica", title_size, "bold"))
                if "url_label" in refs:
                    refs["url_label"].config(font=("Helvetica", default_size))
                if "text_label" in refs:
                    refs["text_label"].config(font=("Helvetica", default_size))
                if "keywords_label" in refs:
                    refs["keywords_label"].config(font=("Helvetica", default_size))
                if "added_label" in refs:
                    refs["added_label"].config(
                        font=("Helvetica", max(int(8 * self.zoom_level), 5))
                    )
                if "heading_label" in refs:
                    refs["heading_label"].config(
                        font=("Helvetica", heading_size, "bold")
                    )
                if "icon_label" in refs:
                    od = refs.get("original_icon_data", {})
                    if od.get("is_favicon"):
                        target_size = max(1, int(16 * self.zoom_level))
                        try:
                            resized = od["pil_img"].resize(
                                (target_size, target_size), Image.Resampling.LANCZOS
                            )
                            new_img = ImageTk.PhotoImage(resized)
                            refs["icon_label"].config(image=new_img)
                            refs["icon_label"].image = new_img
                        except Exception as exc:
                            logger.debug(
                                "Favicon-Resize fehlgeschlagen (%s): %s", item_id, exc
                            )
                    else:
                        refs["icon_label"].config(
                            font=("Helvetica", max(int(self.base_icon_size * self.zoom_level), 10))
                        )
            except Exception as exc:
                logger.debug("Card-Scale-Update fehlgeschlagen (%s): %s", item_id, exc)

    def _wrap_keywords(self, keywords: str, max_line_len: int = 31) -> str:
        words = keywords.split()
        lines, current = [], ""
        for word in words:
            candidate = (current + " " + word).strip() if current else word
            if len(candidate) <= max_line_len:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return "\n".join(lines)

    def _create_source_card_gui(self, source, favicon_path):
        color = self._get_effective_bg_color(source)
        text_color = get_contrast_color(color)
        source["effective_color"] = color
        item_id = source["id"]
        style_name = f"Source.{item_id}.TFrame"
        self.card_widgets[item_id] = {}
        try:
            self.root.style.configure(style_name, background=color)
        except tk.TclError as exc:
            logger.debug("Style-Konfiguration fehlgeschlagen (%s): %s", style_name, exc)
            self.root.style.configure(
                style_name, relief="raised",
                borderwidth=self._get_default_border_width(source),
            )

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
                pil_img = Image.open(favicon_path)
                self.card_widgets[item_id]["original_icon_data"] = {
                    "pil_img": pil_img, "is_favicon": True
                }
                target_size = max(10, int(16 * self.zoom_level))
                resized_pil = pil_img.resize(
                    (target_size, target_size), Image.Resampling.LANCZOS
                )
                tk_img = ImageTk.PhotoImage(resized_pil)
                favicon_label = tk.Label(frame, image=tk_img, bg=color)
                favicon_label.image = tk_img
                favicon_label.pack(anchor="w")
                self.card_widgets[item_id]["icon_label"] = favicon_label
            except (OSError, Exception) as exc:
                logger.warning("Favicon konnte nicht geladen werden (%s): %s", favicon_path, exc)
                globe_label = tk.Label(
                    frame, text="🌐", font=("Helvetica", self.base_icon_size),
                    bg=color, fg=text_color,
                )
                globe_label.pack(anchor="w")
                self.card_widgets[item_id]["icon_label"] = globe_label
        else:
            globe_label = tk.Label(
                frame, text="🌐", font=("Helvetica", self.base_icon_size),
                bg=color, fg=text_color,
            )
            globe_label.pack(anchor="w")
            self.card_widgets[item_id]["icon_label"] = globe_label

        title_text = source.get("title") or source["url"]
        title_label = ttk.Label(
            frame, text=title_text, font=self.base_font_title,
            foreground=text_color, wraplength=320,
        )
        title_label.pack(anchor="w")
        self.card_widgets[item_id]["title_label"] = title_label

        if source.get("title"):
            url_label = ttk.Label(
                frame, text=source["url"], font=self.base_font_default,
                foreground=text_color, wraplength=350,
            )
            url_label.pack(anchor="w")
            self.card_widgets[item_id]["url_label"] = url_label

        if source["text"]:
            preview = source["text"][:180] + ("..." if len(source["text"]) > 180 else "")
            text_label = ttk.Label(
                frame, text=f"📝 {preview}", font=self.base_font_default,
                foreground=text_color, wraplength=350,
            )
            text_label.pack(anchor="w", pady=(6, 0))
            self.card_widgets[item_id]["text_label"] = text_label

        if source["keywords"]:
            keywords_label = ttk.Label(
                frame,
                text=f"🏷 {self._wrap_keywords(source['keywords'])}",
                font=self.base_font_default, bootstyle="info",
                foreground=text_color, justify="left",
            )
            keywords_label.pack(anchor="w", pady=(4, 0))
            self.card_widgets[item_id]["keywords_label"] = keywords_label

        added_label = ttk.Label(
            frame, text=f"📅 {source['added']}", font=("Helvetica", 8),
            foreground=text_color,
        )
        added_label.pack(anchor="w", pady=(8, 0))
        self.card_widgets[item_id]["added_label"] = added_label

        ttk.Button(
            frame, text="🔗 Original öffnen", bootstyle="success-outline", width=20,
            command=lambda url=source["url"]: webbrowser.open(url),
        ).pack(pady=(4, 0))

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

        frame.bind(
            "<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid)
        )
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
        except tk.TclError as exc:
            logger.debug("Heading-Style fehlgeschlagen (%s): %s", style_name, exc)

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

        label = tk.Label(
            frame, text=heading["text"], font=self.base_font_heading,
            fg=text_color, bg=color,
        )
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

        frame.bind(
            "<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid)
        )
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

        self._minimap_params = {
            "minimap_scale": 1.0, "offset_x": 0, "offset_y": 0,
            "x1_main": 0, "y1_main": 0, "x2_main": 0, "y2_main": 0,
        }

        if not bbox_all:
            self.viewport_rect_id = None
            self._update_minimap_viewport()
            return

        x1_main, y1_main, x2_main, y2_main = bbox_all
        buffer = 100
        x1_main -= buffer; y1_main -= buffer
        x2_main += buffer; y2_main += buffer
        content_width = x2_main - x1_main
        content_height = y2_main - y1_main
        map_w = self.minimap_canvas.winfo_width()
        map_h = self.minimap_canvas.winfo_height()

        if content_width > 0 and content_height > 0:
            minimap_scale = min(map_w / content_width, map_h / content_height) * 0.9
        else:
            minimap_scale = 1.0

        center_x_map = map_w / 2
        center_y_map = map_h / 2
        offset_x = center_x_map - (x1_main + content_width / 2) * minimap_scale
        offset_y = center_y_map - (y1_main + content_height / 2) * minimap_scale

        self._minimap_params.update({
            "x1_main": x1_main, "y1_main": y1_main,
            "x2_main": x2_main, "y2_main": y2_main,
            "minimap_scale": minimap_scale,
            "offset_x": offset_x, "offset_y": offset_y,
        })

        for item_id, (frame, window_id) in self.source_frames.items():
            coords = self.canvas.coords(window_id)
            if not coords:
                continue
            color = frame.item_data.get("effective_color", "#ffffff")
            mx = coords[0] * minimap_scale + offset_x
            my = coords[1] * minimap_scale + offset_y
            mw = max(15, frame.winfo_width() * minimap_scale)
            mh = max(15, frame.winfo_height() * minimap_scale)
            self.minimap_canvas.create_rectangle(
                mx, my, mx + mw, my + mh, fill=color, outline="#aaaaaa", width=1
            )

        self._update_minimap_viewport()

    def _update_minimap_viewport(self):
        if (
            not self.minimap_canvas
            or not self.minimap_canvas.winfo_exists()
            or not hasattr(self, "_minimap_params")
        ):
            return
        params = self._minimap_params
        ms = params["minimap_scale"]
        ox = params["offset_x"]
        oy = params["offset_y"]
        x_start = self.canvas.canvasx(0)
        y_start = self.canvas.canvasy(0)
        vw = self.canvas.winfo_width()
        vh = self.canvas.winfo_height()
        x_ms = x_start * ms + ox
        y_ms = y_start * ms + oy
        x_me = x_ms + vw * ms
        y_me = y_ms + vh * ms
        if self.viewport_rect_id and self.minimap_canvas.find_withtag(
            self.viewport_rect_id
        ):
            self.minimap_canvas.coords(
                self.viewport_rect_id, x_ms, y_ms, x_me, y_me
            )
            self.minimap_canvas.tag_raise(self.viewport_rect_id)
        else:
            self.viewport_rect_id = self.minimap_canvas.create_rectangle(
                x_ms, y_ms, x_me, y_me,
                outline="#333333", fill="", width=2, stipple="gray50",
            )

    def on_minimap_click(self, event):
        if not hasattr(self, "_minimap_params"):
            return
        params = self._minimap_params
        ms = params["minimap_scale"]
        ox = params["offset_x"]
        oy = params["offset_y"]
        x1_main, y1_main = params["x1_main"], params["y1_main"]
        x2_main, y2_main = params["x2_main"], params["y2_main"]
        total_w = x2_main - x1_main
        total_h = y2_main - y1_main
        if total_w <= 0 or total_h <= 0:
            return
        tx = (event.x - ox) / ms
        ty = (event.y - oy) / ms
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        x_frac = max(0.0, min(1.0, (tx - cx - x1_main) / total_w))
        y_frac = max(0.0, min(1.0, (ty - cy - y1_main) / total_h))
        self.canvas.xview_moveto(x_frac)
        self.canvas.yview_moveto(y_frac)
        self._update_minimap_viewport()

    
    def _apply_selection_style(self, item_id, color):
        if item_id in self.source_frames:
            frame = self.source_frames[item_id][0]
            text_color = get_contrast_color(color)
            frame.config(
                borderwidth=self.DEFAULT_SELECT_BORDER_WIDTH,
                bootstyle=self.DEFAULT_SELECT_BORDER_COLOR,
                relief="raised",
            )
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
            frame.configure(
                style=original_style_name, bootstyle=None,
                borderwidth=border,
                relief="raised" if item_type == "source" else "flat",
            )
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
            if item_id in self.selected_source_ids and len(self.selected_source_ids) > 1:
                pass
            elif item_id not in self.selected_source_ids:
                self.deselect_all_cards(exclude_id=item_id)
                self.selected_source_ids.add(item_id)
                self._apply_selection_style(item_id, original_color)

    def deselect_all_cards(self, exclude_id=None):
        for item_id in list(self.selected_source_ids):
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
            original_color = self.card_original_colors.pop(
                item_id, item.get("effective_color", "#ffffff")
            )
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
                    self.canvas.move(self.source_frames[item_id][1], dx, dy)
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root

    def on_card_release(self, event):
        if self.dragging_card:
            for item_id in self.selected_source_ids:
                if item_id in self.source_frames:
                    coords = self.canvas.coords(self.source_frames[item_id][1])
                    item = next(
                        i for i in self.project["data"]["items"] if i["id"] == item_id
                    )
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
        items = self.canvas.find_overlapping(
            x - search_radius, y - search_radius,
            x + search_radius, y + search_radius,
        )
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
            self.canvas.xview_scroll(
                int(-1 * (event.x - self.canvas_start_x) / self.zoom_level), "units"
            )
            self.canvas.yview_scroll(
                int(-1 * (event.y - self.canvas_start_y) / self.zoom_level), "units"
            )
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
        new_item = self._create_new_item_from_existing(
            item, self.paste_offset_x, self.paste_offset_y
        )
        self.project["data"]["items"].append(new_item)
        if new_item["type"] == "source":
            threading.Thread(
                target=self._concurrent_reload_single_card,
                args=(new_item,), daemon=True,
            ).start()
        else:
            self._create_heading_card_gui(new_item)
        self.selected_source_ids.add(new_item["id"])
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()
        logger.debug("Element dupliziert: %s", item.get("id"))

    def duplicate_selected_items(self):
        if not self.selected_source_ids:
            return
        original_items = [
            next(i for i in self.project["data"]["items"] if i["id"] == item_id)
            for item_id in list(self.selected_source_ids)
        ]
        self.deselect_all_cards()
        new_ids = []
        items_to_process = []
        for original_item in original_items:
            new_item = self._create_new_item_from_existing(
                original_item, self.paste_offset_x, self.paste_offset_y
            )
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
        self.paste_offset_x = min(self.paste_offset_x + 20, 100) or 50
        self.paste_offset_y = min(self.paste_offset_y + 20, 100) or 50
        logger.debug("%d Element(e) dupliziert", len(new_ids))

    def copy_card(self, item):
        self.clipboard = item.copy()
        self.clipboard.pop("effective_color", None)
        self.paste_offset_x = 50
        self.paste_offset_y = 50
        logger.debug("Karte kopiert: %s", item.get("id"))

    def paste_card(self):
        if not self.clipboard:
            return
        new_item = self._create_new_item_from_existing(
            self.clipboard, self.paste_offset_x, self.paste_offset_y
        )
        self.project["data"]["items"].append(new_item)
        if new_item["type"] == "source":
            threading.Thread(
                target=self._concurrent_reload_single_card,
                args=(new_item,), daemon=True,
            ).start()
        else:
            self._create_heading_card_gui(new_item)
        self.deselect_all_cards()
        self.selected_source_ids.add(new_item["id"])
        self.paste_offset_x = (self.paste_offset_x + 20 - 50) % 51 + 50
        self.paste_offset_y = (self.paste_offset_y + 20 - 50) % 51 + 50
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()
        logger.debug("Karte eingefügt: %s", new_item["id"])

    def show_add_menu(self, event=None):
        self.add_menu.delete(0, tk.END)
        self.add_menu.add_command(
            label="Überschrift (Strg+U)", command=self.add_heading
        )
        self.add_menu.add_command(
            label="Quellenangabe (Strg+N)", command=self.add_source
        )
        self.add_menu.add_command(
            label="Datei anhängen …", command=self.add_file
        )
        self.add_menu.post(
            self.add_button.winfo_rootx(),
            self.add_button.winfo_rooty() + self.add_button.winfo_height(),
        )

    def manual_save(self):
        self.save_project()
        logger.debug("Manuelles Speichern — Projekt: %s", self.project["name"])

    def manual_export(self):
        success, file_path = self.app.project_manager.export_project(self.project)
        if success:
            messagebox.showinfo("Exportiert", f"Projekt als '{file_path}' exportiert.")

    def manual_reload(self):
        self.reload_items()
        logger.debug("Manueller Reload — Projekt: %s", self.project["name"])

    def update_last_mtime(self):
        try:
            if os.path.exists(self.project["data_file"]):
                self.last_file_mtime = os.path.getmtime(self.project["data_file"])
            else:
                self.last_file_mtime = 0
        except OSError as exc:
            logger.debug("mtime konnte nicht gelesen werden: %s", exc)
            self.last_file_mtime = 0

    
    def show_saved_pages_popup(self, item=None):
        popup = tk.Toplevel(self.root)
        popup.title("Gespeicherte Seiten")
        popup.geometry("700x500")
        try:
            popup.iconbitmap("icon128.ico")
        except Exception:
            pass
        popup.transient(self.root)
        popup.grab_set()
        popup.focus_set()
        popup.bind("<Escape>", lambda e: popup.destroy())
        popup.bind("<Control-w>", lambda e: popup.destroy())

        main_frame = ttk.Frame(popup, padding=15)
        main_frame.pack(fill="both", expand=True)
        ttk.Label(
            main_frame, text="Gespeicherte Versionen verwalten",
            font=("Helvetica", 12, "bold"),
        ).pack(pady=(0, 15))

        sites_dir = Path(self.project["path"]) / "sites"

        list_container = ttk.Frame(main_frame)
        list_container.pack(fill="both", expand=True)
        canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(canvas_window, width=e.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        popup.bind("<MouseWheel>", _on_mousewheel)
        popup.bind("<Button-4>", _on_mousewheel)
        popup.bind("<Button-5>", _on_mousewheel)

        def get_saved_pages():
            if item and isinstance(item, dict):
                return item.get("saved_pages", [])
            return self.project.get("data", {}).get("saved_pages", [])

        def open_saved_page(page_data):
            filename = page_data.get("file")
            if not filename:
                logger.warning("Gespeicherte Seite ohne Dateiname")
                messagebox.showwarning("Fehler", "Kein Dateiname in den Daten gefunden.")
                return
            full_path = sites_dir / filename
            if full_path.exists():
                webbrowser.open(full_path.absolute().as_uri())
            else:
                logger.warning("Gespeicherte Seite nicht gefunden: %s", full_path)
                messagebox.showerror("Fehler", f"Datei nicht gefunden:\n{full_path}")

        def refresh_list():
            for widget in scroll_frame.winfo_children():
                widget.destroy()
            pages = get_saved_pages()
            if not pages:
                ttk.Label(
                    scroll_frame,
                    text="Keine gespeicherten Seiten vorhanden.",
                    font=("Helvetica", 10, "italic"),
                ).pack(pady=20)
                return
            for index, page in enumerate(pages):
                row = ttk.Frame(scroll_frame, padding=5)
                row.pack(fill="x", pady=2)
                timestamp = page.get("timestamp", "Unbekannt")
                filename = page.get("file", "Unbekannte_Datei.html")
                display_title = page.get("title")
                full_path = sites_dir / filename
                if (not display_title or display_title == "Unbekannter Titel") and full_path.exists():
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            soup = BeautifulSoup(f.read(), "html.parser")
                            display_title = (
                                soup.title.string.strip() if soup.title else filename
                            )
                    except Exception as exc:
                        logger.debug("Titel aus HTML nicht lesbar: %s", exc)
                        display_title = filename
                final_text = f"{timestamp} – {display_title or filename}"
                lbl = ttk.Label(row, text=f"• {final_text}", wraplength=500, cursor="hand2")
                lbl.pack(side="left", padx=5, fill="x", expand=True)
                lbl.bind("<Button-1>", lambda e, p=page: open_saved_page(p))
                btn_frame = ttk.Frame(row)
                btn_frame.pack(side="right")
                ttk.Button(
                    btn_frame, text="🌐", width=3, bootstyle="link",
                    command=lambda p=page: open_saved_page(p),
                ).pack(side="left", padx=2)
                ttk.Button(
                    btn_frame, text="🗑", width=3, bootstyle="danger-link",
                    command=lambda i=index: delete_entry(i),
                ).pack(side="left", padx=2)

        def delete_entry(index=None):
            pages = get_saved_pages()
            if not pages:
                return
            idx = index if index is not None else (len(pages) - 1)
            if messagebox.askyesno(
                "Löschen", "Diese Version wirklich unwiderruflich löschen?", parent=popup
            ):
                page_to_del = pages[idx]
                file_to_del = sites_dir / page_to_del.get("file", "")
                if file_to_del.exists():
                    try:
                        os.remove(file_to_del)
                        logger.debug("Gespeicherte Seite gelöscht: %s", file_to_del.name)
                    except OSError as exc:
                        logger.warning("Datei konnte nicht gelöscht werden: %s", exc)
                pages.pop(idx)
                self.app.project_manager.save_specific_project_data(self.project)
                refresh_list()

        popup.bind("<Delete>", lambda e: delete_entry())
        refresh_list()

    def show_saved_shortcut(self):
        if not self.selected_source_ids:
            return
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if item:
            self.show_saved_pages_popup(item)

    
    def reload_current_page(self, source):
        threading.Thread(
            target=self._reload_worker, args=(source,), daemon=True
        ).start()

    def reload_current_page_shortcut(self):
        if not self.selected_source_ids:
            return
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if item:
            self.reload_current_page(item)

    def _reload_worker(self, source):
        url = source["url"]
        logger.info("Seite neu laden — url=%s", url)
        sites_dir = Path(self.project["path"]) / "sites"
        images_dir = Path(self.project["path"]) / "images"
        sites_dir.mkdir(exist_ok=True)
        images_dir.mkdir(exist_ok=True)
        new_favicon_name = None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            html_content = response.text

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_{source['id']}_{timestamp}.html"
            with open(sites_dir / filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.debug("Seite gespeichert: %s", filename)

            icon_url = None
            base_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(response.url))

            try:
                soup = BeautifulSoup(html_content, "html.parser")
                icon_link = soup.find(
                    "link",
                    rel=lambda x: x
                    and x.lower() in ["icon", "shortcut icon", "apple-touch-icon"],
                )
                if icon_link and icon_link.get("href"):
                    icon_url = urljoin(base_url, icon_link.get("href"))
            except Exception as exc:
                logger.debug("Favicon-Link nicht gefunden: %s", exc)

            if not icon_url:
                icon_url = urljoin(base_url, "/favicon.ico")

            fav_content = None
            try:
                fr = requests.get(icon_url, headers=headers, timeout=5)
                if fr.status_code == 200 and len(fr.content) > 0:
                    fav_content = fr.content
            except requests.exceptions.RequestException as exc:
                logger.debug("Favicon-Download fehlgeschlagen (%s): %s", icon_url, exc)

            if not fav_content:
                try:
                    gr = requests.get(
                        f"https://www.google.com/s2/favicons?domain={base_url}&sz=64",
                        headers=headers, timeout=5,
                    )
                    if gr.status_code == 200:
                        fav_content = gr.content
                except requests.exceptions.RequestException as exc:
                    logger.debug("Google-Favicon-Fallback fehlgeschlagen: %s", exc)

            if fav_content:
                ext = ".ico"
                if b"PNG" in fav_content[:8]:
                    ext = ".png"
                elif b"JFIF" in fav_content[:10]:
                    ext = ".jpg"
                favicon_filename = f"favicon_{source['id']}_{timestamp}{ext}"
                with open(images_dir / favicon_filename, "wb") as f:
                    f.write(fav_content)
                new_favicon_name = favicon_filename

            self.root.after(
                0, self._finalize_reload, source["id"], filename, timestamp, new_favicon_name
            )

        except requests.exceptions.Timeout:
            logger.warning("Reload Timeout — url=%s", url)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Fehler", f"Zeitüberschreitung beim Laden von:\n{url}", parent=self.root
                ),
            )
        except requests.exceptions.HTTPError as exc:
            logger.warning("Reload HTTP-Fehler — url=%s: %s", url, exc)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Fehler", f"Seite nicht erreichbar:\n{exc}", parent=self.root
                ),
            )
        except requests.exceptions.RequestException as exc:
            logger.error("Reload fehlgeschlagen — url=%s: %s", url, exc)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Fehler", f"Verbindungsfehler:\n{exc}", parent=self.root
                ),
            )
        except OSError as exc:
            logger.error("Reload IO-Fehler: %s", exc)

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
            logger.error("Quelle für Reload nicht gefunden: %s", source_id)
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
        logger.info("Seite aktualisiert: %s", source_id)

    def _concurrent_reload_single_card(self, source):
        try:
            result = self._process_item_data(source)
            if source["type"] == "source":
                self.root.after(
                    0, self._create_source_card_gui, source, result["favicon_path"]
                )
            else:
                self.root.after(0, self._create_heading_card_gui, source)
        except Exception as exc:
            logger.error("Einzelkarte konnte nicht neu geladen werden (%s): %s", source.get("id"), exc)

    
    def show_context_menu(self, event, item):
        self.context_menu.delete(0, tk.END)
        item_id = item["id"]
        item_type = item.get("type", "source")

        # ── Gemeinsame Aktionen ──────────────────────────────────────────
        self.context_menu.add_command(
            label="Löschen (Entf)", command=lambda: self.delete_selected_items(item)
        )
        self.context_menu.add_command(
            label="Duplizieren (Strg+D)", command=lambda: self.duplicate_item(item)
        )
        self.context_menu.add_separator()

        # ── Typ-spezifische Aktionen ─────────────────────────────────────
        if item_type == "heading":
            self.context_menu.add_command(
                label="Bearbeiten (Strg+E)", command=lambda: self.edit_heading(item)
            )

        elif item_type == "file":
            self.context_menu.add_command(
                label="Datei öffnen (Strg+O)",
                command=lambda: self._open_file(item),
            )
            self.context_menu.add_command(
                label="Ordner öffnen",
                command=lambda: self._open_file_folder(item),
            )
            if item.get("text"):
                self.context_menu.add_command(
                    label="Reader öffnen (Strg+I)",
                    command=lambda: MarkdownReader(
                        self.root, item, self.project["path"], self.app
                    ),
                )
            self.context_menu.add_command(
                label="Bearbeiten (Strg+E)", command=lambda: self.edit_file(item)
            )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Kopieren (Strg+C)", command=lambda: self.copy_card(item)
            )
            if self.clipboard:
                self.context_menu.add_command(
                    label="Einfügen (Strg+V)", command=self.paste_card
                )

        else:  # source
            if item.get("saved_pages"):
                self.context_menu.add_command(
                    label="Gespeicherte Versionen (Strg+H)",
                    command=lambda: self.show_saved_pages_popup(item),
                )
                self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Original öffnen (Strg+O)",
                command=lambda: webbrowser.open(item["url"]),
            )
            self.context_menu.add_command(
                label="Reader öffnen (Strg+I)",
                command=lambda: MarkdownReader(
                    self.root, item, self.project["path"], self.app
                ),
            )
            self.context_menu.add_command(
                label="Quellenangabe erstellen (Strg+Q)",
                command=lambda: self.create_citation(item),
            )
            self.context_menu.add_command(
                label="Karte bearbeiten (Strg+E)", command=lambda: self.edit_source(item)
            )
            self.context_menu.add_command(
                label="Seite erneut speichern (Strg+L)",
                command=lambda: self.reload_current_page(item),
            )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Kopieren (Strg+C)", command=lambda: self.copy_card(item)
            )
            if self.clipboard:
                self.context_menu.add_command(
                    label="Einfügen (Strg+V)", command=self.paste_card
                )

        # ── Auswahl ──────────────────────────────────────────────────────
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
                or self.handle_card_selection(item_id),
            )
        self.context_menu.post(event.x_root, event.y_root)

    
    def edit_heading(self, heading):
        dialog = HeadingDialog(self.root, heading)
        if not dialog.result:
            return
        heading["text"] = dialog.result["text"]
        heading["color"] = dialog.result["color"]
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
        logger.debug("Überschrift bearbeitet: %s", heading["id"])

    def rename_heading(self, heading):
        new_text = simpledialog.askstring(
            "Umbenennen", "Neuer Text:", initialvalue=heading["text"], parent=self.root
        )
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
        color_result = colorchooser.askcolor(
            title="Farbe wählen",
            initialcolor=heading["color"] or self.DEFAULT_HEADING_BG,
        )
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

    def delete_shortcut(self, event=None):
        if not self.selected_source_ids:
            return
        if len(self.selected_source_ids) > 1:
            self.delete_selected_items()
        else:
            item_id = next(iter(self.selected_source_ids))
            self.delete_item(item_id)

    def delete_item(self, item_id):
        item_to_delete = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if not item_to_delete:
            logger.warning("Zu löschendes Element nicht gefunden: %s", item_id)
            return
        self.project["data"]["items"] = [
            i for i in self.project["data"]["items"] if i["id"] != item_id
        ]
        self._garbage_collect_files([item_to_delete])
        if item_id in self.source_frames:
            frame, canvas_id = self.source_frames[item_id]
            self.canvas.delete(canvas_id)
            frame.destroy()
            del self.source_frames[item_id]
        if item_id in self.card_widgets:
            del self.card_widgets[item_id]
        if item_id in self.selected_source_ids:
            self.selected_source_ids.remove(item_id)
        self.manual_save()
        self._update_minimap()
        logger.info("Element gelöscht: %s", item_id)

    def delete_selected_items(self, _item=None):
        if not self.selected_source_ids:
            return
        if not messagebox.askyesno(
            "Löschen", f"{len(self.selected_source_ids)} Element(e) wirklich löschen?"
        ):
            return
        items_to_remove = [
            item
            for item in self.project["data"]["items"]
            if item["id"] in self.selected_source_ids
        ]
        self.project["data"]["items"] = [
            item
            for item in self.project["data"]["items"]
            if item["id"] not in self.selected_source_ids
        ]
        self._garbage_collect_files(items_to_remove)
        for item_id in list(self.selected_source_ids):
            if item_id in self.source_frames:
                frame, canvas_id = self.source_frames[item_id]
                self.canvas.delete(canvas_id)
                frame.destroy()
                del self.source_frames[item_id]
            if item_id in self.card_widgets:
                del self.card_widgets[item_id]
        logger.info("%d Element(e) gelöscht", len(self.selected_source_ids))
        self.selected_source_ids.clear()
        self.manual_save()
        self._update_minimap()

    def _garbage_collect_files(self, removed_items):
        project_path = Path(self.project["path"])
        remaining_items = self.project.get("data", {}).get("items", [])
        sites_dir = project_path / "sites"
        files_dir = project_path / "files"

        for item in removed_items:
            item_type = item.get("type")
            item_id = item.get("id")
            if not item_id:
                continue

            if item_type == "file":
                filename = item.get("filename")
                if filename and files_dir.exists():
                    still_used = any(
                        i.get("filename") == filename and i.get("type") == "file"
                        for i in remaining_items
                    )
                    if not still_used:
                        fp = files_dir / filename
                        if fp.exists():
                            try:
                                fp.unlink()
                                logger.debug("GC: Datei gelöscht: %s", filename)
                            except OSError as exc:
                                logger.warning("GC: Datei konnte nicht gelöscht werden (%s): %s", filename, exc)
                continue  # file type has no HTML snapshots or favicons

            if item_type == "heading":
                continue

            # source type: delete HTML snapshots
            if sites_dir.exists():
                pattern = f"page_{item_id}_*.html"
                found_files = list(sites_dir.glob(pattern))
                if not found_files:
                    logger.debug("GC: Keine HTML-Dateien für Muster %s", pattern)
                for html_file in found_files:
                    try:
                        html_file.unlink()
                        logger.debug("GC: HTML gelöscht: %s", html_file.name)
                    except OSError as exc:
                        logger.warning("GC: HTML konnte nicht gelöscht werden (%s): %s", html_file.name, exc)

            favicon_name = item.get("favicon")
            if favicon_name:
                still_used = any(
                    i.get("favicon") == favicon_name for i in remaining_items
                )
                if not still_used:
                    fav_path = project_path / "images" / favicon_name
                    if fav_path.exists():
                        try:
                            fav_path.unlink()
                            logger.debug("GC: Favicon gelöscht: %s", favicon_name)
                        except OSError as exc:
                            logger.warning("GC: Favicon konnte nicht gelöscht werden: %s", exc)

    
    def add_heading(self):
        dialog = HeadingDialog(self.root)
        if not dialog.result:
            return
        new_heading = {
            "id": str(uuid.uuid4()), "type": "heading",
            "text": dialog.result["text"], "color": dialog.result["color"],
            "pos_x": 300, "pos_y": 300,
        }
        self.project["data"]["items"].append(new_heading)
        self.deselect_all_cards()
        self._create_heading_card_gui(new_heading)
        self.selected_source_ids.add(new_heading["id"])
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()
        logger.info("Überschrift hinzugefügt: '%s'", new_heading["text"])

    def add_source(self):
        dialog = SourceDialog(self.root, self)
        if dialog.result:
            new_source = {
                "id": str(uuid.uuid4()), "type": "source",
                "url": dialog.result["url"], "title": dialog.result["title"],
                "text": dialog.result["text"], "keywords": dialog.result["keywords"],
                "color": dialog.result["color"],
                "added": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "pos_x": 300 + len(self.project["data"]["items"]) * 80,
                "pos_y": 300, "favicon": "", "saved_pages": [],
            }
            self.project["data"]["items"].append(new_source)
            self.deselect_all_cards()
            self.selected_source_ids.add(new_source["id"])
            threading.Thread(
                target=self._concurrent_reload_single_card,
                args=(new_source,), daemon=True,
            ).start()
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
            self.reset_zoom()
            self._update_minimap()
            logger.info("Quelle manuell hinzugefügt: '%s'", new_source["url"])

    def edit_source(self, source):
        dialog = SourceDialog(self.root, self, source)
        if dialog.result:
            source.update({
                "url": dialog.result["url"],
                "title": dialog.result["title"],
                "text": dialog.result["text"],
                "keywords": dialog.result["keywords"],
                "color": dialog.result["color"],
            })
            item_id = source["id"]
            frame, item_id_canvas = self.source_frames[item_id]
            self.canvas.delete(item_id_canvas)
            frame.destroy()
            del self.source_frames[item_id]
            del self.card_widgets[item_id]
            threading.Thread(
                target=self._concurrent_reload_single_card, args=(source,), daemon=True
            ).start()
            self.save_project()
            self.update_last_mtime()
            self.update_scrollregion()
            self.reset_zoom()
            self._update_minimap()
            logger.debug("Quelle bearbeitet: %s", item_id)

    def edit_shortcut(self):
        if not self.selected_source_ids:
            return
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if item is None:
            return
        if item["type"] == "heading":
            self.edit_heading(item)
        else:
            self.edit_source(item)

    def open_original_shortcut(self):
        """Öffnet die Original-URL bzw. Datei der ausgewählten Karte (Strg+O)."""
        if not self.selected_source_ids:
            return
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if item is None:
            return
        if item.get("type") == "source" and item.get("url"):
            webbrowser.open(item["url"])
            logger.debug("Original geöffnet via Strg+O: %s", item["url"])
        elif item.get("type") == "file":
            self._open_file(item)

    def show_reader(self):
        """Öffnet den Markdown-Reader für die ausgewählte Karte (Strg+I)."""
        if not self.selected_source_ids:
            return
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if item and item.get("type") in ("source", "file"):
            MarkdownReader(self.root, item, self.project["path"], self.app)
            logger.debug("Reader geöffnet für: %s", item_id)

    # ── File card ──────────────────────────────────────────────────────────

    def add_file(self):
        """Datei in das Projekt kopieren und als Karte hinzufügen."""
        filepath = filedialog.askopenfilename(
            title="Datei auswählen", parent=self.root
        )
        if not filepath:
            return

        src = Path(filepath)
        files_dir = Path(self.project["path"]) / "files"
        files_dir.mkdir(exist_ok=True)

        # Collision-safe copy
        dest_name = src.name
        dest = files_dir / dest_name
        counter = 1
        while dest.exists():
            dest = files_dir / f"{src.stem}_{counter}{src.suffix}"
            dest_name = dest.name
            counter += 1

        try:
            shutil.copy2(str(src), str(dest))
        except OSError as exc:
            messagebox.showerror("Fehler", f"Datei konnte nicht kopiert werden:\n{exc}")
            logger.error("Datei-Copy fehlgeschlagen: %s", exc)
            return

        # Optional metadata dialog
        dialog = FileCardDialog(self.root, dest_name, project_path=self.project["path"])
        if dialog.result is None:
            # User cancelled – remove the copied file
            try:
                dest.unlink()
            except OSError:
                pass
            return

        new_file_item = {
            "id": str(uuid.uuid4()),
            "type": "file",
            "filename": dest_name,
            "title": dialog.result.get("title", "").strip() or dest_name,
            "text": dialog.result.get("text", ""),
            "keywords": dialog.result.get("keywords", ""),
            "color": dialog.result.get("color", "#e8f4fd"),
            "added": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "pos_x": 300 + len(self.project["data"]["items"]) * 30 % 400,
            "pos_y": 300,
        }
        self.project["data"]["items"].append(new_file_item)
        self.deselect_all_cards()
        self._create_file_card_gui(new_file_item)
        self.selected_source_ids.add(new_file_item["id"])
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        self.reset_zoom()
        self._update_minimap()
        logger.info("Datei-Karte hinzugefügt: %s", dest_name)

    def edit_file(self, item):
        """Metadaten einer Datei-Karte bearbeiten."""
        dialog = FileCardDialog(self.root, item["filename"], item, project_path=self.project["path"])
        if dialog.result is None:
            return
        item.update({
            "title": dialog.result.get("title", "").strip() or item["filename"],
            "text": dialog.result.get("text", ""),
            "keywords": dialog.result.get("keywords", ""),
            "color": dialog.result.get("color", item.get("color", "#e8f4fd")),
        })
        item_id = item["id"]
        frame, canvas_id = self.source_frames[item_id]
        self.canvas.delete(canvas_id)
        frame.destroy()
        del self.source_frames[item_id]
        del self.card_widgets[item_id]
        self._create_file_card_gui(item)
        self.save_project()
        self.update_last_mtime()
        self._update_minimap()
        logger.debug("Datei-Karte bearbeitet: %s", item_id)

    def _create_file_card_gui(self, item):
        """Erstellt eine Kachel für einen Datei-Anhang."""
        color = item.get("color") or "#e8f4fd"
        text_color = get_contrast_color(color)
        item["effective_color"] = color
        item_id = item["id"]
        style_name = f"File.{item_id}.TFrame"
        self.card_widgets[item_id] = {}

        try:
            self.root.style.configure(style_name, background=color)
        except tk.TclError:
            pass

        frame = ttk.Frame(self.canvas, padding="14")
        frame.item_data = item
        frame.unique_style_name = style_name
        frame.configure(style=style_name)
        frame.config(relief="raised", borderwidth=2)

        def on_enter(e, f=frame):
            if f.item_data["id"] not in self.selected_source_ids:
                f.config(borderwidth=3, relief="ridge")

        def on_leave(e, f=frame):
            if f.item_data["id"] not in self.selected_source_ids:
                f.config(borderwidth=2, relief="raised")

        # File type icon
        ext = Path(item.get("filename", "")).suffix.lower()
        icon_char = FILE_TYPE_ICONS.get(ext, "📎")
        icon_lbl = tk.Label(
            frame, text=icon_char,
            font=("Helvetica", self.base_icon_size),
            bg=color, fg=text_color,
        )
        icon_lbl.pack(anchor="w")
        self.card_widgets[item_id]["icon_label"] = icon_lbl
        self.card_widgets[item_id]["original_icon_data"] = {"is_favicon": False}

        # Title / filename
        title_lbl = ttk.Label(
            frame,
            text=item.get("title") or item["filename"],
            font=self.base_font_title,
            foreground=text_color, wraplength=280,
        )
        title_lbl.pack(anchor="w")
        self.card_widgets[item_id]["title_label"] = title_lbl

        # Text preview
        if item.get("text"):
            preview = item["text"][:180] + ("…" if len(item["text"]) > 180 else "")
            text_lbl = ttk.Label(
                frame, text=f"📝 {preview}",
                font=self.base_font_default, foreground=text_color, wraplength=300,
            )
            text_lbl.pack(anchor="w", pady=(4, 0))
            self.card_widgets[item_id]["text_label"] = text_lbl

        # Keywords
        if item.get("keywords"):
            kw_lbl = ttk.Label(
                frame,
                text=f"🏷 {self._wrap_keywords(item['keywords'])}",
                font=self.base_font_default, foreground=text_color, justify="left",
            )
            kw_lbl.pack(anchor="w", pady=(3, 0))
            self.card_widgets[item_id]["keywords_label"] = kw_lbl

        # Date
        added_lbl = ttk.Label(
            frame, text=f"📅 {item['added']}",
            font=("Helvetica", 8), foreground=text_color,
        )
        added_lbl.pack(anchor="w", pady=(6, 0))
        self.card_widgets[item_id]["added_label"] = added_lbl

        # Open button
        ttk.Button(
            frame, text="📂 Datei öffnen", bootstyle="info-outline", width=18,
            command=lambda i=item: self._open_file(i),
        ).pack(pady=(6, 0))

        # Bind events to all children
        for widget in [frame] + list(frame.winfo_children()):
            widget.bind("<Button-3>", lambda e, i=item: self.show_context_menu(e, i))
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            try:
                if isinstance(widget, (ttk.Label, tk.Label)):
                    widget.config(background=color, foreground=text_color)
            except Exception:
                pass

        frame.bind("<ButtonPress-1>", lambda e, iid=item_id: self.on_card_press(e, iid))
        frame.bind("<B1-Motion>", lambda e: self.on_card_motion(e))
        frame.bind("<ButtonRelease-1>", lambda e: self.on_card_release(e))

        x, y = item.get("pos_x", 300), item.get("pos_y", 300)
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

    def _open_file(self, item):
        """Öffnet eine Datei-Karte mit dem Standard-Programm."""
        files_dir = Path(self.project["path"]) / "files"
        filepath = files_dir / item.get("filename", "")
        if not filepath.exists():
            messagebox.showerror("Fehler", f"Datei nicht gefunden:\n{filepath}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(filepath))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(filepath)])
            else:
                subprocess.Popen(["xdg-open", str(filepath)])
        except Exception as exc:
            messagebox.showerror("Fehler", f"Datei konnte nicht geöffnet werden:\n{exc}")
            logger.error("Datei öffnen fehlgeschlagen: %s", exc)

    def _open_file_folder(self, item):
        """Öffnet den Ordner der Datei und wählt sie aus (wo möglich)."""
        files_dir = Path(self.project["path"]) / "files"
        filepath = files_dir / item.get("filename", "")
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", str(filepath)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(filepath)])
            else:
                subprocess.Popen(["xdg-open", str(files_dir)])
        except Exception as exc:
            messagebox.showerror("Fehler", f"Ordner konnte nicht geöffnet werden:\n{exc}")
            logger.error("Ordner öffnen fehlgeschlagen: %s", exc)

    def create_citation(self, source):
        fmt = self.app.project_manager.get_setting(
            "citation_format", "{url}, zuletzt aufgerufen am {added}"
        )
        try:
            citation = fmt.format_map({
                "url":      source.get("url", ""),
                "title":    source.get("title", ""),
                "added":    source.get("added", ""),
                "keywords": source.get("keywords", ""),
                "text":     source.get("text", ""),
            })
        except (KeyError, ValueError) as exc:
            logger.warning("Quellenangabe-Format ungültig (%s) — Fallback verwendet", exc)
            citation = f"{source.get('url', '')}, zuletzt aufgerufen am {source.get('added', '')}"
        pyperclip.copy(citation)
        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")
        logger.debug("Quellenangabe erstellt für: %s", source.get("url"))

    def shortcut_citation(self):
        if not self.selected_source_ids:
            return
        item_id = next(iter(self.selected_source_ids))
        item = next(
            (i for i in self.project["data"]["items"] if i["id"] == item_id), None
        )
        if item:
            self.create_citation(item)

    
    def update_scrollregion(self):
        self.canvas.update_idletasks()
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 500
            x1, y1, x2, y2 = bbox
            self.canvas.configure(
                scrollregion=(x1 - padding, y1 - padding, x2 + padding, y2 + padding)
            )
        else:
            self.canvas.configure(scrollregion=(-500, -500, 1000, 1000))
        self._update_minimap()

    def handle_external_data(self, data):
        threading.Thread(
            target=self._download_and_add_worker, args=(data,), daemon=True
        ).start()

    def _download_and_add_worker(self, data):
        url = data["url"]
        source_id = str(uuid.uuid4())
        logger.info("Externe Quelle wird geladen — url=%s", url)
        new_source = {
            "id": source_id, "type": "source", "url": url,
            "title": data.get("title", url), "text": data.get("text", ""),
            "keywords": data.get("keywords", ""), "color": "#ffffff",
            "added": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "pos_x": 300, "pos_y": 300, "favicon": "", "saved_pages": [],
        }

        project_dir = Path(self.project["path"])
        images_dir = project_dir / "images"
        sites_dir = project_dir / "sites"
        images_dir.mkdir(exist_ok=True)
        sites_dir.mkdir(exist_ok=True)

        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                html_content = response.text
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                html_filename = f"page_{source_id}_{timestamp}.html"
                with open(sites_dir / html_filename, "w", encoding="utf-8") as f:
                    f.write(html_content)
                new_source["saved_pages"].append(
                    {
                        "file": html_filename,
                        "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    }
                )
                try:
                    parsed_uri = urlparse(url)
                    base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    fav_resp = requests.get(
                        urljoin(base_url, "/favicon.ico"), timeout=5
                    )
                    if fav_resp.status_code == 200 and fav_resp.content:
                        fav_name = f"favicon_{source_id}.ico"
                        with open(images_dir / fav_name, "wb") as f:
                            f.write(fav_resp.content)
                        new_source["favicon"] = fav_name
                except requests.exceptions.RequestException as exc:
                    logger.debug("Favicon für externe Quelle nicht geladen: %s", exc)
        except requests.exceptions.RequestException as exc:
            logger.error("Externe Quelle konnte nicht geladen werden (%s): %s", url, exc)
        except OSError as exc:
            logger.error("IO-Fehler beim Speichern der externen Quelle: %s", exc)

        self.root.after(0, lambda: self._add_external_source_to_gui(new_source))

    def _add_external_source_to_gui(self, new_source):
        self.project["data"]["items"].append(new_source)
        offset = len(self.project["data"]["items"]) * 20
        new_source["pos_x"] = 300 + (offset % 500)
        new_source["pos_y"] = 300 + (offset // 500) * 100
        self.deselect_all_cards()
        self.selected_source_ids.add(new_source["id"])
        threading.Thread(
            target=self._concurrent_reload_single_card,
            args=(new_source,), daemon=True,
        ).start()
        self.save_project()
        self.update_last_mtime()
        self.update_scrollregion()
        logger.info("Externe Quelle hinzugefügt: %s", new_source["url"])

    def save_project(self):
        self.project["data"]["canvas_zoom_level"] = self.zoom_level
        self.project["data"]["selected_source_id"] = (
            next(iter(self.selected_source_ids)) if self.selected_source_ids else None
        )
        self.app.project_manager.save_specific_project_data(self.project)

    def start_auto_refresh(self):
        try:
            if self.shutting_down:
                return
            if self.dragging_card or self.dragging_canvas:
                self.root.after(3000, self.start_auto_refresh)
                return

            current_mtime = (
                os.path.getmtime(self.project["data_file"])
                if os.path.exists(self.project["data_file"])
                else 0
            )
            if current_mtime > self.last_file_mtime:
                logger.debug("Auto-Refresh ausgelöst — Datei hat sich geändert")
                self.reload_items()
                self.last_file_mtime = current_mtime
        except OSError as exc:
            logger.debug("Auto-Refresh mtime-Fehler: %s", exc)
        except Exception as exc:
            logger.warning("Auto-Refresh Fehler: %s", exc)

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
            logger.debug("Projekt neu geladen: %d Element(e)", len(items))
        except json.JSONDecodeError as exc:
            logger.error("Projektdatei beschädigt beim Reload: %s", exc)
        except OSError as exc:
            logger.error("Projektdatei nicht lesbar beim Reload: %s", exc)

    def back_to_projects(self):
        self.shutting_down = True
        self.save_project()
        self.executor.shutdown(wait=False)
        self.main_frame.destroy()
        self.app.close_project()
        logger.info("Zurück zur Projektliste")