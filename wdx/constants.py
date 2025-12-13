from pathlib import Path

# ========= KONFIG =========
VERSION = "v1.0.5"
APP_TITLE = f"wdx {VERSION}"

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
PORT = 8765

INVALID_CHARS = r'[<>:"/\\|?*]'

DEFAULT_COLOR = "#ffffff"