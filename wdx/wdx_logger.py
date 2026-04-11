import logging
import sys
from pathlib import Path
from constants import WDX_DIR, VERSION

LOG_FILE = WDX_DIR / "wdx.log"
LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    WDX_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("wdx")
    if root.handlers:
        return  # already configured

    root.setLevel(logging.DEBUG)

    # --- file handler (DEBUG+) -------------------------------------------------
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # --- console handler (WARNING+) -------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.info("wdx v%s logging initialised - log: %s", VERSION, LOG_FILE)


def get_logger(module_name: str) -> logging.Logger:
    short = module_name.split(".")[-1] if "." in module_name else module_name
    return logging.getLogger(f"wdx.{short}")