#!/usr/bin/env python3
"""Test the real bind/mountinfo path in an isolated mount namespace/container.

Requires CAP_SYS_ADMIN. Uses only a temporary tmpfs, never a disk. Board/UCI/
filesystem identity are doubles; mount, mountinfo and file aliases are real.
Usage: python3 tests/storage/bind-checks.py [RUNTIME_HELPER]
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


helper = (Path(sys.argv[1]) if len(sys.argv) > 1 else
          Path(__file__).resolve().parents[2] / 'files/usr/libexec/arthur-docker-mount')


def mounted(path):
    return [line for line in Path('/proc/self/mountinfo').read_text().splitlines()
            if line.split()[4] == str(path)]


with tempfile.TemporaryDirectory(prefix='arthur-real-bind-') as directory:
    base = Path(directory)
    data, target = base / 'data', base / 'opt/docker'
    data.mkdir()
    target.mkdir(parents=True)
    subprocess.run(['mount', '-t', 'tmpfs', 'arthur-data-test', str(data)], check=True)
    try:
        (data / 'docker').mkdir()
        (data / 'docker/container-file').write_text('preserved container data')
        (data / 'shared-file').write_text('general data')
        script = helper.read_text().replace('data=/data\n', f'data={data}\n')
        script = script.replace('target=/opt/docker\n', f'target={target}\n')
        (base / 'helper.sh').write_text(script)
        environment = os.environ | {'TEST_DATA': str(data), 'TEST_HELPER': str(base / 'helper.sh')}
        command = r'''
cat() {
    if [ "$1" = /tmp/sysinfo/board_name ]; then echo jdcloud,re-ss-01; else command cat "$@"; fi
}
uci() {
    [ "$1" != -q ] || shift
    case "$2" in
        fstab.arthur_data.uuid) echo fixture-uuid ;;
        fstab.arthur_data.enabled) echo 1 ;;
        fstab.arthur_data.target) echo "$TEST_DATA" ;;
        *) return 1 ;;
    esac
}
blkid() {
    case "$*" in *' TYPE '*) echo ext4 ;; *) echo fixture-uuid ;; esac
}
pidof() { return 1; }
. "$TEST_HELPER"
'''

        def run(success=True):
            result = subprocess.run(['bash', '-c', command], env=environment,
                                    text=True, capture_output=True, timeout=40)
            assert (result.returncode == 0) == success, result.stderr

        run()
        assert len(mounted(target)) == 1
        original = (data / 'docker/container-file').stat()
        alias = (target / 'container-file').stat()
        assert (original.st_dev, original.st_ino) == (alias.st_dev, alias.st_ino)
        (target / 'new-file').write_text('written through bind')
        assert (data / 'docker/new-file').read_text() == 'written through bind'
        assert (data / 'shared-file').read_text() == 'general data'
        assert not (target / 'shared-file').exists()
        run()
        assert len(mounted(target)) == 1, 'Repeated start stacked another bind'

        subprocess.run(['umount', str(target)], check=True)
        (target / 'overlay-file').write_text('must not be hidden')
        run(success=False)
        assert not mounted(target)
        assert (target / 'overlay-file').read_text() == 'must not be hidden'
        (target / 'overlay-file').unlink()
        run()
        assert (target / 'container-file').read_text() == 'preserved container data'
    finally:
        if mounted(target):
            subprocess.run(['umount', str(target)], check=True)
        subprocess.run(['umount', str(data)], check=True)

print('Real bind checks passed: inode alias, writes, shared data separation, '
      'idempotence, overlay data protection and rebind; no real disks used')
