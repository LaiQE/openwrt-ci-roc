#!/usr/bin/env python3
"""Apply reviewed patch releases to maintained feed recipes, retaining their patches."""
import json
import re
import sys
from pathlib import Path

updates = json.loads(Path(sys.argv[1]).read_text())
for name, update in updates.items():
    recipe = Path("feeds/packages") / name / "Makefile"
    text = recipe.read_text()
    current = re.search(r"^PKG_VERSION:=(.+)$", text, re.M).group(1)
    if current not in (update["from"], update["version"]):
        raise SystemExit(f"{name}: feed moved to {current}; review the version override before building")
    text = re.sub(r"^PKG_VERSION:=.+$", f"PKG_VERSION:={update['version']}", text, flags=re.M)
    text = re.sub(r"^PKG_HASH:=.+$", f"PKG_HASH:={update['sha256']}", text, flags=re.M)
    recipe.write_text(text)
    print(f"{name}: {update['version']} ({update['sha256']})")
