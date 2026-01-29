from pathlib import Path

VERSION = "1.3.3"
BUILDDATE = "2026-01-29"
APP_TITLE = f"wdx v{VERSION} ({BUILDDATE})"
CODENAME = "com.crackyOS.wdx"

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
INVALID_CHARS = r'[<>:"/\\|?*]'
DEFAULT_COLOR = "#ffffff"
PORT = 8765
