from pathlib import Path

VERSION = "v1.2.5 (2025-12-24)"
APP_TITLE = f"wdx {VERSION}"
CODENAME = "com.crackyOS.wdx"

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
INVALID_CHARS = r'[<>:"/\\|?*]'
DEFAULT_COLOR = "#ffffff"
PORT = 8765
