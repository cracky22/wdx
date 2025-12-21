import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, simpledialog, filedialog
import datetime
from constants import APP_TITLE
import re
from constants import INVALID_CHARS

class MainWindow:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.root.iconbitmap("icon128.ico")
        self.project_manager = app.project_manager
        self.main_frame = ttk.Frame(self.root, padding="20", bootstyle="light")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        header_frame = ttk.Frame(self.main_frame, padding="10", bootstyle="primary")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)
        ttk.Button(header_frame, text="Neues Projekt", command=self.create_project, bootstyle="primary-outline", width=15).grid(row=0, column=0, padx=5)
        ttk.Button(header_frame, text="Projekt importieren", command=self.import_project, bootstyle="secondary-outline", width=15).grid(row=0, column=1, padx=5)
        ttk.Button(header_frame, text="Einstellungen", command=self.show_settings, bootstyle="info-outline", width=15).grid(row=0, column=2, padx=5)
        self.status_label = ttk.Label(header_frame, text="Keine Browser-Verbindung", bootstyle="danger")
        self.status_label.grid(row=0, column=3, padx=20)
        self.projects_frame = ttk.Frame(self.main_frame)
        self.projects_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.rowconfigure(1, weight=1)
        self.update_project_tiles()
        
    def show(self):
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def hide(self):
        self.main_frame.grid_forget()

    def show_settings(self):
        settings_window = ttk.Toplevel(self.root)
        settings_window.title("Einstellungen")
        settings_window.geometry("400x200")
        settings_window.transient(self.root)
        settings_window.grab_set()
        ttk.Label(settings_window, text="Dark Mode", font=("Helvetica", 12)).pack(pady=20)
        var = tk.BooleanVar(value=self.app.dark_mode)
        switch = ttk.Checkbutton(settings_window, text="Aktiviert", variable=var, bootstyle="round-toggle", command=lambda: self.app.toggle_theme())
        switch.pack(pady=10)
        ttk.Button(settings_window, text="Schließen", command=settings_window.destroy, bootstyle="secondary").pack(pady=20)

    def create_project(self):
        name = simpledialog.askstring("Neues Projekt", "Projektname:", parent=self.root)
        if not name:
            return
        description = simpledialog.askstring("Neues Projekt", "Projektbeschreibung:", parent=self.root)
        if description is None:
            return
        success, result = self.project_manager.create_project(name, description)
        if success:
            self.update_project_tiles()
        else:
            messagebox.showerror("Fehler", result)

    def import_project(self):
        file_path = filedialog.askopenfilename(filetypes=[("wdx Files", "*.wdx")])
        if file_path:
            success = self.project_manager.import_project(file_path)
            if success:
                self.update_project_tiles()
            else:
                messagebox.showerror("Fehler", "Import fehlgeschlagen.")
                
    def update_project_tiles(self):
        for widget in self.projects_frame.winfo_children():
            widget.destroy()

        for project in sorted(self.project_manager.projects, key=lambda p: p["last_modified"], reverse=True):
            tile = ttk.Frame(self.projects_frame, padding="20", relief="raised", borderwidth=2)
            tile.pack(fill="x", pady=10, padx=20)
            ttk.Label(tile, text=project["name"], font=("Helvetica", 16, "bold")).pack(anchor="w")
            ttk.Label(tile, text=project["description"], font=("Helvetica", 10)).pack(anchor="w", pady=(5,0))
            ttk.Label(tile, text=f"Zuletzt geändert: {project['last_modified'][:16].replace('T', ' ')}", font=("Helvetica", 8), foreground="gray").pack(anchor="w")
            btn_frame = ttk.Frame(tile)
            btn_frame.pack(anchor="e", pady=10)
            ttk.Button(btn_frame, text="Öffnen", command=lambda p=project: self.app.open_project(p), bootstyle="primary").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Umbenennen", command=lambda p=project: self.rename_project(p), bootstyle="secondary-outline").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Beschreibung ändern", command=lambda p=project: self.edit_project(p), bootstyle="secondary-outline").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Exportieren", command=lambda p=project: self.export_project(p), bootstyle="info-outline").pack(side="left", padx=5)
            ttk.Button(btn_frame, text="Löschen", command=lambda p=project: self.delete_project(p), bootstyle="danger-outline").pack(side="left", padx=5)

    def rename_project(self, project):
        new_name = simpledialog.askstring("Umbenennen", "Neuer Name:", initialvalue=project["name"], parent=self.root)
        if new_name and new_name != project["name"] and re.search(INVALID_CHARS, new_name) is None:
            success, error = self.project_manager.rename_project(project, new_name)
            if success:
                self.update_project_tiles()
            else:
                messagebox.showerror("Fehler", error)

    def edit_project(self, project):
        new_desc = simpledialog.askstring("Bearbeiten", "Neue Projektbeschreibung:", initialvalue=project["description"], parent=self.root)
        if new_desc is not None:
            self.project_manager.edit_project_description(project, new_desc)
            self.update_project_tiles()

    def delete_project(self, project):
        if messagebox.askyesno("Bestätigen", f"Projekt '{project['name']}' löschen?", parent=self.root):
            self.project_manager.delete_project(project)
            self.update_project_tiles()

    def export_project(self, project):
        success, file_path = self.project_manager.export_project(project)
        if success:
            messagebox.showinfo("Erfolg", f"Projekt als '{file_path}' exportiert.")

    def show(self):
        self.main_frame.grid()

    def hide(self):
        self.main_frame.grid_remove()