from pathlib import Path

# ========= KONFIG =========
VERSION = "1.0.4 devbeta"
APP_TITLE = f"WDX {VERSION}"

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
PORT = 8765

INVALID_CHARS = r'[<>:"/\\|?*]'

DEFAULT_COLOR = "#ffffff"