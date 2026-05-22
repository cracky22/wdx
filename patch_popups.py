import os

# 1. Update main_window.py
main_path = "wdx/main_window.py"
with open(main_path, "r", encoding="utf-8") as f:
    main_code = f.read()

old_delete = """    def delete_project(self, project):
        confirm = True
        if self._should_show_prompts():
            confirm = messagebox.askyesno(
                "Löschen", f"'{project['name']}' wirklich löschen?"
            )
        if confirm:
            self.project_manager.delete_project(project)
            self.update_project_tiles()"""

new_delete = """    def delete_project(self, project):
        if messagebox.askyesno("Löschen", f"'{project['name']}' wirklich löschen?"):
            self.project_manager.delete_project(project)
            self.update_project_tiles()"""

if old_delete in main_code:
    main_code = main_code.replace(old_delete, new_delete)
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(main_code)
    print("Updated main_window.py")
else:
    print("Could not find old_delete in main_window.py")

# 2. Update project_window.py
proj_path = "wdx/project_window.py"
with open(proj_path, "r", encoding="utf-8") as f:
    proj_code = f.read()

old_copy = '        messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")'
new_copy = '        if self.app.project_manager.get_setting("show_prompts", True):\n            messagebox.showinfo("Erfolg", "Quellenangabe kopiert.")'

old_export = '            messagebox.showinfo("Exportiert", f"Projekt als \'{file_path}\' exportiert.")'
new_export = '            if self.app.project_manager.get_setting("show_prompts", True):\n                messagebox.showinfo("Exportiert", f"Projekt als \'{file_path}\' exportiert.")'

changed = False
if old_copy in proj_code:
    proj_code = proj_code.replace(old_copy, new_copy)
    changed = True
if old_export in proj_code:
    proj_code = proj_code.replace(old_export, new_export)
    changed = True

if changed:
    with open(proj_path, "w", encoding="utf-8") as f:
        f.write(proj_code)
    print("Updated project_window.py")
else:
    print("Could not find strings in project_window.py")