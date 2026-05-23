import os

mw_path = "wdx/main_window.py"
with open(mw_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_init = False
for line in lines:
    if line.strip() == "def __init__(self, root, app):":
        in_init = True
    elif in_init and line.startswith("    def "):
        in_init = False

    if "self.root.after(500, self.show_onboarding)" in line:
        if not in_init:
            continue # Remove from outside __init__
    
    new_lines.append(line)

with open(mw_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Fixed main_window.py duplications")