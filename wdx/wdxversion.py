import argparse
import json
import re
from datetime import datetime
from pathlib import Path

def update_files(new_version):
    today = datetime.now().strftime("%Y-%m-%d")
    version_val = new_version.lstrip('v')

    files = {
        "python_constants": Path("./wdx/constants.py"),
        "js_constants": Path("./wdx_extension/src/js/constants.js"),
        "manifest": Path("./wdx_extension/manifest.json"),
        "package": Path("./wdx_extension/package.json")
    }

    if files["python_constants"].exists():
        content = files["python_constants"].read_text(encoding="utf-8")
        content = re.sub(r'VERSION = ".*?"', f'VERSION = "{version_val}"', content)
        content = re.sub(r'BUILDDATE = ".*?"', f'BUILDDATE = "{today}"', content)
        files["python_constants"].write_text(content, encoding="utf-8")
        print(f"Updated {files['python_constants']}")

    if files["js_constants"].exists():
        content = files["js_constants"].read_text(encoding="utf-8")
        content = re.sub(r'export const VERSION = ".*?"', f'export const VERSION = "{version_val}"', content)
        content = re.sub(r'export const BUILDDATE = ".*?"', f'export const BUILDDATE = "{today}"', content)
        files["js_constants"].write_text(content, encoding="utf-8")
        print(f"Updated {files['js_constants']}")

    for key in ["manifest", "package"]:
        if files[key].exists():
            data = json.loads(files[key].read_text(encoding="utf-8"))
            data["version"] = version_val
            files[key].write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Updated {files[key]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update version and build date.")
    parser.add_argument("-v", "--version", required=True, help="New version (e.g., v1.2.9)")
    args = parser.parse_args()

    update_files(args.version)