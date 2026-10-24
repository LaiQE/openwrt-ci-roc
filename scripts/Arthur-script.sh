#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE="${GITHUB_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DEVICE_CONFIG_FILE="${1:-${CONFIG_FILE:-}}"
GENERAL_CONFIG_FILE="${2:-${GENERAL_CONFIG_FILE:-configs/Arthur-General.config}}"
GIT_CLONE_RETRY_COUNT="${GIT_CLONE_RETRY_COUNT:-3}"
THIRD_PARTY_SOURCES_FILE="${THIRD_PARTY_SOURCES_FILE:-$PWD/third-party-sources.txt}"

case "$GIT_CLONE_RETRY_COUNT" in
  '' | *[!0-9]* | 0)
    echo "Error: GIT_CLONE_RETRY_COUNT must be a positive integer" >&2
    exit 1
    ;;
esac

resolve_config_file() {
  local config_file="$1"

  if [ -f "$config_file" ]; then
    printf '%s\n' "$config_file"
  elif [ -f "$WORKSPACE/$config_file" ]; then
    printf '%s\n' "$WORKSPACE/$config_file"
  else
    echo "Error: configuration file was not found: $config_file" >&2
    return 1
  fi
}

CONFIG_FILES=()
if [ -n "$DEVICE_CONFIG_FILE" ]; then
  CONFIG_FILES+=("$(resolve_config_file "$DEVICE_CONFIG_FILE")")
elif [ -f .config ]; then
  # Keep direct invocations compatible with an existing OpenWrt .config.
  CONFIG_FILES+=("$PWD/.config")
else
  echo "Error: pass the device config as the first argument or CONFIG_FILE" >&2
  exit 1
fi
CONFIG_FILES+=("$(resolve_config_file "$GENERAL_CONFIG_FILE")")

config_symbol_enabled() {
  local symbol="$1"

  awk -v symbol="$symbol" '
    { sub(/\r$/, "") }
    $0 == symbol "=y" || $0 == symbol "=m" { enabled = 1; next }
    $0 == symbol "=n" || $0 == "# " symbol " is not set" { enabled = 0 }
    END { exit(enabled ? 0 : 1) }
  ' "${CONFIG_FILES[@]}"
}

