import json
import shutil
from pathlib import Path
from tkinter import messagebox, filedialog
from zipfile import ZipFile
import datetime
import re
import threading  # NEU
from constants import WDX_DIR, PROJECTS_FILE, INVALID_CHARS

class ProjectManager:
    def __init__(self):
        self.lock = threading.Lock()  # NEU: Thread-Lock
        self.projects = []
        self.load_projects()

    def load_projects(self):
        self.projects = []
        if PROJECTS_FILE.exists():
            try:
                with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                    projects_data = json.load(f)
                for proj in projects_data:
                    project_path = Path(proj["path"])
                    data_file = Path(proj["data_file"])
                    if data_file.exists():
                        with open(data_file, "r", encoding="utf-8") as f:
                            proj["data"] = json.load(f)
                        proj["path"] = project_path
                        proj["data_file"] = data_file
                        self.projects.append(proj)
            except json.JSONDecodeError:
                messagebox.showwarning("Warnung", "projects.json ist beschädigt. Initialisiere neue Datei.")

    def save_projects(self):
        with self.lock:  # NEU: Thread-safe Block
            projects_data = []
            for project in self.projects:
                projects_data.append({
                    "name": project["name"],
                    "description": project["description"],
                    "created": project["created"],
                    "last_modified": project["last_modified"],
                    "path": str(project["path"]),
                    "data_file": str(project["data_file"])
                })
            try:
                with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(projects_data, f, indent=4)
            except Exception as e:
                print(f"Fehler beim Speichern der Projektliste: {e}")

    def create_project(self, name, description):
        project_dir = WDX_DIR / name
        if project_dir.exists():
            return False, "Ein Projekt mit diesem Namen existiert bereits!"
        
        try:
            project_dir.mkdir(parents=True)
            data_file = project_dir / "project.json"
            
            initial_data = {
                "name": name,
                "description": description,
                "created": datetime.datetime.now().isoformat(),
                "last_modified": datetime.datetime.now().isoformat(),
                "items": []
            }

            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4)

            new_project = {
                "name": name,
                "description": description,
                "created": initial_data["created"],
                "last_modified": initial_data["last_modified"],
                "path": project_dir,
                "data_file": data_file,
                "data": initial_data
            }
            
            self.projects.append(new_project)
            self.save_projects()
            return True, new_project

        except Exception as e:
            return False, str(e)

    def import_project(self, file_path):
        #file_path = filedialog.askopenfilename(filetypes=[("Zip Files", "*.zip"), ("wdx Files", "*.wdx")])
        #if not file_path:
        #    return False
            
        try:
            with ZipFile(file_path, 'r') as zip_ref:
                # Prüfen ob project.json enthalten ist
                if "project.json" not in zip_ref.namelist():
                    return False
                
                # Temporär entpacken um Namen zu lesen
                with zip_ref.open("project.json") as f:
                    data = json.load(f)
                    name = data.get("name", "Imported Project")
                
                # Namenskollision vermeiden
                original_name = name
                counter = 1
                while (WDX_DIR / name).exists():
                    name = f"{original_name}_{counter}"
                    counter += 1
                
                target_dir = WDX_DIR / name
                target_dir.mkdir(parents=True)
                zip_ref.extractall(target_dir)
                
                # Pfade im geladenen JSON anpassen falls nötig (hier laden wir neu)
                self.load_projects() # Reload um sicher zu gehen oder manuell hinzufügen
                
                # Manuell hinzufügen, da load_projects nur die projects.json liest, 
                # und der Import dort noch nicht drin steht.
                
                # Fix: Wir müssen das importierte Projekt sauber registrieren
                data_file = target_dir / "project.json"
                
                # Ggf. Name in der project.json anpassen falls Ordner umbenannt wurde
                if name != original_name:
                    with open(data_file, "r", encoding="utf-8") as f:
                        pj_data = json.load(f)
                    pj_data["name"] = name
                    with open(data_file, "w", encoding="utf-8") as f:
                        json.dump(pj_data, f, indent=4)

                # Projekt zur Liste hinzufügen
                new_proj = {
                    "name": name,
                    "description": data.get("description", ""),
                    "created": data.get("created", datetime.datetime.now().isoformat()),
                    "last_modified": datetime.datetime.now().isoformat(),
                    "path": target_dir,
                    "data_file": data_file,
                    "data": data 
                }
                # Data neu laden, da wir es oben ggf geändert haben
                with open(data_file, "r", encoding="utf-8") as f:
                     new_proj["data"] = json.load(f)

                self.projects.append(new_proj)
                self.save_projects()
                
                return True
        except Exception as e:
            messagebox.showerror("Import Fehler", str(e))
            return False

    def rename_project(self, project, new_name):
        new_path = WDX_DIR / new_name
        if new_path.exists():
            return False, "Projektname existiert bereits!"
        project["path"].rename(new_path)
        project["name"] = new_name
        project["path"] = new_path
        project["data_file"] = new_path / "project.json"
        project["data"]["name"] = new_name
        with open(project["data_file"], "w", encoding="utf-8") as f:
            json.dump(project["data"], f, indent=4)
        self.save_projects()
        return True, None

    def edit_project_description(self, project, new_desc):
        project["description"] = new_desc
        project["data"]["description"] = new_desc
        project["last_modified"] = datetime.datetime.now().isoformat()
        with open(project["data_file"], "w", encoding="utf-8") as f:
            json.dump(project["data"], f, indent=4)
        self.save_projects()

    def delete_project(self, project):
        shutil.rmtree(project["path"])
        self.projects.remove(project)
        self.save_projects()

    def export_project(self, project):
        file_path = filedialog.asksaveasfilename(defaultextension=".wdx", filetypes=[("wdx Files", "*.wdx")], initialfile=f"{project['name']}.wdx")
        if file_path:
            shutil.make_archive(file_path.replace(".wdx", ""), 'zip', project["path"])
            shutil.move(file_path.replace(".wdx", ".zip"), file_path)
            return True, file_path
        return False, None