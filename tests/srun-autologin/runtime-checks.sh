#!/bin/sh

set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
TEST_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/srun-runtime.XXXXXX")"
trap 'rm -rf "$TEST_ROOT"' EXIT INT TERM
BIN_DIR="$TEST_ROOT/bin"
mkdir -p "$BIN_DIR" "$TEST_ROOT/run"
cp "$ROOT_DIR/package/luci-app-srun-autologin/files/usr/bin/srun-autologin" "$BIN_DIR/"
chmod 0755 "$BIN_DIR/srun-autologin"

cat > "$BIN_DIR/logger" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$TEST_LOG"
EOF

cat > "$BIN_DIR/uci" <<'EOF'
#!/bin/sh
key="$3"
case "$key" in
	srun-autologin.main) printf 'srun\n' ;;
	srun-autologin.main.enabled) printf '1\n' ;;
	srun-autologin.main.username) printf 'test-user\n' ;;
	srun-autologin.main.password) printf 'secret-value\n' ;;
	srun-autologin.main.check_host) printf 'test.example\n' ;;
	srun-autologin.main.check_count) printf '3\n' ;;
	srun-autologin.main.check_timeout) printf '1\n' ;;
	*) exit 1 ;;
esac
EOF

cat > "$BIN_DIR/ping" <<'EOF'
#!/bin/sh
count=0
[ ! -r "$PING_COUNT" ] || count="$(cat "$PING_COUNT")"
count=$((count + 1))
printf '%s\n' "$count" > "$PING_COUNT"
[ "$PING_MODE" = online ] && exit 0
[ -r "$AUTHENTICATED" ] && exit 0
exit 1
EOF

cat > "$BIN_DIR/srun" <<'EOF'
#!/bin/sh
[ "$1" = login ] && [ "$2" = -c ] || exit 9
cp "$3" "$CAPTURED_CONFIG"
touch "$AUTHENTICATED"
cat <<OUT
User {
    username: "test-user",
    password: "secret-value",
}
OUT
exit 0
EOF

cat > "$TEST_ROOT/jshn.sh" <<'EOF'
json_init() { :; }
json_add_boolean() { :; }
json_add_int() { :; }
json_add_array() { :; }
json_add_object() { :; }
json_close_object() { :; }
json_close_array() { :; }
json_add_string() {
	case "$1" in
		server) j_server="$2" ;;
		username) j_username="$2" ;;
		password) j_password="$2" ;;
	esac
}
json_dump() {
	printf '{"server":"%s","users":[{"username":"%s","password":"%s"}]}\n' \
		"$j_server" "$j_username" "$j_password"
}
EOF

chmod 0755 "$BIN_DIR/logger" "$BIN_DIR/uci" "$BIN_DIR/ping" "$BIN_DIR/srun"

export PATH="$BIN_DIR:/usr/bin:/bin"
export TEST_LOG="$TEST_ROOT/log"
export PING_COUNT="$TEST_ROOT/ping-count"
export AUTHENTICATED="$TEST_ROOT/authenticated"
export CAPTURED_CONFIG="$TEST_ROOT/config.json"
export SRUN_AUTOLOGIN_RUNTIME_CONFIG="$TEST_ROOT/run/config.json"
export SRUN_AUTOLOGIN_STATUS_FILE="$TEST_ROOT/run/status"
export SRUN_AUTOLOGIN_LOCK_DIR="$TEST_ROOT/run/lock"
export SRUN_AUTOLOGIN_JSHN_LIB="$TEST_ROOT/jshn.sh"

# Already-online path must not invoke srun.
export PING_MODE=online
rm -f "$AUTHENTICATED" "$CAPTURED_CONFIG" "$PING_COUNT" "$TEST_LOG"
"$BIN_DIR/srun-autologin" run
grep -q '^state=online$' "$SRUN_AUTOLOGIN_STATUS_FILE"
[ ! -e "$CAPTURED_CONFIG" ]
[ "$(cat "$PING_COUNT")" = 1 ]

# Offline path performs exactly three probes, authenticates, then verifies once.
export PING_MODE=offline
rm -f "$AUTHENTICATED" "$CAPTURED_CONFIG" "$PING_COUNT" "$TEST_LOG"
"$BIN_DIR/srun-autologin" run
grep -q '^state=online$' "$SRUN_AUTOLOGIN_STATUS_FILE"
grep -q '"password":"secret-value"' "$CAPTURED_CONFIG"
[ "$(cat "$PING_COUNT")" = 4 ]
! grep -q 'secret-value' "$TEST_LOG"

printf 'runtime checks passed\n'
