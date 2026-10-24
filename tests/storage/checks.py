#!/usr/bin/env python3
"""Run the initializer with isolated device/mount doubles; never touch real disks.

Usage: python3 tests/storage/checks.py
Requires bash. Real GPT geometry and ARM64 tools are additionally checked manually
on sparse disk images; the router verifies actual mounting, UCI and swap activation.
"""
from pathlib import Path
import re
import subprocess
import tempfile


SOURCE = Path(__file__).resolve().parents[2] / 'files/etc/uci-defaults/dockerd'
MOCKS = r'''
record() { printf '%s\n' "$*" >> "$TEST_ROOT/commands"; }
logger() { record "logger $*"; }
lsblk() {
    printf '%s disk\n' "$TEST_ROOT/dev/mmcblk0"
    printf '%s part swap\n' "$TEST_ROOT/dev/mmcblk0p26"
    if [ -f "$TEST_ROOT/dev/mmcblk0p27" ]; then
        printf '%s part %s\n' "$TEST_ROOT/dev/mmcblk0p27" "$(cat "$TEST_ROOT/label27")"
    fi
}
sgdisk() {
    record "sgdisk $*"
    case "$1" in
        --backup=*) : > "${1#--backup=}" ;;
        -F) echo 6258722 ;;
        -E) cat "$TEST_ROOT/last-sector" ;;
        -n)
            : > "$TEST_ROOT/dev/mmcblk0p27"
            echo storage > "$TEST_ROOT/label27"
            echo "$(( $(cat "$TEST_ROOT/last-sector") - 6258722 + 1 ))" > "$TEST_ROOT/sys/class/block/mmcblk0p27/size"
            ;;
    esac
}
partprobe() { record "partprobe $*"; }
blkid() {
    local field device
    while [ "$#" -gt 0 ]; do
        case "$1" in -s) field=$2; shift ;; "$TEST_ROOT"/dev/*) device=${1##*/} ;; esac
        shift
    done
    cat "$TEST_ROOT/$device.$field" 2>/dev/null
}
mkfs.ext4() {
    record "mkfs.ext4 $*"
    echo ext4 > "$TEST_ROOT/mmcblk0p27.TYPE"
    echo new-storage-uuid > "$TEST_ROOT/mmcblk0p27.UUID"
}
mkswap() {
    record "mkswap $*"
    echo swap > "$TEST_ROOT/mmcblk0p26.TYPE"
    rm -f "$TEST_ROOT/mmcblk0p26.UUID" # BusyBox mkswap does not generate one.
}
mount() {
    record "mount $*"
    local device path
    while [ "$#" -gt 0 ]; do
        case "$1" in -t|-o) shift ;; "$TEST_ROOT"/dev/*) device=$1 ;; *) path=$1 ;; esac
        shift
    done
    [ ! -f "$TEST_ROOT/fail-mount" ] || return 1
    printf '%s %s ext4 rw 0 0\n' "$device" "$path" >> "$TEST_ROOT/proc/mounts"
    if [ "$device" = "$TEST_ROOT/dev/mmcblk0p27" ]; then
        cp "$TEST_ROOT/storage-payload" "$path/preserved-file"
    fi
}
umount() {
    record "umount $*"
    awk -v path="$1" '$2 != path' "$TEST_ROOT/proc/mounts" > "$TEST_ROOT/mounts-new"
    mv "$TEST_ROOT/mounts-new" "$TEST_ROOT/proc/mounts"
}
swapon() {
    record "swapon $*"
    printf '%s partition 524284 0 10\n' "$3" >> "$TEST_ROOT/proc/swaps"
}
uci() {
    [ "$1" != -q ] || shift
    local operation=$1 key=${2%%=*} value=${2#*=}
    case "$operation" in
        get) awk -F= -v key="$key" '$1 == key {print substr($0, length(key)+2)}' "$TEST_ROOT/config" ;;
        set|delete)
            awk -F= -v key="$key" '$1 != key && index($1, key ".") != 1' "$TEST_ROOT/config" > "$TEST_ROOT/config-new"
            [ "$operation" != set ] || printf '%s=%s\n' "$key" "$value" >> "$TEST_ROOT/config-new"
            mv "$TEST_ROOT/config-new" "$TEST_ROOT/config"
            ;;
        commit) record 'uci commit'; [ ! -f "$TEST_ROOT/fail-commit" ] ;;
    esac
}
'''
FUNCTIONS = r'''
config_load() { :; }
config_get() { eval "$1=\$(uci -q get fstab.$2.$3)"; }
config_foreach() {
    local name value
    while IFS='=' read -r name value; do
        case "$name" in fstab.*.*) continue ;; esac
        if [ "$value" = "$2" ]; then "$1" "${name#fstab.}"; fi
    done < "$TEST_ROOT/config"
}
'''


