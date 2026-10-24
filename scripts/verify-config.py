#!/usr/bin/env python3
"""Fail when Kconfig silently drops or changes an explicit seed selection."""
import re
import sys
from pathlib import Path


def read_config(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        match = re.fullmatch(r"(CONFIG_[^= ]+)=(.*)", line)
        disabled = re.fullmatch(r"# (CONFIG_[^ ]+) is not set", line)
        if match:
            result[match[1]] = match[2]
        elif disabled:
            result[disabled[1]] = "n"
    return result


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: verify-config.py RESOLVED_CONFIG SEED [SEED ...]")
    resolved = read_config(sys.argv[1])
    requested = {}
    for seed in sys.argv[2:]:
        requested.update(read_config(seed))
    errors = []
    for key, value in requested.items():
        actual = resolved.get(key, "n")
        if actual != value:
            errors.append(f"{key}: requested {value}, resolved {actual}")
    devices = [key for key, value in resolved.items()
               if re.fullmatch(r"CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_.+", key)
               and value == "y"]
    if devices != ["CONFIG_TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-ss-01"]:
        errors.append(f"Expected only Arthur, got {devices}")
    if errors:
        raise SystemExit("Configuration validation failed:\n" + "\n".join(errors))
    packages = sorted(key.removeprefix("CONFIG_PACKAGE_") for key, value in resolved.items()
                      if key.startswith("CONFIG_PACKAGE_") and value == "y")
    Path("selected-packages.txt").write_text("\n".join(packages) + "\n")
    print(f"Validated {len(requested)} explicit selections; {len(packages)} package symbols built in.")


if __name__ == "__main__":
    main()
