import json
import shutil
import os
import sys
import gc
from pathlib import Path
from tkinter import messagebox, filedialog
import pyzipper
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from constants import WDX_DIR, PROJECTS_FILE, CODENAME, CONFIG_FILE
from wdx_logger import get_logger

if sys.platform == "win32":
    import winreg

logger = get_logger(__name__)

DEFAULT_CITATION_FORMAT = "{url}, zuletzt aufgerufen am {added}"


class ProjectManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.projects = []

        self.config = {
            "dark_mode": False,
            "show_prompts": True,
            "encryption_password": CODENAME,
            "citation_format": DEFAULT_CITATION_FORMAT,
        }

        self.load_settings()
        self.load_projects()

    
    def _get_dir_size(self, path) -> int:
        total_size = 0
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return 0
            with os.scandir(path_obj) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat().st_size
                        elif entry.is_dir(follow_symlinks=False):
                            total_size += self._get_dir_size(entry.path)
                    except (PermissionError, OSError) as exc:
                        logger.debug(
                            "Dateigröße nicht lesbar (%s): %s", entry.path, exc
                        )
        except Exception as exc:
            logger.warning("Fehler bei Größenberechnung für %s: %s", path, exc)
        return total_size

    
    def load_settings(self):
        if sys.platform == "win32":
            self._load_settings_win_registry()
        else:
            self._load_settings_json()

    def save_settings(self):
        if sys.platform == "win32":
            self._save_settings_win_registry()
        else:
            self._save_settings_json()

    def get_setting(self, key, default=None):
        return self.config.get(key, default)

    def set_setting(self, key, value):
        self.config[key] = value
        self.save_settings()
        logger.debug("Einstellung gesetzt — %s=%s", key, value)

    def _load_settings_win_registry(self):
        REG_PATH = r"Software\crackyOS\wdx"
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ
            ) as key:
                for reg_key, cfg_key, cast in [
                    ("dark_mode", "dark_mode", bool),
                    ("show_prompts", "show_prompts", bool),
                    ("encryption_password", "encryption_password", str),
                    ("citation_format", "citation_format", str),
                ]:
                    try:
                        val, _ = winreg.QueryValueEx(key, reg_key)
                        self.config[cfg_key] = cast(val) if val else self.config[cfg_key]
                    except FileNotFoundError:
                        pass
            logger.debug("Einstellungen aus Registry geladen")
        except (FileNotFoundError, OSError) as exc:
            logger.debug("Registry-Schlüssel nicht gefunden (Erststart?): %s", exc)

    def _save_settings_win_registry(self):
        REG_PATH = r"Software\crackyOS\wdx"
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                winreg.SetValueEx(
                    key, "dark_mode", 0, winreg.REG_DWORD,
                    1 if self.config["dark_mode"] else 0,
                )
                winreg.SetValueEx(
                    key, "show_prompts", 0, winreg.REG_DWORD,
                    1 if self.config["show_prompts"] else 0,
                )
                winreg.SetValueEx(
                    key, "encryption_password", 0, winreg.REG_SZ,
                    self.config["encryption_password"],
                )
                winreg.SetValueEx(
                    key, "citation_format", 0, winreg.REG_SZ,
                    self.config.get("citation_format", DEFAULT_CITATION_FORMAT),
                )
            logger.debug("Einstellungen in Registry gespeichert")
        except OSError as exc:
            logger.error("Registry schreiben fehlgeschlagen: %s", exc)

    def _load_settings_json(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.config.update(data)
                logger.debug("Einstellungen aus %s geladen", CONFIG_FILE)
            except json.JSONDecodeError as exc:
                logger.error("Config-JSON beschädigt (%s): %s", CONFIG_FILE, exc)
            except OSError as exc:
                logger.error("Config-Datei nicht lesbar: %s", exc)

    def _save_settings_json(self):
        try:
            WDX_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            logger.debug("Einstellungen in %s gespeichert", CONFIG_FILE)
        except OSError as exc:
            logger.error("Einstellungen konnten nicht gespeichert werden: %s", exc)

    
    
    def load_projects(self):
        self.projects = []
        if not PROJECTS_FILE.exists():
            logger.info("Keine projects.json gefunden — leere Projektliste")
            return

        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                projects_data = json.load(f)

            for proj in projects_data:
                try:
                    p_path = Path(proj["path"])
                    d_file = Path(proj["data_file"])

                    if not d_file.exists():
                        logger.warning(
                            "Projektdatei fehlt, überspringe '%s': %s",
                            proj.get("name", "?"),
                            d_file,
                        )
                        continue

                    with open(d_file, "r", encoding="utf-8") as f:
                        actual_data = json.load(f)

                    self.projects.append(
                        {
                            "name": actual_data.get("name", proj["name"]),
                            "description": actual_data.get(
                                "description", proj["description"]
                            ),
                            "created": actual_data.get("created", proj["created"]),
                            "last_modified": actual_data.get(
                                "last_modified", proj["last_modified"]
                            ),
                            "path": p_path,
                            "data_file": d_file,
                            "data": actual_data,
                            "size": self._get_dir_size(p_path),
                        }
                    )
                except (KeyError, json.JSONDecodeError, OSError) as exc:
                    logger.error(
                        "Projekt '%s' konnte nicht geladen werden: %s",
                        proj.get("name", "?"),
                        exc,
                    )

            logger.info("%d Projekt(e) geladen", len(self.projects))
        except json.JSONDecodeError as exc:
            logger.critical("projects.json beschädigt: %s", exc)
        except OSError as exc:
            logger.critical("projects.json nicht lesbar: %s", exc)

    def save_projects(self):
        with self.lock:
            projects_data = [
                {
                    "name": p["name"],
                    "description": p["description"],
                    "created": p["created"],
                    "last_modified": p["last_modified"],
                    "path": str(p["path"]),
                    "data_file": str(p["data_file"]),
                }
                for p in self.projects
            ]
            try:
                WDX_DIR.mkdir(parents=True, exist_ok=True)
                with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(projects_data, f, indent=4)
                logger.debug("projects.json gespeichert (%d Einträge)", len(projects_data))
            except OSError as exc:
                logger.error("projects.json konnte nicht gespeichert werden: %s", exc)

    def update_project_file_safe(self, project, update_fn):
        with self.lock:
            try:
                update_fn(project["data"])
                project["last_modified"] = datetime.datetime.now().isoformat()
                with open(project["data_file"], "w", encoding="utf-8") as f:
                    json.dump(project["data"], f, indent=4)
                project["size"] = self._get_dir_size(project["path"])
                logger.debug("Projekt-Datei aktualisiert: %s", project["name"])
            except OSError as exc:
                logger.error(
                    "Projekt '%s' konnte nicht geschrieben werden: %s",
                    project["name"],
                    exc,
                )
            except Exception as exc:
                logger.exception(
                    "Unerwarteter Fehler in update_project_file_safe (%s): %s",
                    project["name"],
                    exc,
                )
        self.save_projects()

    def save_specific_project_data(self, project):
        try:
            project["last_modified"] = datetime.datetime.now().isoformat()
            with open(project["data_file"], "w", encoding="utf-8") as f:
                json.dump(project["data"], f, indent=4)
            project["size"] = self._get_dir_size(project["path"])
            logger.debug("Projektdaten gespeichert: %s", project["name"])
        except OSError as exc:
            logger.error(
                "Projektdaten für '%s' konnten nicht gespeichert werden: %s",
                project["name"],
                exc,
            )
        except Exception as exc:
            logger.exception("Unerwarteter Fehler beim Speichern von '%s': %s", project["name"], exc)
        self.save_projects()

    def create_project(self, name, description):
        project_dir = WDX_DIR / name
        if project_dir.exists():
            logger.warning("Projekt '%s' existiert bereits", name)
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
                "name": name,
                "description": description,
                "created": now,
                "last_modified": now,
                "path": project_dir,
                "data_file": data_file,
                "data": initial_data,
                "size": 0,
            }
            self.projects.append(new_project)
            self.save_projects()
            logger.info("Neues Projekt erstellt: %s", name)
            return True, new_project
        except OSError as exc:
            logger.error("Projekt '%s' konnte nicht erstellt werden: %s", name, exc)
            return False, str(exc)

    def rename_project(self, project, new_name, new_description=None):
        """Benennt ein Projekt um und aktualisiert optional die Beschreibung."""
        new_path = WDX_DIR / new_name
        if new_path.exists() and new_path != project["path"]:
            logger.warning("Umbenennen abgelehnt — '%s' existiert bereits", new_name)
            return False, "Existiert bereits!"
        gc.collect()
        try:
            old_name = project["name"]
            # Verzeichnis nur umbenennen wenn der Name sich geändert hat
            if new_name != project["name"]:
                os.rename(str(project["path"]), str(new_path))
                project["path"] = new_path
                project["data_file"] = new_path / "project.json"

            project["name"] = new_name
            project["data"]["name"] = new_name

            if new_description is not None:
                project["description"] = new_description
                project["data"]["description"] = new_description

            with open(project["data_file"], "w", encoding="utf-8") as f:
                json.dump(project["data"], f, indent=4)

            self.save_projects()
            logger.info(
                "Projekt aktualisiert: '%s' → '%s' (Beschreibung: %s)",
                old_name, new_name,
                new_description if new_description is not None else "unverändert",
            )
            return True, None
        except PermissionError:
            logger.warning("Umbenennen fehlgeschlagen — Datei wird verwendet: %s", project["name"])
            return False, "Datei wird noch verwendet"
        except OSError as exc:
            logger.error("Umbenennen fehlgeschlagen: %s", exc)
            return False, str(exc)

    def export_project(self, project):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".wdx",
            filetypes=[("wdx Projektdatei", "*.wdx")],
            initialfile=f"{project['name']}.wdx",
        )
        if not file_path:
            return False, None

        pwd = self.config.get("encryption_password", CODENAME)
        logger.info("Exportiere Projekt '%s' nach %s", project["name"], file_path)

        try:
            files_to_add = []
            for root, _, files in os.walk(project["path"]):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(project["path"])
                    files_to_add.append((full_path, rel_path))

            with pyzipper.AESZipFile(
                file_path,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                if pwd:
                    zf.setpassword(pwd.encode("utf-8"))
                with ThreadPoolExecutor() as executor:
                    for full_p, rel_p in files_to_add:
                        zf.write(full_p, rel_p)

            logger.info("Export erfolgreich: %s (%d Dateien)", file_path, len(files_to_add))
            return True, file_path
        except OSError as exc:
            logger.error("Export fehlgeschlagen (IO): %s", exc)
            return False, None
        except Exception as exc:
            logger.exception("Export fehlgeschlagen (unbekannt): %s", exc)
            return False, None

    def import_project(self, file_path):
        logger.info("Importiere Projekt von %s", file_path)
        try:
            pwd = self.config.get("encryption_password", CODENAME)

            with pyzipper.AESZipFile(file_path, "r") as zip_ref:
                if pwd:
                    zip_ref.setpassword(pwd.encode("utf-8"))

                if "project.json" not in zip_ref.namelist():
                    logger.error("Import: project.json fehlt in der Archivdatei")
                    return False

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
                    "name": name,
                    "description": data.get("description", ""),
                    "created": data.get(
                        "created", datetime.datetime.now().isoformat()
                    ),
                    "last_modified": datetime.datetime.now().isoformat(),
                    "path": target_dir,
                    "data_file": data_file,
                    "data": data,
                    "size": self._get_dir_size(target_dir),
                }
                self.projects.append(new_proj)
                self.save_projects()
                logger.info("Import erfolgreich: '%s'", name)
                return True

        except RuntimeError as exc:
            logger.warning("Import fehlgeschlagen — falsches Passwort oder beschädigte Datei: %s", exc)
            messagebox.showerror(
                "Import Fehler", "Falsches Passwort oder beschädigte Datei."
            )
            return False
        except json.JSONDecodeError as exc:
            logger.error("Import: project.json beschädigt: %s", exc)
            messagebox.showerror("Import Fehler", "Projektdatei ist beschädigt.")
            return False
        except OSError as exc:
            logger.error("Import IO-Fehler: %s", exc)
            messagebox.showerror("Import Fehler", str(exc))
            return False

    def delete_project(self, project):
        gc.collect()
        try:
            shutil.rmtree(project["path"])
            self.projects.remove(project)
            self.save_projects()
            logger.info("Projekt gelöscht: %s", project["name"])
            return True
        except OSError as exc:
            logger.error("Projekt '%s' konnte nicht gelöscht werden: %s", project["name"], exc)
            messagebox.showerror("Fehler", str(exc))
            return False