class Router:
    def __init__(self, directory, sectors=119783424, existing=False, size=100000000):
        self.path = Path(directory)
        for folder in ('dev', 'sys/class/block/mmcblk0p27', 'proc', 'tmp/sysinfo',
                       'etc/config', 'lib', 'opt/docker', 'tmp/arthur-swap-check/lost+found'):
            (self.path / folder).mkdir(parents=True, exist_ok=True)
        self.write('tmp/sysinfo/board_name', 'jdcloud,re-ss-01')
        for file in ('dev/mmcblk0', 'dev/mmcblk0p26', 'proc/mounts', 'etc/config/fstab', 'config'):
            self.write(file, '')
        self.write('proc/swaps', '/dev/zram0 partition 206844 0 100\n')
        self.write('mmcblk0p26.TYPE', 'ext4')
        self.write('last-sector', str(sectors - 34))
        self.write('lib/functions.sh', FUNCTIONS)
        self.write('storage-payload', 'existing user data\n')
        if existing:
            self.write('dev/mmcblk0p27', '')
            self.write('label27', 'storage')
            self.write('sys/class/block/mmcblk0p27/size', str(size))
            self.write('mmcblk0p27.TYPE', 'ext4')
            self.write('mmcblk0p27.UUID', 'existing-uuid')

    def write(self, name, value):
        (self.path / name).write_text(value)

    def read(self, name):
        return (self.path / name).read_text()

    def run(self, success=True):
        # Redirect all absolute paths and only relax the block-node type check
        # in this disposable test copy. Production checks remain unchanged.
        script = SOURCE.read_text().replace('[ -b ', '[ -f ')
        script = re.sub(r'/(dev|sys|proc|tmp|etc|lib|opt)/',
                        lambda match: str(self.path) + match[0], script)
        self.write('initializer.sh', script)
        # OpenWrt sources defaults inside a conditional; set -e is suppressed.
        command = (f'TEST_ROOT={str(self.path)!r}\n' + MOCKS +
                   '\napply() { ( . "$1" ); }; apply "$TEST_ROOT/initializer.sh" && exit 0; exit 1\n')
        result = subprocess.run(['bash', '-c', command], capture_output=True, text=True, timeout=10)
        assert (result.returncode == 0) == success, result.stderr + self.read('commands')
        return self.read('commands')


with tempfile.TemporaryDirectory(prefix='arthur-storage-tests-') as directory:
    base = Path(directory)
    for label, sectors in [('64g', 119783424), ('128g', 250000000)]:
        router = Router(base / label, sectors=sectors)
        commands = router.run()
        assert commands.count('mkfs.ext4 ') == 1
        assert commands.count('mkswap ') == 1
        assert 'fstab.mountdocker.enabled=1' in router.read('config')
        assert 'fstab.arthur_swap.device=' in router.read('config')
        assert 'fstab.arthur_swap.priority=10' in router.read('config')
        assert '/dev/zram0 partition 206844 0 100' in router.read('proc/swaps')
        router.write('commands', '')
        commands = router.run()
        assert all(word not in commands for word in ('sgdisk ', 'mkfs.ext4 ', 'mkswap ', 'swapon '))
        assert router.read('opt/docker/preserved-file') == 'existing user data\n'

    for label in ('storage', 'legacy-docker'):
        router = Router(base / label, existing=True)
        router.write('label27', label)
        router.write('mmcblk0p26.TYPE', 'swap')
        router.write('mmcblk0p26.UUID', 'existing-swap-uuid')
        commands = router.run()
        assert all(word not in commands for word in ('sgdisk ', 'mkfs.ext4 ', 'mkswap '))
        assert router.read('mmcblk0p27.UUID') == 'existing-uuid'
        assert router.read('mmcblk0p26.UUID') == 'existing-swap-uuid'
        assert router.read('opt/docker/preserved-file') == 'existing user data\n'

    for size in (1000000, 2097152):
        router = Router(base / f'small-{size}', existing=True, size=size)
        commands = router.run(success=False)
        assert all(word not in commands for word in ('sgdisk ', 'mkfs.ext4 ', 'mount ', 'mkswap '))

    for filesystem in ('', 'xfs'):
        router = Router(base / f'unknown-{filesystem or "blank"}', existing=True)
        router.write('mmcblk0p27.TYPE', filesystem)
        commands = router.run(success=False)
        assert all(word not in commands for word in ('sgdisk ', 'mkfs.ext4 ', 'mount '))

    router = Router(base / 'no-space', sectors=6258722 + 2097152 + 33)
    commands = router.run(success=False)
    assert all(word not in commands for word in ('sgdisk -n ', 'mkfs.ext4 ', 'mount '))

    for label, filename in [('swap-data', 'tmp/arthur-swap-check/user-file'),
                            ('swap-recovered', 'tmp/arthur-swap-check/lost+found/recovered')]:
        router = Router(base / label, existing=True)
        router.write(filename, 'must not erase')
        commands = router.run(success=False)
        assert 'mkswap ' not in commands
        assert router.read(filename) == 'must not erase'

    router = Router(base / 'occupied', existing=True)
    router.write('opt/docker/old-docker-data', 'must migrate first')
    assert 'mount ' not in router.run(success=False)

    router = Router(base / 'mount-error', existing=True)
    router.write('fail-mount', '')
    assert 'fstab.mountdocker' not in router.read('config')
    router.run(success=False)
    assert 'fstab.mountdocker' not in router.read('config')

    router = Router(base / 'commit-error', existing=True)
    router.write('fail-commit', '')
    assert 'swapon ' not in router.run(success=False)

print('Storage checks passed: 64/128GB creation, existing/labeled or legacy p27 reuse, '
      '>1GiB limit, repeat runs, data preservation, unknown filesystems/no space, '
      'swap UUID/no-UUID, zram and mount failure.')
