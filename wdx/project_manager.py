import json
import shutil
from pathlib import Path
from tkinter import messagebox, filedialog
from zipfile import ZipFile
import datetime
import re
from constants import WDX_DIR, PROJECTS_FILE, INVALID_CHARS

class ProjectManager:
    def __init__(self):
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
        projects_data = []
        for project in self.projects:
            projects_data.append({
                "name": project["name"],
                "description": project["description"],
                "created": project["created"],
                "last_modified": project["last_modified"],
                "path": str(project["path"]),
                "data_file": str(project["data_file"]),
                "data": project["data"]
            })
        WDX_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(projects_data, f, indent=4, ensure_ascii=False)

    def create_project(self, name, description):
        if re.search(INVALID_CHARS, name):
            return False, "Ungültige Zeichen im Projektnamen!"
        project_path = WDX_DIR / name
        if project_path.exists():
            return False, "Projekt existiert bereits!"
        project_path.mkdir(parents=True)
        (project_path / "images").mkdir(exist_ok=True)
        (project_path / "sites").mkdir(exist_ok=True)
        project_data = {
            "name": name,
            "description": description or "",
            "sources": [],
            "created": datetime.datetime.now().isoformat()
        }
        data_file = project_path / "project.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=4)
        project = {
            "name": name,
            "description": description or "",
            "created": project_data["created"],
            "last_modified": project_data["created"],
            "path": project_path,
            "data_file": data_file,
            "data": project_data
        }
        self.projects.append(project)
        self.save_projects()
        return True, project

    def import_project(self):
        file_path = filedialog.askopenfilename(filetypes=[("WDX Files", "*.wdx")])
        if not file_path:
            return False, None
        with ZipFile(file_path, "r") as zip_ref:
            temp_dir = WDX_DIR / "temp_import"
            temp_dir.mkdir(exist_ok=True)
            zip_ref.extractall(temp_dir)
            project_json = temp_dir / "project.json"
            if not project_json.exists():
                messagebox.showerror("Fehler", "Ungültige WDX-Datei!")
                shutil.rmtree(temp_dir)
                return False, None
            with open(project_json, "r", encoding="utf-8") as f:
                project_data = json.load(f)
            project_name = project_data["name"]
            if re.search(INVALID_CHARS, project_name):
                messagebox.showerror("Fehler", "Ungültige Zeichen im importierten Projektnamen!")
                shutil.rmtree(temp_dir)
                return False, None
            project_path = WDX_DIR / project_name
            if project_path.exists():
                messagebox.showerror("Fehler", "Projekt existiert bereits!")
                shutil.rmtree(temp_dir)
                return False, None
            shutil.move(temp_dir, project_path)
            project = {
                "name": project_name,
                "description": project_data.get("description", ""),
                "created": project_data.get("created", datetime.datetime.now().isoformat()),
                "last_modified": datetime.datetime.now().isoformat(),
                "path": project_path,
                "data_file": project_path / "project.json",
                "data": project_data
            }
            self.projects.append(project)
            self.save_projects()
            return True, project

    def rename_project(self, project, new_name):
        if re.search(INVALID_CHARS, new_name):
            return False, "Ungültige Zeichen im Projektnamen!"
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
        file_path = filedialog.asksaveasfilename(defaultextension=".wdx", filetypes=[("WDX Files", "*.wdx")], initialfile=f"{project['name']}.wdx")
        if file_path:
            with ZipFile(file_path, "w") as zip_ref:
                for file in project["path"].rglob("*"):
                    zip_ref.write(file, file.relative_to(project["path"]))
            return True, file_path
        return False, None