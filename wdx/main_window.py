import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, simpledialog, filedialog
import re
import math
import time

from constants import INVALID_CHARS
from wdx_logger import get_logger

logger = get_logger(__name__)

DEFAULT_CITATION_FORMAT = "{url}, zuletzt aufgerufen am {added}"

CITATION_PLACEHOLDERS_HELP = (
    "Verfügbare Platzhalter:\n"
    "  {url}       — URL der Quelle\n"
    "  {title}     — Titel der Seite\n"
    "  {added}     — Datum & Uhrzeit des Hinzufügens\n"
    "  {keywords}  — Schlagwörter\n"
    "  {text}      — Textauszug\n\n"
    "Beispiel:\n"
    "  {title}. {url}, zuletzt aufgerufen am {added}."
)


class MainWindow:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        try:
            self.root.iconbitmap("icon128.ico")
        except Exception as exc:
            logger.debug("App-Icon konnte nicht gesetzt werden: %s", exc)
        self.project_manager = app.project_manager

        self.main_frame = ttk.Frame(self.root, padding="20", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        header = ttk.Frame(self.main_frame, padding="10", bootstyle="primary")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.columnconfigure(1, weight=1)

        ttk.Button(
            header, text="Neues Projekt", command=self.create_project,
            bootstyle="info", width=15,
        ).grid(row=0, column=0, padx=5)
        ttk.Button(
            header, text="Projekt importieren", command=self.import_project,
            bootstyle="info-outline", width=15,
        ).grid(row=0, column=1, padx=5)
        ttk.Button(
            header, text="Einstellungen", command=self.show_settings,
            bootstyle="secondary", width=15,
        ).grid(row=0, column=2, padx=5)

        self.status_label = ttk.Label(
            header, text="Keine Browser-Verbindung", bootstyle="danger"
        )
        self.status_label.grid(row=0, column=3, padx=20)

        self.projects_frame = ttk.Frame(self.main_frame)
        self.projects_frame.grid(row=1, column=0, sticky="nsew")
        self.main_frame.rowconfigure(1, weight=1)

        self.update_project_tiles()

    
    def set_browser_connected(self, connected: bool = True):
        if connected:
            self.status_label.config(text="Browser verbunden", bootstyle="success")
            if hasattr(self, "_status_timer"):
                self.root.after_cancel(self._status_timer)
            self._status_timer = self.root.after(
                10000, lambda: self.set_browser_connected(False)
            )
            logger.debug("Browser-Verbindung aktiv")
        else:
            self.status_label.config(
                text="Keine Browser-Verbindung", bootstyle="danger"
            )

    def format_size(self, size_bytes: int) -> str:
        if size_bytes <= 0:
            return "0 B"
        units = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        s = round(size_bytes / math.pow(1024, i), 2)
        return f"{s} {units[i]}"

    def refresh_and_update(self):
        for project in self.project_manager.projects:
            project["size"] = self.project_manager._get_dir_size(project["path"])
        self.update_project_tiles()

    def update_project_tiles(self):
        for widget in self.projects_frame.winfo_children():
            widget.destroy()

        for project in sorted(
            self.project_manager.projects,
            key=lambda p: p["last_modified"],
            reverse=True,
        ):
            tile = ttk.Frame(
                self.projects_frame, padding="20", relief="raised", borderwidth=2
            )
            tile.pack(fill="x", pady=10, padx=20)

            ttk.Label(
                tile, text=project["name"], font=("Helvetica", 16, "bold")
            ).pack(anchor="w")
            ttk.Label(
                tile, text=project["description"], font=("Helvetica", 10)
            ).pack(anchor="w", pady=(5, 0))

            size_str = self.format_size(project.get("size", 0))
            last_mod = project["last_modified"][:16].replace("T", " ")
            ttk.Label(
                tile,
                text=f"Zuletzt geändert: {last_mod}  |  Dateigröße: {size_str}",
                font=("Helvetica", 8),
                foreground="gray",
            ).pack(anchor="w")

            btn_frame = ttk.Frame(tile)
            btn_frame.pack(anchor="e", pady=10)
            ttk.Button(
                btn_frame, text="Öffnen",
                command=lambda p=project: self.app.open_project(p),
                bootstyle="primary",
            ).pack(side="left", padx=5)
            ttk.Button(
                btn_frame, text="Umbenennen",
                command=lambda p=project: self.rename_project(p),
                bootstyle="secondary-outline",
            ).pack(side="left", padx=5)
            ttk.Button(
                btn_frame, text="Exportieren",
                command=lambda p=project: self.export_project(p),
                bootstyle="info-outline",
            ).pack(side="left", padx=5)
            ttk.Button(
                btn_frame, text="Löschen",
                command=lambda p=project: self.delete_project(p),
                bootstyle="danger-outline",
            ).pack(side="left", padx=5)

    
    def show_settings(self):
        win = ttk.Toplevel(self.root)
        win.title("Einstellungen")
        win.geometry("560x780")
        try:
            win.iconbitmap("icon128.ico")
        except Exception:
            pass
        win.grab_set()
        win.focus_set()
        win.bind("<Escape>", lambda e: win.destroy())

        # ── Design ───────────────────────────────────────────────────────────
        ttk.Label(win, text="Design", font=("Helvetica", 12, "bold")).pack(pady=(20, 5))
        var_dark = tk.BooleanVar(value=self.app.dark_mode)
        ttk.Checkbutton(
            win, text="Dark Mode", variable=var_dark,
            bootstyle="round-toggle",
            command=lambda: self.app.toggle_theme(),
        ).pack(pady=5)
        ttk.Separator(win).pack(fill="x", pady=15, padx=20)

        # ── Verhalten ────────────────────────────────────────────────────────
        ttk.Label(win, text="Verhalten", font=("Helvetica", 12, "bold")).pack(pady=5)
        current_prompts = self.app.project_manager.get_setting("show_prompts", True)
        var_prompts = tk.BooleanVar(value=current_prompts)

        def toggle_prompts():
            self.app.project_manager.set_setting("show_prompts", var_prompts.get())

        ttk.Checkbutton(
            win, text="Meldungen & Bestätigungen anzeigen",
            variable=var_prompts, bootstyle="round-toggle",
            command=toggle_prompts,
        ).pack(pady=5)
        ttk.Separator(win).pack(fill="x", pady=15, padx=20)

        # ── Verschlüsselungs-Passwort ─────────────────────────────────────
        ttk.Label(
            win, text="Verschlüsselungs-Passwort", font=("Helvetica", 12, "bold")
        ).pack(pady=5)
        ttk.Label(win, text="Für den Export von .wdx Dateien:", font=("Helvetica", 9)).pack()
        pwd_frame = ttk.Frame(win)
        pwd_frame.pack(pady=10)
        current_pwd = self.app.project_manager.get_setting("encryption_password", "")
        pwd_var = tk.StringVar(value=current_pwd)
        entry_pwd = ttk.Entry(pwd_frame, textvariable=pwd_var, show="*", width=30)
        entry_pwd.pack(side="left", padx=5)

        self.pwd_visible = False

        def toggle_pwd_viz():
            self.pwd_visible = not self.pwd_visible
            entry_pwd.config(show="" if self.pwd_visible else "*")

        ttk.Button(
            pwd_frame, text="👁", width=3, bootstyle="secondary-outline",
            command=toggle_pwd_viz,
        ).pack(side="left")

        ttk.Separator(win).pack(fill="x", pady=15, padx=20)

        # ── Quellenangabe-Format ──────────────────────────────────────────
        ttk.Label(
            win, text="Quellenangabe-Format", font=("Helvetica", 12, "bold")
        ).pack(pady=(5, 2))

        ttk.Label(
            win,
            text=CITATION_PLACEHOLDERS_HELP,
            font=("Courier", 8),
            justify="left",
            foreground="gray",
        ).pack(padx=25, anchor="w")

        citation_frame = ttk.Frame(win)
        citation_frame.pack(fill="x", padx=20, pady=(8, 5))

        current_citation_fmt = self.app.project_manager.get_setting(
            "citation_format", DEFAULT_CITATION_FORMAT
        )
        citation_var = tk.StringVar(value=current_citation_fmt)
        citation_entry = ttk.Entry(citation_frame, textvariable=citation_var, width=55)
        citation_entry.pack(side="left", fill="x", expand=True)

        def reset_citation_format():
            citation_var.set(DEFAULT_CITATION_FORMAT)

        ttk.Button(
            citation_frame, text="↺", width=3, bootstyle="secondary-outline",
            command=reset_citation_format,
        ).pack(side="left", padx=(5, 0))

        ttk.Separator(win).pack(fill="x", pady=20, padx=20)

        # ── Speichern ────────────────────────────────────────────────────────
        def save_settings_manual():
            self.app.project_manager.set_setting(
                "encryption_password", pwd_var.get()
            )
            self.app.project_manager.set_setting("show_prompts", var_prompts.get())

            fmt = citation_var.get().strip()
            if not fmt:
                fmt = DEFAULT_CITATION_FORMAT
            self.app.project_manager.set_setting("citation_format", fmt)

            self.app.project_manager.save_settings()
            logger.info("Einstellungen gespeichert")
            win.destroy()

        ttk.Button(
            win, text="Speichern & Schließen",
            command=save_settings_manual, bootstyle="primary",
        ).pack(pady=10)

    def _should_show_prompts(self) -> bool:
        return self.app.project_manager.get_setting("show_prompts", True)

    # ------------------------------------------------------------------
    def create_project(self):
        name = simpledialog.askstring("Neues Projekt", "Projektname (Titel):", parent=self.root)
        if name:
            self.root.after(200, lambda: self.ask_desc(name))

    def ask_desc(self, name):
        desc = simpledialog.askstring("Neues Projekt", "Beschreibung:", parent=self.root)
        success, res = self.project_manager.create_project(name, desc or "")
        if success:
            self.update_project_tiles()
            logger.info("Projekt erstellt: %s", name)
        else:
            messagebox.showerror("Fehler", res)

    def import_project(self):
        path = filedialog.askopenfilename(
            filetypes=[("wdx Projektdatei", "*.wdx")]
        )
        if path:
            if self.project_manager.import_project(path):
                self.update_project_tiles()
                logger.info("Projekt importiert von: %s", path)

    def rename_project(self, project):
        """Öffnet einen Dialog zum Umbenennen von Name und Beschreibung."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Projekt bearbeiten")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)
        try:
            dialog.iconbitmap("icon128.ico")
        except Exception:
            pass

        main = ttk.Frame(dialog, padding=20)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Name:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        name_var = tk.StringVar(value=project["name"])
        name_entry = ttk.Entry(main, textvariable=name_var, width=45)
        name_entry.pack(fill="x", pady=(0, 12))

        ttk.Label(main, text="Beschreibung:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        desc_var = tk.StringVar(value=project["description"])
        desc_entry = ttk.Entry(main, textvariable=desc_var, width=45)
        desc_entry.pack(fill="x", pady=(0, 20))

        result = {"confirmed": False}

        def confirm():
            result["confirmed"] = True
            dialog.destroy()

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Abbrechen", command=dialog.destroy,
                   bootstyle="secondary-outline").pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Speichern", command=confirm,
                   bootstyle="primary", width=12).pack(side="right")

        dialog.bind("<Return>", lambda e: confirm())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        name_entry.focus_set()
        self.root.wait_window(dialog)

        if not result["confirmed"]:
            return

        new_name = name_var.get().strip()
        new_desc = desc_var.get().strip()

        if not new_name:
            messagebox.showerror("Fehler", "Name darf nicht leer sein.")
            return

        if re.search(INVALID_CHARS, new_name):
            messagebox.showerror("Fehler", "Ungültige Zeichen im Projektnamen.")
            logger.warning("Umbenennen abgelehnt — ungültige Zeichen in '%s'", new_name)
            return

        success, err = self.project_manager.rename_project(
            project, new_name, new_description=new_desc
        )
        if success:
            self.update_project_tiles()
        else:
            messagebox.showerror("Fehler", err)

    def delete_project(self, project):
        confirm = True
        if self._should_show_prompts():
            confirm = messagebox.askyesno(
                "Löschen", f"'{project['name']}' wirklich löschen?"
            )
        if confirm:
            self.project_manager.delete_project(project)
            self.update_project_tiles()

    def export_project(self, project):
        success, path = self.project_manager.export_project(project)
        if success and self._should_show_prompts():
            messagebox.showinfo("Erfolg", f"Exportiert nach: {path}")

    def show(self):
        self.main_frame.grid()

    def hide(self):
        self.main_frame.grid_remove()