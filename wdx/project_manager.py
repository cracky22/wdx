import json
import shutil
import os
from pathlib import Path
from tkinter import messagebox, filedialog
import pyzipper
import datetime
import threading
import winreg
from constants import WDX_DIR, PROJECTS_FILE, CODENAME

class ProjectManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.projects = []
        self.load_projects()

    def _get_dir_size(self, path):
        total_size = 0
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return 0
            with os.scandir(path_obj) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            # Korrektur: st_size statt size
                            total_size += entry.stat().st_size
                        elif entry.is_dir(follow_symlinks=False):
                            total_size += self._get_dir_size(entry.path)
                    except (PermissionError, OSError):
                        continue
        except Exception as e:
            print(f"Fehler bei Größenberechnung für {path}: {e}")
        return total_size

    def get_registry_password(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\wdx", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "ExportPassword")
            winreg.CloseKey(key)
            return value if value else CODENAME
        except FileNotFoundError:
            return CODENAME
        except Exception:
            return CODENAME

    def load_projects(self):
        self.projects = []
        if not PROJECTS_FILE.exists():
            return

        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                projects_data = json.load(f)
            
            for proj in projects_data:
                try:
                    p_path = Path(proj["path"])
                    d_file = Path(proj["data_file"])

                    if d_file.exists():
                        with open(d_file, "r", encoding="utf-8") as f:
                            actual_data = json.load(f)
                        
                        project_entry = {
                            "name": actual_data.get("name", proj["name"]),
                            "description": actual_data.get("description", proj["description"]),
                            "created": actual_data.get("created", proj["created"]),
                            "last_modified": actual_data.get("last_modified", proj["last_modified"]),
                            "path": p_path,
                            "data_file": d_file,
                            "data": actual_data,
                            "size": self._get_dir_size(p_path)
                        }
                        self.projects.append(project_entry)
                    else:
                        print(f"Überspringe: {proj.get('name')}, Datei nicht gefunden.")
                except Exception as e:
                    print(f"Fehler beim Laden von {proj.get('name')}: {e}")
        except Exception as e:
            print(f"Kritischer Fehler in load_projects: {e}")

    def save_projects(self):
        with self.lock:
            projects_data = []
            for project in self.projects:
                projects_data.append({
                    "name": project["name"],
                    "description": project["description"],
                    "created": project["created"],
                    "last_modified": project["last_modified"],
                    "path": str(project["path"]),
                    "data_file": str(project["data_file"]),
                })
            try:
                with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(projects_data, f, indent=4)
            except Exception as e:
                print(f"Save Error: {e}")

    def save_specific_project_data(self, project):
        with self.lock:
            try:
                project["last_modified"] = datetime.datetime.now().isoformat()
                with open(project["data_file"], "w", encoding="utf-8") as f:
                    json.dump(project["data"], f, indent=4)
                project["size"] = self._get_dir_size(project["path"])
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
                project["size"] = self._get_dir_size(project["path"])
            except Exception as e:
                print(f"Update Fehler: {e}")
        self.save_projects()

    def create_project(self, name, description):
        project_dir = WDX_DIR / name
        if project_dir.exists():
            return False, "Name existiert bereits!"
        try:
            project_dir.mkdir(parents=True)
            data_file = project_dir / "project.json"
            now = datetime.datetime.now().isoformat()
            initial_data = {
                "name": name,
                "description": description,
                "created": now,
                "last_modified": now,
                "items": [],
            }
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4)
            
            new_project = {
                "name": name, "description": description, "created": now,
                "last_modified": now, "path": project_dir, "data_file": data_file,
                "data": initial_data, "size": self._get_dir_size(project_dir)
            }
            self.projects.append(new_project)
            self.save_projects()
            return True, new_project
        except Exception as e:
            return False, str(e)

    def import_project(self, file_path):
        try:
            pwd = self.get_registry_password()
            with pyzipper.AESZipFile(file_path, "r") as zip_ref:
                if pwd: zip_ref.setpassword(pwd.encode('utf-8'))
                namelist = zip_ref.namelist()
                if "project.json" not in namelist: return False
                
                with zip_ref.open("project.json") as f:
                    data = json.load(f)
                
                name = data.get("name", "Import")
                original_name = name
                counter = 1
                while (WDX_DIR / name).exists():
                    name = f"{original_name}_{counter}"
                    counter += 1

                target_dir = WDX_DIR / name
                target_dir.mkdir(parents=True)
                zip_ref.extractall(target_dir)
                
                data_file = target_dir / "project.json"
                data["name"] = name
                with open(data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

                new_proj = {
                    "name": name, "description": data.get("description", ""),
                    "created": data.get("created", datetime.datetime.now().isoformat()),
                    "last_modified": datetime.datetime.now().isoformat(),
                    "path": target_dir, "data_file": data_file, "data": data,
                    "size": self._get_dir_size(target_dir)
                }
                self.projects.append(new_proj)
                self.save_projects()
                return True
        except Exception as e:
            messagebox.showerror("Import Fehler", str(e))
            return False

    def rename_project(self, project, new_name):
        new_path = WDX_DIR / new_name
        if new_path.exists(): return False, "Existiert bereits!"
        try:
            project["path"].rename(new_path)
            project["name"] = new_name
            project["path"] = new_path
            project["data_file"] = new_path / "project.json"
            project["data"]["name"] = new_name
            with open(project["data_file"], "w", encoding="utf-8") as f:
                json.dump(project["data"], f, indent=4)
            self.save_projects()
            return True, None
        except Exception as e:
            return False, str(e)

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
            messagebox.showerror("Fehler", str(e))

    def export_project(self, project):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".wdx", initialfile=f"{project['name']}.wdx"
        )
        if file_path:
            pwd = self.get_registry_password()
            try:
                with pyzipper.AESZipFile(file_path, 'w', compression=pyzipper.ZIP_DEFLATED, 
                                         encryption=pyzipper.WZ_AES if pwd else None) as zf:
                    if pwd: zf.setpassword(pwd.encode('utf-8'))
                    for root, _, files in os.walk(project["path"]):
                        for file in files:
                            full_p = Path(root) / file
                            zf.write(full_p, full_p.relative_to(project["path"]))
                return True, file_path
            except Exception: return False, None
        return False, None