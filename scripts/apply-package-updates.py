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
    if update.get("kind") == "go":
        series = re.search(r"^GO_VERSION_MAJOR_MINOR:=(.+)$", text, re.M).group(1)
        patch = re.search(r"^GO_VERSION_PATCH:=(.+)$", text, re.M).group(1)
        current = f"{series}.{patch}"
        if not update["version"].startswith(series + "."):
            raise SystemExit(f"{name}: version override must stay within Go {series}")
    else:
        current = re.search(r"^PKG_VERSION:=(.+)$", text, re.M).group(1)
    if current not in (update["from"], update["version"]):
        raise SystemExit(f"{name}: feed moved to {current}; review the version override before building")
    if update.get("kind") == "go":
        text = re.sub(r"^GO_VERSION_PATCH:=.+$", f"GO_VERSION_PATCH:={update['version'].split('.')[-1]}", text, flags=re.M)
        values = recipe.parent.parent / "golang-values.mk"
        values.write_text(re.sub(r"^GO_DEFAULT_VERSION:=.+$", f"GO_DEFAULT_VERSION:={series}", values.read_text(), flags=re.M))
        # The package scanner does not track this included file. Refresh the
        # dummy package so golang/host also depends on the new default version.
        (values.parent / "golang/Makefile").touch()
    else:
        text = re.sub(r"^PKG_VERSION:=.+$", f"PKG_VERSION:={update['version']}", text, flags=re.M)
    text = re.sub(r"^PKG_HASH:=.+$", f"PKG_HASH:={update['sha256']}", text, flags=re.M)
    if "git_short_commit" in update:
        text, count = re.subn(r"^PKG_GIT_SHORT_COMMIT:=.+$",
                              f"PKG_GIT_SHORT_COMMIT:={update['git_short_commit']}",
                              text, flags=re.M)
        assert count == 1, f"{name}: missing source commit metadata"
    recipe.write_text(text)
    print(f"{name}: {update['version']} ({update['sha256']})")
