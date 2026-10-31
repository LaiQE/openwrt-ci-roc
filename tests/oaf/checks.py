#!/usr/bin/env python3
"""Exercise installed OAF defaults/startup and preserve later user opt-in."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


root = Path(sys.argv[1]).resolve()
for program in ('proot', 'qemu-aarch64'):
    assert shutil.which(program), f'Missing build-host tool: {program}'
settings = ('global.tcp_rst', 'appfilter.enable', 'macfilter.enable', 'record.enable')

with tempfile.TemporaryDirectory(prefix='arthur-oaf-') as temporary:
    temporary = Path(temporary)
    etc, tmp = temporary / 'etc', temporary / 'tmp'
    shutil.copytree(root / 'etc', etc, symlinks=True)
    (tmp / '.uci').mkdir(parents=True)
    (tmp / 'lock').mkdir()

    def run(*command):
        result = subprocess.run([
            'proot', '-q', shutil.which('qemu-aarch64'), '-r', str(root),
            '-b', f'{etc}:/etc', '-b', f'{tmp}:/tmp',
            '-b', '/dev:/dev', '-b', '/proc:/proc', '-w', '/', *command,
        ], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (command, result.stdout, result.stderr)
        return result.stdout.strip()

    def check_settings(value):
        for setting in settings:
            assert run('/sbin/uci', 'get', 'fwx.' + setting) == value, setting
        assert run('/sbin/uci', 'get', 'fwx.advanced.disable_hnat') == '0'

    check_settings('0')
    run('/etc/init.d/appfilter', 'enabled')

    # Invoke the actual startup/config generator; isolate only kernel-module
    # detection and procd spawning. No daemon or filter starts on the build host.
    service = etc / 'init.d/appfilter'
    service.write_text(service.read_text() + '''
test_start() {
    lsmod() { echo oaf; }
    procd_open_instance() { :; }
    procd_set_param() { printf '%s\\n' "$*" >> /tmp/oaf-procd; }
    procd_close_instance() { :; }
    start_service
}
extra_command test_start "Exercise isolated OAF startup"
''')
    run('/etc/init.d/appfilter', 'test_start')
    check_settings('0')
    commands = (tmp / 'oaf-procd').read_text()
    assert 'command /usr/bin/oafd' in commands, commands
    assert 'command /usr/bin/rule_manager' in commands, commands

    # Missing UCI config (e.g. after resetting this package) uses the same off
    # defaults as the shipped template, rather than resurrecting upstream ones.
    (etc / 'config/fwx').unlink()
    run('/etc/init.d/appfilter', 'test_start')
    check_settings('0')

    for setting in settings:
        run('/sbin/uci', 'set', 'fwx.' + setting + '=1')
    run('/sbin/uci', 'commit', 'fwx')
    run('/etc/init.d/appfilter', 'test_start')
    check_settings('1')

print('OAF checks passed: four features off by default, management backend enabled, '
      'fallback config off, later user opt-in preserved, NSS disable option untouched')
