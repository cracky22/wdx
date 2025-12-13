from pathlib import Path

# ========= KONFIG =========
VERSION = "1.0.2 devbeta"
APP_TITLE = f"WDX {VERSION}"
ICON_BASE64 = "BASE64BILD"  # Platzhalter

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
PORT = 8765

INVALID_CHARS = r'[<>:"/\\|?*]'

DEFAULT_COLOR = "#ffffff"