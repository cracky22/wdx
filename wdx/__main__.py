import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox
import datetime
import uuid
import threading
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from constants import APP_TITLE
from server import start_server
from project_manager import ProjectManager
from main_window import MainWindow
from project_window import ProjectWindow
from utils import get_smart_color_for_source

class WdxApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.project_manager = ProjectManager()
        self.style = ttk.Style()
        
        self.dark_mode = self.project_manager.get_setting("dark_mode", False)
        self.apply_theme()
        
        self.main_window = MainWindow(root, self)
        start_server(self)
        self.last_connection = None
        self.connection_count = 0
        self.current_project_name = None
        
        self.update_connection_status()

    def open_project(self, project):
        self.main_window.hide()
        self.project_window = ProjectWindow(self.root, project, self)
        self.current_project_name = project["name"]

    def close_project(self):
        if hasattr(self, "project_window"):
            if hasattr(self.project_window, "executor"):
                self.project_window.executor.shutdown(wait=False)
            if hasattr(self.project_window, "main_frame") and self.project_window.main_frame.winfo_exists():
                self.project_window.main_frame.destroy()
            del self.project_window
            
            if hasattr(self, "current_project_name"):
                self.root.after(0, self.main_window.set_browser_connected, True)
            
        self.current_project_name = None
        self.main_window.refresh_and_update()
        self.main_window.show()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        
        self.project_manager.set_setting("dark_mode", self.dark_mode)

    def apply_theme(self):
        if self.dark_mode:
            self.style.theme_use("darkly")
        else:
            self.style.theme_use("litera")

    def update_connection_status(self):
        if self.last_connection:
            delta = datetime.datetime.now() - self.last_connection
            if delta.total_seconds() < 5:
                pass
        self.root.after(2000, self.update_connection_status)

    def set_current_project(self, project_name):
        self.current_project_name = project_name

    def handle_communication(self, data):
        self.last_connection = datetime.datetime.now()
        self.connection_count += 1
        
        try:
            self.root.deiconify()
            self.root.lift()
        except Exception:
            pass

        project = None
        if self.current_project_name:
            try:
                project = next(
                    p
                    for p in self.project_manager.projects
                    if p["name"] == self.current_project_name
                )
            except StopIteration:
                self.current_project_name = None
                return
        else:
            project_names = [p["name"] for p in self.project_manager.projects]
            if not project_names:
                
                messagebox.showerror(
                    "Fehler",
                    "Keine Projekte vorhanden. Bitte erst ein Projekt erstellen.",
                )
                return

            project_name = self._ask_project_selection(project_names)
            
            if not project_name or project_name not in project_names:
                return
            
            project = next(
                p for p in self.project_manager.projects if p["name"] == project_name
            )

        if self.current_project_name == project["name"] and hasattr(self, 'project_window'):
            self.project_window.handle_external_data(data)
        else:
            threading.Thread(
                target=self._download_worker, args=(data, project), daemon=True
            ).start()
            
    def _ask_project_selection(self, project_names):
        selection = {"name": None}
        dialog = tk.Toplevel(self.root)
        dialog.title("Projekt wählen")
        dialog.geometry("300x400")
        dialog.grab_set()
        ttk.Label(dialog, text="In welches Projekt speichern?", padding=10).pack()
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)

        def select(name):
            selection["name"] = name
            dialog.destroy()

        for name in project_names:
            btn = ttk.Button(
                frame, 
                text=name, 
                bootstyle="outline-primary",
                command=lambda n=name: select(n)
            )
            btn.pack(fill="x", pady=2)

        ttk.Separator(dialog).pack(fill="x", pady=5)
        ttk.Button(dialog, text="Abbrechen", bootstyle="danger", command=dialog.destroy).pack(pady=10)
        self.root.wait_window(dialog)
        return selection["name"]

    def _download_worker(self, data, project):
        source_id = str(uuid.uuid4())
        
        new_source = {
            "id": source_id,
            "type": "source",
            "url": data["url"],
            "title": data.get("title", data["url"]),
            "text": data.get("text", ""),
            "keywords": data.get("keywords", ""),
            "color": "#ffffff",
            "added": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 300,
            "pos_y": 300,
            "favicon": "",
            "saved_pages": [],
        }
        
        project_dir = project["path"]
        images_dir = project_dir / "images"
        sites_dir = project_dir / "sites"
        images_dir.mkdir(exist_ok=True)
        sites_dir.mkdir(exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        html_content = ""

        try:
            response = requests.get(data["url"], headers=headers, timeout=15)
            html_content = response.text
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"page_{source_id}_{timestamp}.html"
            with open(sites_dir / html_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            new_source["saved_pages"].append({
                "file": html_filename,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            print(f"HTML Download Fehler: {e}")

        fav_path = None
        try:
            icon_url = None
            try:
                parsed_uri = urlparse(data["url"])
                base_url = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)
            except:
                base_url = ""

            if html_content and base_url:
                try:
                    soup = BeautifulSoup(html_content, "html.parser")
                    icon_link = soup.find("link", rel=lambda x: x and x.lower() in ["icon", "shortcut icon", "apple-touch-icon"])
                    if icon_link and icon_link.get("href"):
                        icon_url = urljoin(base_url, icon_link.get("href"))
                except Exception:
                    pass

            if not icon_url and base_url:
                icon_url = urljoin(base_url, "/favicon.ico")

            fav_content = None
            if icon_url:
                try:
                    fav_resp = requests.get(icon_url, headers=headers, timeout=5)
                    if fav_resp.status_code == 200 and len(fav_resp.content) > 0:
                        fav_content = fav_resp.content
                except:
                    pass

            if not fav_content and base_url:
                try:
                    google_url = f"https://www.google.com/s2/favicons?domain={base_url}&sz=64"
                    g_resp = requests.get(google_url, headers=headers, timeout=5)
                    if g_resp.status_code == 200:
                        fav_content = g_resp.content
                except:
                    pass

            if fav_content:
                fav_name = f"favicon_{source_id}.ico"
                if b"PNG" in fav_content[:8]:
                    fav_name = f"favicon_{source_id}.png"
                elif b"JFIF" in fav_content[:10] or b"Exif" in fav_content[:10]:
                    fav_name = f"favicon_{source_id}.jpg"
                
                fav_full_path = images_dir / fav_name
                with open(fav_full_path, "wb") as f:
                    f.write(fav_content)
                
                new_source["favicon"] = fav_name
                fav_path = fav_full_path

        except Exception as e:
            print(f"Favicon Worker Fehler: {e}")

        if fav_path:
            try:
                existing_colors = set()
                if "items" in project["data"]:
                    for item in project["data"]["items"]:
                        if "color" in item:
                            existing_colors.add(item["color"])
                
                smart_color = get_smart_color_for_source(str(fav_path), existing_colors)
                new_source["color"] = smart_color
                
            except Exception as e:
                print(f"Farbanalyse Fehler: {e}")

        self.root.after(0, lambda: self._finalize_source_add_safe(project, new_source))

    def _finalize_source_add_safe(self, project, source):
        def update_logic(data):
            if "items" not in data:
                data["items"] = []
            data["items"].append(source)
            
        self.project_manager.update_project_file_safe(project, update_logic)
        
        if self.current_project_name is None:
            self.main_window.refresh_and_update()
        
        if self.project_manager.get_setting("show_prompts", True):
            messagebox.showinfo("Gespeichert", f"Inhalt wurde in '{project['name']}' gespeichert.")


if __name__ == "__main__":
    root = ttk.Window()
    app = WdxApp(root)
    try:
        root.mainloop()
    finally:
        if hasattr(app, "httpd"):
            app.httpd.shutdown()