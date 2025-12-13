import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, simpledialog
import datetime
from constants import APP_TITLE

class MainWindow:
    def __init__(self, root, app):
        self.root = root
        self.app = app
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
        ttk.Label(header_frame, text=APP_TITLE, font=("Helvetica", 16, "bold"), bootstyle="inverse-primary").grid(row=0, column=2, sticky=tk.E)

        self.status_label = ttk.Label(header_frame, text="Keine Browser-Verbindung", font=("Helvetica", 10), bootstyle="danger")
        self.status_label.grid(row=1, column=2, sticky=tk.E, pady=5)

        self.canvas = tk.Canvas(self.main_frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round")
        self.project_frame = ttk.Frame(self.canvas, padding="10")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        self.project_window = self.canvas.create_window((0, 0), window=self.project_frame, anchor="nw")
        self.project_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._resize_canvas)

        self.update_project_tiles()

    def _resize_canvas(self, event):
        self.canvas.itemconfig(self.project_window, width=event.width)

    def update_project_tiles(self):
        for widget in self.project_frame.winfo_children():
            widget.destroy()
        for idx, project in enumerate(self.project_manager.projects):
            tile = ttk.Frame(self.project_frame, padding="15", bootstyle="info", relief="flat", borderwidth=2)
            tile.grid(row=idx, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
            tile.columnconfigure(0, weight=1)

            ttk.Label(tile, text=f"📋 {project['name']}", font=("Helvetica", 14, "bold"), bootstyle="inverse-info").grid(row=0, column=0, sticky=tk.W, pady=2)
            ttk.Label(tile, text=project["description"], wraplength=400, font=("Helvetica", 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
            ttk.Label(tile, text=f"📅 Erstellt: {project['created']}", font=("Helvetica", 10)).grid(row=2, column=0, sticky=tk.W, pady=2)
            last_modified = datetime.datetime.fromisoformat(project["last_modified"])
            now = datetime.datetime.now()
            minutes = (now - last_modified).total_seconds() / 60
            time_str = f"{int(minutes)} Minuten" if minutes < 60 else f"{int(minutes // 60)} Stunden"
            ttk.Label(tile, text=f"🕒 Bearbeitet: {time_str} her", font=("Helvetica", 10)).grid(row=3, column=0, sticky=tk.W, pady=2)

            menu_button = ttk.Menubutton(tile, text="⋮", bootstyle="dark-outline", width=3)
            menu_button.grid(row=0, column=1, sticky=tk.E)
            menu = tk.Menu(menu_button, tearoff=0, font=("Helvetica", 10))
            menu.add_command(label="✏️ Umbenennen", command=lambda p=project: self.rename_project(p))
            menu.add_command(label="📝 Bearbeiten", command=lambda p=project: self.edit_project(p))
            menu.add_command(label="💾 Exportieren", command=lambda p=project: self.export_project(p))
            menu.add_command(label="🗑️ Löschen", command=lambda p=project: self.delete_project(p))
            menu_button["menu"] = menu

            tile.bind("<Double-1>", lambda e, p=project: self.app.open_project(p))
            for child in tile.winfo_children():
                child.bind("<Double-1>", lambda e, p=project: self.app.open_project(p))

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
        success, project = self.project_manager.import_project()
        if success:
            self.update_project_tiles()

    def rename_project(self, project):
        new_name = simpledialog.askstring("Umbenennen", "Neuer Projektname:", initialvalue=project["name"], parent=self.root)
        if new_name and new_name != project["name"]:
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