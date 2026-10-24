#!/bin/sh

set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
MAIN_SCRIPT="$ROOT_DIR/package/luci-app-srun-autologin/files/usr/bin/srun-autologin"
VIEW="$ROOT_DIR/package/luci-app-srun-autologin/files/www/luci-static/resources/view/srun-autologin/config.js"

sh -n "$MAIN_SCRIPT"
sh -n "$ROOT_DIR/package/luci-app-srun-autologin/files/etc/init.d/srun-autologin"
sh -n "$ROOT_DIR/tests/srun-autologin/runtime-checks.sh"
if command -v node >/dev/null 2>&1; then
	node --check "$VIEW"
else
	printf 'node is unavailable here; run node --check on config.js on the host\n'
fi

python3 -m json.tool "$ROOT_DIR/package/luci-app-srun-autologin/files/usr/share/luci/menu.d/luci-app-srun-autologin.json" >/dev/null
python3 -m json.tool "$ROOT_DIR/package/luci-app-srun-autologin/files/usr/share/rpcd/acl.d/luci-app-srun-autologin.json" >/dev/null

want='25c2e3645f6fb508d186812790165f7ed3f9d17fc2fef5257c9417957ed4c526'
archive="$ROOT_DIR/work/vendor/srun-aarch64.tar.xz"
[ ! -f "$archive" ] || [ "$(sha256sum "$archive" | awk '{print $1}')" = "$want" ]
grep -q "$want" "$MAIN_SCRIPT"

printf 'static checks passed\n'
