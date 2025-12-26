from pathlib import Path

VERSION = "1.2.6"
BUILDDATE = "2025-12-26"
APP_TITLE = f"wdx v{VERSION} ({BUILDDATE})"
CODENAME = "com.crackyOS.wdx"

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
INVALID_CHARS = r'[<>:"/\\|?*]'
DEFAULT_COLOR = "#ffffff"
PORT = 8765
