import json
import shutil
from pathlib import Path
from tkinter import messagebox, filedialog
from zipfile import ZipFile
import datetime
import re
import threading
from constants import WDX_DIR, PROJECTS_FILE, INVALID_CHARS

class ProjectManager:
    def __init__(self):
        self.lock = threading.Lock()
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
                        try:
                            with open(data_file, "r", encoding="utf-8") as f:
                                proj["data"] = json.load(f)
                            proj["path"] = project_path
                            proj["data_file"] = data_file
                            self.projects.append(proj)
                        except Exception:
                            print(f"Konnte Projektdaten für {proj.get('name')} nicht laden.")
            except json.JSONDecodeError:
                messagebox.showwarning(
                    "Warnung", "projects.json ist beschädigt. Initialisiere neue Datei."
                )

    def save_projects(self):
        with self.lock:
            projects_data = []
            for project in self.projects:
                projects_data.append(
                    {
                        "name": project["name"],
                        "description": project["description"],
                        "created": project["created"],
                        "last_modified": project["last_modified"],
                        "path": str(project["path"]),
                        "data_file": str(project["data_file"]),
                    }
                )
            try:
                with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(projects_data, f, indent=4)
            except Exception as e:
                print(f"Fehler beim Speichern der Projektliste: {e}")

    def save_specific_project_data(self, project):
        with self.lock:
            try:
                with open(project["data_file"], "w", encoding="utf-8") as f:
                    json.dump(project["data"], f, indent=4)
                project["last_modified"] = datetime.datetime.now().isoformat()
            except Exception as e:
                print(f"Fehler beim Speichern von {project['name']}: {e}")
        self.save_projects()

    def update_project_file_safe(self, project, update_callback):
        with self.lock:
            try:
                with open(project["data_file"], "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                update_callback(data)
                with open(project["data_file"], "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                
                project["data"] = data
                project["last_modified"] = datetime.datetime.now().isoformat()
            except Exception as e:
                print(f"Fehler beim sicheren Update: {e}")
        self.save_projects()

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
                "items": [],
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
                "data": initial_data,
            }
            self.projects.append(new_project)
            self.save_projects()
            return True, new_project

        except Exception as e:
            return False, str(e)

    def import_project(self, file_path):
        try:
            with ZipFile(file_path, "r") as zip_ref:
                for name in zip_ref.namelist():
                    if name.startswith("/") or ".." in name:
                        return False

                if "project.json" not in zip_ref.namelist():
                    return False

                with zip_ref.open("project.json") as f:
                    data = json.load(f)
                    name = data.get("name", "Imported Project")

                original_name = name
                counter = 1
                while (WDX_DIR / name).exists():
                    name = f"{original_name}_{counter}"
                    counter += 1

                target_dir = WDX_DIR / name
                target_dir.mkdir(parents=True)
                zip_ref.extractall(target_dir)
                
                data_file = target_dir / "project.json"
                
                if name != original_name:
                    with open(data_file, "r", encoding="utf-8") as f:
                        pj_data = json.load(f)
                    pj_data["name"] = name
                    with open(data_file, "w", encoding="utf-8") as f:
                        json.dump(pj_data, f, indent=4)

                new_proj = {
                    "name": name,
                    "description": data.get("description", ""),
                    "created": data.get("created", datetime.datetime.now().isoformat()),
                    "last_modified": datetime.datetime.now().isoformat(),
                    "path": target_dir,
                    "data_file": data_file,
                }
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
        
        try:
            project["path"].rename(new_path)
            project["name"] = new_name
            project["path"] = new_path
            project["data_file"] = new_path / "project.json"
            project["data"]["name"] = new_name
            
            with self.lock:
                with open(project["data_file"], "w", encoding="utf-8") as f:
                    json.dump(project["data"], f, indent=4)
            
            self.save_projects()
            return True, None
        except OSError as e:
            return False, f"Fehler beim Umbenennen (Datei geöffnet?): {e}"

    def edit_project_description(self, project, new_desc):
        project["description"] = new_desc
        project["data"]["description"] = new_desc
        self.save_specific_project_data(project)

    def delete_project(self, project):
        try:
            shutil.rmtree(project["path"])
            self.projects.remove(project)
            self.save_projects()
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Projekt nicht löschen: {e}")

    def export_project(self, project):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".wdx",
            filetypes=[("wdx Files", "*.wdx")],
            initialfile=f"{project['name']}.wdx",
        )
        if file_path:
            base_name = file_path.replace(".wdx", "")
            shutil.make_archive(base_name, "zip", project["path"])
            shutil.move(base_name + ".zip", file_path)
            return True, file_path
        return False, None