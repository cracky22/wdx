import os

filepath = 'wdx/main_window.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Import ScrolledFrame
import_old = "from tkinter import messagebox, simpledialog, filedialog"
import_new = "from tkinter import messagebox, simpledialog, filedialog\nfrom ttkbootstrap.widgets.scrolled import ScrolledFrame"
content = content.replace(import_old, import_new)

# Fix 2: Remove bootstyle="light" from main_frame
bootstyle_old = 'self.main_frame = ttk.Frame(self.root, padding="20", bootstyle="light")'
bootstyle_new = 'self.main_frame = ttk.Frame(self.root, padding="20")'
content = content.replace(bootstyle_old, bootstyle_new)

# Fix 3: Use ScrolledFrame for projects
frame_old = '''        self.projects_frame = ttk.Frame(self.main_frame)
        self.projects_frame.grid(row=1, column=0, sticky="nsew")'''
frame_new = '''        self.projects_frame = ScrolledFrame(self.main_frame, autohide=True)
        self.projects_frame.grid(row=1, column=0, sticky="nsew")'''
content = content.replace(frame_old, frame_new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated main_window.py")