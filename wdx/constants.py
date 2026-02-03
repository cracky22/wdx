from pathlib import Path
import os

VERSION = "1.3.7"
BUILDDATE = "2026-02-03"
APP_TITLE = f"wdx v{VERSION} ({BUILDDATE})"
CODENAME = "com.crackyOS.wdx"

WDX_DIR = Path.home() / "Documents" / "wdx"
PROJECTS_FILE = WDX_DIR / "projects.json"
CONFIG_FILE = WDX_DIR / "config.json"
REG_PATH = r"Software\crackyOS\wdx"

INVALID_CHARS = r'[<>:"/\\|?*]'
DEFAULT_COLOR = "#ffffff"
PORT = 8765
