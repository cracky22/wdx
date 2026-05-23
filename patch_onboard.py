import os

# --- PATCH project_manager.py ---
pm_path = "wdx/project_manager.py"
with open(pm_path, "r", encoding="utf-8") as f:
    pm_code = f.read()

# 1. init config
old_config = """        self.config = {
            "dark_mode": False,
            "show_prompts": True,
            "encryption_password": CODENAME,
            "citation_format": DEFAULT_CITATION_FORMAT,
        }"""
new_config = """        self.config = {
            "dark_mode": False,
            "show_prompts": True,
            "encryption_password": CODENAME,
            "citation_format": DEFAULT_CITATION_FORMAT,
            "first_run": True,
        }"""
pm_code = pm_code.replace(old_config, new_config)

# 2. registry read
old_reg_read = """                for reg_key, cfg_key, cast in [
                    ("dark_mode", "dark_mode", bool),
                    ("show_prompts", "show_prompts", bool),
                    ("encryption_password", "encryption_password", str),
                    ("citation_format", "citation_format", str),
                ]:"""
new_reg_read = """                for reg_key, cfg_key, cast in [
                    ("dark_mode", "dark_mode", bool),
                    ("show_prompts", "show_prompts", bool),
                    ("encryption_password", "encryption_password", str),
                    ("citation_format", "citation_format", str),
                    ("first_run", "first_run", bool),
                ]:"""
pm_code = pm_code.replace(old_reg_read, new_reg_read)

# 3. registry write
old_reg_write = """                winreg.SetValueEx(
                    key, "dark_mode", 0, winreg.REG_DWORD,
                    1 if self.config["dark_mode"] else 0,
                )"""
new_reg_write = """                winreg.SetValueEx(
                    key, "dark_mode", 0, winreg.REG_DWORD,
                    1 if self.config["dark_mode"] else 0,
                )
                winreg.SetValueEx(
                    key, "first_run", 0, winreg.REG_DWORD,
                    1 if self.config.get("first_run", True) else 0,
                )"""
pm_code = pm_code.replace(old_reg_write, new_reg_write)

with open(pm_path, "w", encoding="utf-8") as f:
    f.write(pm_code)
print("Updated project_manager.py")


# --- PATCH main_window.py ---
mw_path = "wdx/main_window.py"
with open(mw_path, "r", encoding="utf-8") as f:
    mw_code = f.read()

# 1. show_settings Add Reset Button
old_settings_save = """        ttk.Separator(win).pack(fill="x", pady=20, padx=20)

        # ── Speichern ────────────────────────────────────────────────────────"""
new_settings_save = """        ttk.Separator(win).pack(fill="x", pady=20, padx=20)

        # ── Setup ────────────────────────────────────────────────────────────
        ttk.Label(win, text="Setup", font=("Helvetica", 12, "bold")).pack(pady=(5, 2))
        def reset_onboarding():
            self.app.project_manager.set_setting("first_run", True)
            messagebox.showinfo("Reset", "Das Onboarding wird beim nächsten Start wieder angezeigt.")
        ttk.Button(
            win, text="Erster Start Setup wiederholen", bootstyle="warning-outline",
            command=reset_onboarding
        ).pack(pady=5)

        ttk.Separator(win).pack(fill="x", pady=20, padx=20)

        # ── Speichern ────────────────────────────────────────────────────────"""
mw_code = mw_code.replace(old_settings_save, new_settings_save)

# 2. Add show_onboarding method
new_method = """
    def show_onboarding(self):
        if not self.app.project_manager.get_setting("first_run", True):
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Willkommen bei wdx")
        dialog.geometry("450x350")
        dialog.grab_set()
        dialog.transient(self.root)
        try:
            dialog.iconbitmap("icon128.ico")
        except:
            pass
        
        ttk.Label(dialog, text="Willkommen bei wdx!", font=("Helvetica", 16, "bold")).pack(pady=(20, 10))
        
        desc = "wdx (Web Data Extractor) hilft dir, strukturierte Informationen und Ressourcen aus dem Web direkt in Projekten zu speichern und zu verwalten.\\n\\nNutze die Chrome-Erweiterung, um Webseiten mit einem Klick zu speichern."
        ttk.Label(dialog, text=desc, wraplength=400, justify="center").pack(pady=10)
        
        ttk.Separator(dialog).pack(fill="x", pady=10, padx=20)
        
        ttk.Label(dialog, text="Wähle dein Theme:", font=("Helvetica", 10, "bold")).pack(pady=5)
        
        var_dark = tk.BooleanVar(value=self.app.dark_mode)
        ttk.Checkbutton(
            dialog, text="Dark Mode verwenden", variable=var_dark,
            bootstyle="round-toggle",
            command=lambda: self.app.toggle_theme(),
        ).pack(pady=5)
        
        def finish():
            self.app.project_manager.set_setting("first_run", False)
            dialog.destroy()
            
        ttk.Button(dialog, text="Loslegen!", command=finish, bootstyle="success").pack(pady=20)
        self.root.wait_window(dialog)
"""

if "def show_onboarding" not in mw_code:
    # Append the method to MainWindow class.
    # Find a good place, e.g., before def _should_show_prompts
    mw_code = mw_code.replace("    def _should_show_prompts(self) -> bool:", new_method + "\n    def _should_show_prompts(self) -> bool:")

# 3. Call show_onboarding in __init__
old_init_end = """        self.update_project_tiles()"""
new_init_end = """        self.update_project_tiles()
        self.root.after(500, self.show_onboarding)"""
mw_code = mw_code.replace(old_init_end, new_init_end)

with open(mw_path, "w", encoding="utf-8") as f:
    f.write(mw_code)
print("Updated main_window.py")