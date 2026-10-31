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
HELPER = SOURCE.parents[2] / 'usr/libexec/arthur-docker-mount'
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
    local field device uuid
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -s) field=$2; shift ;;
            -t) uuid=${2#UUID=}; shift ;;
            "$TEST_ROOT"/dev/*) device=${1##*/} ;;
        esac
        shift
    done
    if [ -n "$uuid" ]; then
        for device in mmcblk0p27 mmcblk0p26; do
            if [ "$(cat "$TEST_ROOT/$device.UUID" 2>/dev/null)" = "$uuid" ]; then
                echo "$TEST_ROOT/dev/$device"
                return 0
            fi
        done
        return 1
    fi
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
    local device path root=/ id=179:27
    if [ "$1" = --bind ]; then
        [ ! -f "$TEST_ROOT/fail-bind" ] || return 1
        cp -a "$2/." "$3/"
        device="$TEST_ROOT/dev/mmcblk0p27"
        path=$3
        root=/docker
    else
    while [ "$#" -gt 0 ]; do
        case "$1" in -t|-o) shift ;; "$TEST_ROOT"/dev/*) device=$1 ;; *) path=$1 ;; esac
        shift
    done
    [ ! -f "$TEST_ROOT/fail-mount" ] || return 1
    if [ "$device" = "$TEST_ROOT/dev/mmcblk0p27" ]; then
        cp "$TEST_ROOT/storage-payload" "$path/preserved-file"
        if [ -d "$TEST_ROOT/storage-tree" ]; then cp -a "$TEST_ROOT/storage-tree/." "$path/"; fi
    else
        id=179:26
    fi
    fi
    printf '%s %s ext4 rw 0 0\n' "$device" "$path" >> "$TEST_ROOT/proc/mounts"
    printf '100 1 %s %s %s rw - ext4 %s rw\n' "$id" "$root" "$path" "$device" >> "$TEST_ROOT/proc/self/mountinfo"
}
umount() {
    record "umount $*"
    awk -v path="$1" '$2 != path' "$TEST_ROOT/proc/mounts" > "$TEST_ROOT/mounts-new"
    mv "$TEST_ROOT/mounts-new" "$TEST_ROOT/proc/mounts"
    awk -v path="$1" '$5 != path' "$TEST_ROOT/proc/self/mountinfo" > "$TEST_ROOT/mountinfo-new"
    mv "$TEST_ROOT/mountinfo-new" "$TEST_ROOT/proc/self/mountinfo"
    if [ "$1" = "$TEST_ROOT/opt/docker" ]; then
        command mv "$1" "$TEST_ROOT/old-opt-view"
        mkdir -p "$1"
    fi
}
pidof() { [ -f "$TEST_ROOT/running-docker" ]; }
rm() {
    if [ "${!#}" = "$TEST_ROOT/data/image" ] && [ -f "$TEST_ROOT/fail-cleanup" ]; then return 1; fi
    command rm "$@"
}
block() {
    record "block $*"
    if [ "$1" = mount ] && ! awk -v path="$TEST_ROOT/data" '$2 == path {found=1} END {exit !found}' "$TEST_ROOT/proc/mounts"; then
        mount -t ext4 "$TEST_ROOT/dev/mmcblk0p27" "$TEST_ROOT/data"
    fi
}
test_docker_mount() { ( . "$TEST_ROOT/runtime-helper.sh" ); }
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
        for folder in ('dev', 'sys/class/block/mmcblk0p27', 'proc/self', 'tmp/sysinfo',
                       'etc/config', 'lib', 'data', 'opt/docker', 'tmp/arthur-swap-check/lost+found'):
            (self.path / folder).mkdir(parents=True, exist_ok=True)
        self.write('tmp/sysinfo/board_name', 'jdcloud,re-ss-01')
        for file in ('dev/mmcblk0', 'dev/mmcblk0p26', 'proc/mounts', 'proc/self/mountinfo', 'etc/config/fstab', 'config', 'commands'):
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
        (self.path / name).parent.mkdir(parents=True, exist_ok=True)
        (self.path / name).write_text(value)

    def read(self, name):
        return (self.path / name).read_text()

    def run(self, success=True, helper=False, docker=False):
        # Redirect all absolute paths and only relax the block-node type check
        # in this disposable test copy. Production checks remain unchanged.
        def redirect(text):
            text = text.replace('[ -b ', '[ -f ')
            return re.sub(r'''/(dev|sys|proc|tmp|etc|lib|opt|usr|data)(?=/|[\s"']|$)''',
                          lambda match: str(self.path) + match[0], text)
        script = redirect(SOURCE.read_text()).replace(
            str(self.path) + '/usr/libexec/arthur-docker-mount', 'test_docker_mount')
        self.write('initializer.sh', script)
        self.write('runtime-helper.sh', redirect(HELPER.read_text()))
        # OpenWrt sources defaults inside a conditional; set -e is suppressed.
        action = (('test_docker_mount --docker' if docker else 'test_docker_mount') if helper else
                  'apply() { ( . "$1" ); }; apply "$TEST_ROOT/initializer.sh"')
        command = f'TEST_ROOT={str(self.path)!r}\n' + MOCKS + '\n' + action + ' && exit 0; exit 1\n'
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
        assert 'fstab.arthur_data.enabled=1' in router.read('config')
        assert f'fstab.arthur_data.target={router.path}/data' in router.read('config')
        assert f'mount --bind {router.path}/data/docker {router.path}/opt/docker' in commands
        assert 'fstab.arthur_swap.device=' in router.read('config')
        assert 'fstab.arthur_swap.priority=10' in router.read('config')
        assert '/dev/zram0 partition 206844 0 100' in router.read('proc/swaps')
        router.write('commands', '')
        commands = router.run()
        assert all(word not in commands for word in ('sgdisk ', 'mkfs.ext4 ', 'mkswap ', 'swapon '))
        assert router.read('data/preserved-file') == 'existing user data\n'

    for label in ('storage', 'legacy-docker'):
        router = Router(base / label, existing=True)
        router.write('label27', label)
        router.write('mmcblk0p26.TYPE', 'swap')
        router.write('mmcblk0p26.UUID', 'existing-swap-uuid')
        commands = router.run()
        assert all(word not in commands for word in ('sgdisk ', 'mkfs.ext4 ', 'mkswap '))
        assert router.read('mmcblk0p27.UUID') == 'existing-uuid'
        assert router.read('mmcblk0p26.UUID') == 'existing-swap-uuid'
        assert router.read('data/preserved-file') == 'existing user data\n'

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
    assert 'mount --bind ' not in router.run(success=False)
    assert router.read('opt/docker/old-docker-data') == 'must migrate first'

    router = Router(base / 'data-occupied', existing=True)
    router.write('data/user-file', 'must not cover')
    assert 'mount ' not in router.run(success=False)
    assert router.read('data/user-file') == 'must not cover'

    router = Router(base / 'mount-error', existing=True)
    router.write('fail-mount', '')
    assert 'fstab.arthur_data' not in router.read('config')
    router.run(success=False)
    assert 'fstab.arthur_data' not in router.read('config')

    router = Router(base / 'commit-error', existing=True)
    router.write('fail-commit', '')
    assert 'swapon ' not in router.run(success=False)

    router = Router(base / 'legacy-docker-cleanup', existing=True)
    router.write('storage-tree/engine-id', 'old-engine-id')
    router.write('storage-tree/key.json', 'old-engine-key')
    router.write('storage-tree/containers/container1/config', 'old-container')
    router.write('storage-tree/image/metadata', 'old-image')
    router.write('storage-tree/volumes/user-volume/file', 'old-volume')
    router.write('storage-tree/general-data/file', 'shared file')
    router.write('opt/docker/engine-id', 'old-engine-id')
    router.write('proc/mounts', f'{router.path}/dev/mmcblk0p27 {router.path}/opt/docker ext4 rw 0 0\n')
    router.write('proc/self/mountinfo', f'100 1 179:27 / {router.path}/opt/docker rw - ext4 {router.path}/dev/mmcblk0p27 rw\n')
    router.write('config', f'fstab.mountdocker=mount\nfstab.mountdocker.uuid=existing-uuid\nfstab.mountdocker.target={router.path}/opt/docker\nfstab.mountdocker.enabled=1\n')
    commands = router.run()
    assert f'umount {router.path}/opt/docker' in commands
    assert 'mkfs.ext4 ' not in commands
    assert 'fstab.mountdocker' not in router.read('config')
    for name in ('engine-id', 'key.json', 'containers', 'image', 'volumes'):
        assert not (router.path / 'data' / name).exists()
        assert not (router.path / 'data/docker' / name).exists()
    assert not list((router.path / 'opt/docker').iterdir())
    assert router.read('data/general-data/file') == 'shared file'
    assert not (router.path / 'data/docker/general-data').exists()

    router = Router(base / 'cleanup-resume', existing=True)
    router.write('storage-tree/engine-id', 'engine')
    router.write('storage-tree/containers/container1/config', 'container')
    router.write('storage-tree/image/metadata', 'image')
    router.write('fail-cleanup', '')
    router.run(success=False)
    assert router.read('data/.arthur-docker-cleanup').strip() == 'existing-uuid'
    assert not (router.path / 'data/containers').exists()
    assert router.read('data/image/metadata') == 'image'
    (router.path / 'fail-cleanup').unlink()
    router.run()
    assert not (router.path / 'data/.arthur-docker-cleanup').exists()
    assert not (router.path / 'data/image').exists()
    assert not list((router.path / 'opt/docker').iterdir())

    router = Router(base / 'two-docker-roots', existing=True)
    router.write('storage-tree/engine-id', 'old-root')
    router.write('storage-tree/docker/engine-id', 'different-root')
    router.run()
    assert not (router.path / 'data/engine-id').exists()
    assert router.read('data/docker/engine-id') == 'different-root'

    router = Router(base / 'mounted-old-docker-data', existing=True)
    router.run()
    router.write('data/engine-id', 'old-root')
    router.write('data/volumes/user-volume/file', 'must not be deleted while mounted')
    router.write('proc/self/mountinfo', router.read('proc/self/mountinfo') +
                 f'200 1 8:1 / {router.path}/data/volumes/user-volume rw - ext4 /dev/other rw\n')
    router.run(success=False)
    assert router.read('data/engine-id') == 'old-root'
    assert router.read('data/volumes/user-volume/file') == 'must not be deleted while mounted'

    router = Router(base / 'stale-fstab', existing=True)
    router.write('config', '\n'.join([
        'fstab.oldrom=mount', 'fstab.oldrom.target=/rom',
        'fstab.oldrom.uuid=gone-rom', 'fstab.oldrom.enabled=0',
        'fstab.oldoverlay=mount', 'fstab.oldoverlay.target=/overlay',
        'fstab.oldoverlay.uuid=gone-overlay', 'fstab.oldoverlay.enabled=0',
        'fstab.extroot=mount', 'fstab.extroot.target=/overlay',
        'fstab.extroot.uuid=custom-extroot', 'fstab.extroot.enabled=1',
        'fstab.other=mount', 'fstab.other.target=/mnt/user',
        'fstab.other.uuid=gone-user', 'fstab.other.enabled=0',
        'fstab.mountdocker=mount', f'fstab.mountdocker.target={router.path}/opt/docker',
        'fstab.mountdocker.uuid=gone-docker', 'fstab.mountdocker.enabled=1',
    ]) + '\n')
    router.run()
    assert 'fstab.oldrom' not in router.read('config')
    assert 'fstab.oldoverlay' not in router.read('config')
    assert 'fstab.extroot.uuid=custom-extroot' in router.read('config')
    assert 'fstab.other.uuid=gone-user' in router.read('config')
    assert 'fstab.mountdocker' not in router.read('config')

    router = Router(base / 'valid-disabled-system-entry', existing=True)
    router.write('mmcblk0p26.TYPE', 'swap')
    router.write('mmcblk0p26.UUID', 'valid-system-uuid')
    router.write('config', 'fstab.valid=mount\nfstab.valid.target=/rom\n'
                 'fstab.valid.uuid=valid-system-uuid\nfstab.valid.enabled=0\n')
    router.run()
    assert 'fstab.valid.uuid=valid-system-uuid' in router.read('config')

    router = Router(base / 'active-legacy-docker', existing=True)
    router.write('running-docker', '')
    router.write('proc/mounts', f'{router.path}/dev/mmcblk0p27 {router.path}/opt/docker ext4 rw 0 0\n')
    router.write('proc/self/mountinfo', f'100 1 179:27 / {router.path}/opt/docker rw - ext4 {router.path}/dev/mmcblk0p27 rw\n')
    assert 'umount ' not in router.run(success=False)

    router = Router(base / 'data-target-conflict', existing=True)
    router.write('config', f'fstab.user=mount\nfstab.user.target={router.path}/data\n'
                 'fstab.user.uuid=another-device\nfstab.user.enabled=1\n')
    assert 'mount ' not in router.run(success=False)
    assert 'fstab.user.uuid=another-device' in router.read('config')

    router = Router(base / 'custom-docker-root', existing=True)
    router.write('config', 'dockerd.globals.data_root=/mnt/custom-docker\n')
    assert 'mount ' not in router.run(helper=True, docker=True)

    router = Router(base / 'symlink-docker', existing=True)
    router.run()
    (router.path / 'data/docker').rmdir()
    (router.path / 'data/docker').symlink_to(router.path / 'etc', target_is_directory=True)
    router.run(success=False, helper=True)

    router = Router(base / 'bind-error', existing=True)
    router.write('fail-bind', '')
    router.run(success=False)
    assert router.read('data/preserved-file') == 'existing user data\n'
    (router.path / 'fail-bind').unlink()
    router.run()

    router = Router(base / 'wrong-bind', existing=True)
    router.run()
    router.write('proc/self/mountinfo', router.read('proc/self/mountinfo').replace('/docker ', '/wrong-root ', 1))
    router.run(success=False, helper=True)

    router = Router(base / 'runtime-remount', existing=True)
    router.run()
    router.write('proc/mounts', '')
    router.write('proc/self/mountinfo', '')
    (router.path / 'data/preserved-file').unlink()
    (router.path / 'data/docker').rmdir()
    commands = router.run(helper=True)
    assert 'block mount' in commands
    assert router.read('data/preserved-file') == 'existing user data\n'

    router = Router(base / 'running-correct-layout', existing=True)
    router.run()
    router.write('running-docker', '')
    router.write('commands', '')
    commands = router.run()
    assert 'umount ' not in commands and 'mount --bind ' not in commands

    router = Router(base / 'separate-docker-filesystem', existing=True)
    router.run()
    router.write('data/engine-id', 'must stay on original filesystem')
    router.write('proc/self/mountinfo', router.read('proc/self/mountinfo') +
                 f'200 1 8:1 / {router.path}/data/docker rw - ext4 /dev/other rw\n')
    router.run(success=False)
    assert router.read('data/engine-id') == 'must stay on original filesystem'

print('Storage checks passed: 64/128GB creation, existing/labeled or legacy p27 reuse, '
      '>1GiB limit, repeat runs, data preservation, unknown filesystems/no space, '
      'swap UUID/no-UUID, zram, /data plus Docker bind, legacy Docker cleanup/resume, '
      'stale disabled system mounts, mount/bind failures and runtime remount.')