target_device_package_enabled() {
  local package_name="$1"

  awk -v package_name="$package_name" '
    { sub(/\r$/, "") }
    /^CONFIG_TARGET_DEVICE_PACKAGES_[^=]+="/ {
      packages = $0
      sub(/^[^"]*"/, "", packages)
      sub(/"$/, "", packages)
      count = split(packages, values, /[[:space:]]+/)
      for (i = 1; i <= count; i++) {
        if (values[i] == package_name) {
          found = 1
        }
      }
    }
    END { exit(found ? 0 : 1) }
  ' "${CONFIG_FILES[@]}"
}

package_enabled() {
  local package_name

  for package_name in "$@"; do
    if config_symbol_enabled "CONFIG_PACKAGE_$package_name" || target_device_package_enabled "$package_name"; then
      return 0
    fi
  done

  return 1
}

clone_with_retry() {
  local target_dir="$1"
  local attempt
  shift

  for ((attempt = 1; attempt <= GIT_CLONE_RETRY_COUNT; attempt++)); do
    rm -rf "$target_dir"
    if git clone "$@" "$target_dir"; then
      return 0
    fi

    if [ "$attempt" -lt "$GIT_CLONE_RETRY_COUNT" ]; then
      echo "Git clone failed; retrying ($((attempt + 1))/$GIT_CLONE_RETRY_COUNT): ${*: -1}" >&2
      sleep $((attempt * 2))
    fi
  done

  echo "Error: git clone failed after $GIT_CLONE_RETRY_COUNT attempts: ${*: -1}" >&2
  return 1
}

record_git_revision() {
  local repo_url="$1"
  local branch="$2"
  local checkout_dir="$3"
  local commit
  local revision

  commit="$(git -C "$checkout_dir" rev-parse HEAD)"
  printf -v revision '%s\t%s\t%s' "$repo_url" "$branch" "$commit"
  grep -Fqx -- "$revision" "$THIRD_PARTY_SOURCES_FILE" || printf '%s\n' "$revision" >> "$THIRD_PARTY_SOURCES_FILE"
}

clone_repository() {
  local repo_url="$1"
  local branch="$2"
  local target_dir="$3"

  clone_with_retry "$target_dir" \
    --depth=1 \
    --no-tags \
    --branch "$branch" \
    --single-branch \
    "$repo_url"
  record_git_revision "$repo_url" "$branch" "$target_dir"
}

mkdir -p "$(dirname "$THIRD_PARTY_SOURCES_FILE")"
printf 'Repository\tBranch\tCommit\n' > "$THIRD_PARTY_SOURCES_FILE"

# Keep firmware policy in an overlay instead of patching LuCI JavaScript or account files.
[ -f package/base-files/files/bin/config_generate ] || { echo "Run from the OpenWrt source root" >&2; exit 1; }
mkdir -p files/etc/uci-defaults
install -m 0755 "$WORKSPACE/files/etc/uci-defaults/99-arthur-defaults" files/etc/uci-defaults/
rm -rf package/luci-app-srun-autologin
mkdir -p package/luci-app-srun-autologin
cp -a "$WORKSPACE/package/luci-app-srun-autologin/." package/luci-app-srun-autologin/

# Use the matching official 25.12 feeds for Go, AdGuard Home, Tailscale, DDNS,
# Argon and disk management. Import matching current FRP recipes and LuCI.
if package_enabled luci-app-passwall; then
  rm -rf feeds/luci/applications/luci-app-passwall
  rm -rf feeds/packages/net/{xray-core,v2ray-geodata,sing-box,chinadns-ng,dns2socks,hysteria,ipt2socks,microsocks,naiveproxy,shadowsocks-libev,shadowsocks-rust,shadowsocksr-libev,simple-obfs,tcping,trojan-plus,tuic-client,v2ray-plugin,xray-plugin,geoview,shadow-tls}
  clone_repository https://github.com/Openwrt-Passwall/openwrt-passwall-packages main package/passwall-packages
  clone_repository https://github.com/Openwrt-Passwall/openwrt-passwall main package/luci-app-passwall
fi

git_sparse_replace() {
  local repo_url="$1" branch="$2" repo_dir path
  shift 2
  repo_dir="$(mktemp -d "$PWD/.package-update.XXXXXX")"
  clone_with_retry "$repo_dir" --depth=1 --no-tags --branch "$branch" --single-branch --filter=blob:none --sparse "$repo_url"
  git -C "$repo_dir" sparse-checkout set "$@"
  record_git_revision "$repo_url" "$branch" "$repo_dir"
  for path in "$@"; do
    [ -d "$repo_dir/$path" ] || { echo "Missing package path: $path" >&2; exit 1; }
    case "$path" in
      applications/*) rm -rf "feeds/luci/$path"; mv "$repo_dir/$path" "feeds/luci/$path" ;;
      *) rm -rf "feeds/packages/$path"; mv "$repo_dir/$path" "feeds/packages/$path" ;;
    esac
  done
  rm -rf "$repo_dir"
}

if package_enabled luci-app-frpc luci-app-multi-frpc frpc; then
  git_sparse_replace https://github.com/immortalwrt/packages master net/frp
fi
if package_enabled luci-app-frpc; then
  git_sparse_replace https://github.com/immortalwrt/luci master applications/luci-app-frpc
fi
if package_enabled docker-compose; then
  git_sparse_replace https://github.com/immortalwrt/packages master utils/docker-compose
fi

if package_enabled luci-app-multi-frpc; then
  clone_repository https://github.com/justice2001/luci-app-multi-frpc main package/luci-app-multi-frpc
  # This unused import is the only reason the old UI needed luci-lib-ipkg.
  sed -i '/require.*luci\.model\.ipkg/d' package/luci-app-multi-frpc/luasrc/model/cbi/frp/basic.lua
  sed -i 's/LUCI_DEPENDS:=/LUCI_DEPENDS:=+luci-compat /' package/luci-app-multi-frpc/Makefile
fi
if package_enabled luci-app-wolplus; then
  clone_repository https://github.com/sakura-builder1/luci-app-wolplus main package/luci-app-wolplus
fi
if package_enabled luci-app-onliner; then
  clone_repository https://github.com/haiibo/packages main package/onliner-source
  rm -rf package/luci-app-onliner
  mv package/onliner-source/luci-app-onliner package/luci-app-onliner
  rm -rf package/onliner-source
  sed -i 's/LUCI_DEPENDS:=.*/LUCI_DEPENDS:=+luci-compat +nlbwmon/' package/luci-app-onliner/Makefile
  chmod +x package/luci-app-onliner/root/usr/share/onliner/setnlbw.sh
fi
if package_enabled luci-app-homebox; then
  clone_repository https://github.com/jjm2473/openwrt-apps main package/homebox-source
  rm -rf package/homebox-apps
  mkdir -p package/homebox-apps
  cp package/homebox-source/luci-alias.mk package/homebox-apps/
  mv package/homebox-source/luci-app-homebox package/homebox-apps/
  rm -rf package/homebox-source
  cp -a "$WORKSPACE/package/homebox" package/homebox-apps/homebox
  sed -i 's/PKG_VERSION:=1.0.1-r4/PKG_VERSION:=1.0.1/;s/^PKG_RELEASE:=$/PKG_RELEASE:=4/' package/homebox-apps/luci-app-homebox/Makefile
fi

python3 "$WORKSPACE/scripts/apply-package-updates.py" "$WORKSPACE/configs/package-updates.json"

./scripts/feeds update -i -a
./scripts/feeds install -a
# The current 25.12 feed has an unrelated weechat-full/minimal Kconfig cycle.
# Do not expose that unused UI package to Kconfig (it is never selected here).
rm -f package/feeds/luci/luci-app-weechat
