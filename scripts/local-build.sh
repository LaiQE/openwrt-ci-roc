#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
BUILD_ROOT="${BUILD_ROOT:-/work}"
STAGE="${1:-build}"
JOBS="${JOBS:-4}"
case "$JOBS" in ''|*[!0-9]*|0) echo 'JOBS must be a positive integer' >&2; exit 1;; esac
mkdir -p "$BUILD_ROOT/logs" "$BUILD_ROOT/artifacts"
exec 9>"$BUILD_ROOT/build.lock"
flock -n 9 || { echo 'Another build stage is running' >&2; exit 1; }
exec > >(tee -a "$BUILD_ROOT/logs/$STAGE.log") 2>&1
finish() {
    local code=$?
    printf '%s\n' "$code" > "$BUILD_ROOT/last-exit-code"
    printf '%s finished (exit %s) at %s\n' "$STAGE" "$code" "$(date -Is)" > "$BUILD_ROOT/status"
    exit "$code"
}
trap finish EXIT
printf '%s running (pid %s) since %s\n' "$STAGE" "$$" "$(date -Is)" > "$BUILD_ROOT/status"
date -Is
# shellcheck source=../configs/source.env
source "$WORKSPACE/configs/source.env"
OPENWRT_PATH="$BUILD_ROOT/openwrt"
seeds=("$WORKSPACE/configs/Arthur.config" "$WORKSPACE/configs/General.config")

prepare() {
    if [ ! -d "$OPENWRT_PATH/.git" ]; then
        git clone --depth 1 --single-branch --branch "$REPO_BRANCH" "$REPO_URL" "$OPENWRT_PATH"
        if [ "$(git -C "$OPENWRT_PATH" rev-parse HEAD)" != "$REPO_COMMIT" ]; then
            git -C "$OPENWRT_PATH" fetch --depth 1 origin "$REPO_COMMIT"
            git -C "$OPENWRT_PATH" checkout --detach "$REPO_COMMIT"
        fi
    fi
    cd "$OPENWRT_PATH"
    [ "$(git rev-parse HEAD)" = "$REPO_COMMIT" ] || {
        echo 'Source differs from configs/source.env; use a new volume for a new baseline.' >&2
        exit 1
    }
    local fingerprint
    fingerprint="$({
        find "$WORKSPACE/configs" "$WORKSPACE/files" "$WORKSPACE/package" \
            -type f -print0 | sort -z | xargs -0 sha256sum
        sha256sum "$WORKSPACE/scripts/Roc-script.sh" "$WORKSPACE/scripts/apply-package-updates.py"
    } | sha256sum | cut -d' ' -f1)"
    if [ ! -f .prepared ] || [ "$(cat .prepared)" != "$fingerprint" ]; then
        # These feeds are unrelated to the router profile. Keep NSS feeds intact.
        sed -i '/^src-git \(telephony\|video\) /d' feeds.conf.default
        ./scripts/feeds update -a
        GITHUB_WORKSPACE="$WORKSPACE" bash "$WORKSPACE/scripts/Roc-script.sh" "${seeds[@]}"
        printf '%s\n' "$fingerprint" > .prepared
    fi
    configure
}

configure() {
    cd "$OPENWRT_PATH"
    [ -f .prepared ] || { echo 'Run the prepare stage first' >&2; exit 1; }
    cat "${seeds[@]}" > .config
    make defconfig
    python3 "$WORKSPACE/scripts/verify-config.py" .config "${seeds[@]}"
    ./scripts/diffconfig.sh > "$BUILD_ROOT/artifacts/Arthur.diffconfig"
    cp .config "$BUILD_ROOT/artifacts/Arthur.config"
    cp selected-packages.txt "$BUILD_ROOT/artifacts/selected-packages.txt"
    cp "$WORKSPACE/configs/package-updates.json" "$BUILD_ROOT/artifacts/package-updates.json"
    {
        printf 'Repository\tBranch\tCommit\n'
        printf '%s\t%s\t%s\n' "$REPO_URL" "$REPO_BRANCH" "$(git rev-parse HEAD)"
        for feed in feeds/*; do
            [ -d "$feed/.git" ] || continue
            printf '%s\t%s\t%s\n' "$(git -C "$feed" remote get-url origin)" \
                "$(git -C "$feed" branch --show-current)" "$(git -C "$feed" rev-parse HEAD)"
        done
        tail -n +2 third-party-sources.txt
    } > "$BUILD_ROOT/artifacts/build-sources.txt"
}

case "$STAGE" in
    prepare) prepare ;;
    config) configure ;;
    download) configure; make download -j"$JOBS" ;;
    build)
        prepare
        make download -j"$JOBS"
        make -j"$JOBS" V=s
        cp -a bin/targets/qualcommax/ipq60xx/. "$BUILD_ROOT/artifacts/"
        ;;
    *) echo "Unknown stage: $STAGE" >&2; exit 1 ;;
esac
