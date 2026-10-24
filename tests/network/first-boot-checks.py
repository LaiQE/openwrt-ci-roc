#!/usr/bin/env python3
"""Exercise actual ARM64 first-boot scripts and DHCP tools without router hardware.

Usage: python3 tests/network/first-boot-checks.py ROOTFS [ARTHUR_DEFAULTS]
Requires proot and qemu-aarch64 on the build host. Configuration writes are
redirected to temporary /etc and /tmp; the compiled rootfs is not modified.
"""
import ipaddress
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


root = Path(sys.argv[1]).resolve()
defaults = (Path(sys.argv[2]) if len(sys.argv) > 2 else
            root / 'etc/uci-defaults/99-arthur-defaults')
for program in ('proot', 'qemu-aarch64'):
    if not shutil.which(program):
        raise SystemExit(f'Required build-host tool is missing: {program}')

# Verify the installed module policy, before any first-boot script can run.
# The LibWrt validation image must actually enable Wi-Fi NSS.
ath11k = (root / 'etc/modules.d/ath11k').read_text().split()
assert ath11k == ['ath11k', 'nss_offload=1', 'frame_mode=2'], ath11k


class Router:
    def __init__(self, directory, board='jdcloud,re-ss-01'):
        self.directory = Path(directory)
        self.etc = self.directory / 'etc'
        self.tmp = self.directory / 'tmp'
        shutil.copytree(root / 'etc', self.etc, symlinks=True)
        (self.tmp / '.uci').mkdir(parents=True)
        (self.tmp / 'lock').mkdir()
        (self.tmp / 'sysinfo').mkdir()
        (self.tmp / 'sysinfo/board_name').write_text(board + '\n')
        (self.tmp / 'arthur-defaults').write_bytes(defaults.read_bytes())
        self.vim = self.directory / 'vim'
        if (root / 'usr/share/vim').is_dir():
            shutil.copytree(root / 'usr/share/vim', self.vim, symlinks=True)
        for name in ('network', 'system'):
            (self.etc / 'config' / name).unlink(missing_ok=True)
        (self.etc / 'board.json').write_text(json.dumps({
            'model': {'id': board, 'name': 'JDCloud RE-SS-01'},
            'network': {
                'lan': {'ports': ['lan1', 'lan2', 'lan3'], 'protocol': 'static'},
                'wan': {'device': 'wan', 'protocol': 'dhcp'},
            },
        }))

    def run(self, *command, check=True):
        bindings = ['-b', f'{self.vim}:/usr/share/vim'] if self.vim.is_dir() else []
        result = subprocess.run([
            'proot', '-q', shutil.which('qemu-aarch64'), '-r', str(root),
            '-b', f'{self.etc}:/etc', '-b', f'{self.tmp}:/tmp',
            '-b', '/dev:/dev', '-b', '/proc:/proc', *bindings, '-w', '/', *command,
        ], capture_output=True, text=True, timeout=60)
        if check and result.returncode:
            raise AssertionError(f'{command}:\n{result.stdout}\n{result.stderr}')
        return result

    def get(self, key):
        return self.run('/sbin/uci', '-q', 'get', key, check=False).stdout.strip()

    def generate(self):
        self.run('/bin/config_generate')

    def apply(self, *scripts):
        # boot sources each defaults file in a subshell inside a shell function.
        self.run('/bin/sh', '-c',
                 'apply() { ( . "$1" ); }; for script do apply "$script" || exit; done',
                 'defaults', *scripts)

    def check_pool(self):
        address = self.get('network.lan.ipaddr')
        netmask = self.get('network.lan.netmask')
        if '/' not in address:
            # netifd proto_apply_static_ip_settings() defaults to /32.
            address += '/' + (netmask or '32')
        interface = ipaddress.ip_interface(address)
        assert interface == ipaddress.ip_interface('192.168.233.1/24'), address
        result = self.run('/bin/ipcalc.sh', address,
                          self.get('dhcp.lan.start'), self.get('dhcp.lan.limit'))
        pool = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        assert pool['START'] == '192.168.233.100', pool
        assert pool['END'] == '192.168.233.249', pool
        assert pool['NETMASK'] == '255.255.255.0', pool
        assert self.get('dhcp.lan.ignore') != '1'
        assert self.get('dhcp.lan.dhcpv4') != 'disabled'
        (self.tmp / 'dnsmasq-test.conf').write_text(
            f"dhcp-range=set:lan,{pool['START']},{pool['END']},{pool['NETMASK']},12h\n")
        self.run('/usr/sbin/dnsmasq', '--test', '-C', '/tmp/dnsmasq-test.conf')


with tempfile.TemporaryDirectory(prefix='arthur-first-boot-') as temporary:
    router = Router(Path(temporary) / 'arthur')
    router.generate()
    assert router.get('network.lan.ipaddr') == '192.168.1.1/24'
    router.apply('/etc/uci-defaults/11_network-migrate-bridges',
                 '/etc/uci-defaults/12_network-generate-ula',
                 '/etc/uci-defaults/14_network-generate-duid',
                 '/etc/uci-defaults/15_odhcpd',
                 '/tmp/arthur-defaults',
                 '/etc/uci-defaults/991_set-network.sh')
    assert router.get('network.lan.proto') == 'static'
    assert router.get('network.lan.device') == 'br-lan'
    assert router.get('network.@device[0].ports') == 'lan1 lan2 lan3'
    assert router.get('network.wan.proto') == 'dhcp'
    assert router.get('network.wan.device') == 'wan'
    router.check_pool()
    ula = ipaddress.IPv6Network(router.get('network.globals.ula_prefix'))
    assert ula.prefixlen == 48 and ula.subnet_of(ipaddress.IPv6Network('fd00::/8')), ula
    router.run('/bin/busybox', 'lsusb')
    if (root / 'usr/bin/zsh').is_file():
        root_account = next(line for line in (router.etc / 'passwd').read_text().splitlines()
                            if line.startswith('root:'))
        assert root_account.endswith(':/usr/bin/zsh'), root_account
        assert router.get('ttyd.@ttyd[0].command') == '/bin/login -f root'

    # Fresh defaults disable Docker in rc.d and in the Dockerman checkbox.
    assert router.get('dockerd.globals.auto_start') == '0'
    assert router.run('/etc/init.d/dockerd', 'enabled', check=False).returncode != 0

    # Repair the exact invalid state shipped by the first 25.12 image.
    router.run('/sbin/uci', 'set', 'network.lan.ipaddr=192.168.233.1')
    router.run('/sbin/uci', 'commit', 'network')
    router.apply('/tmp/arthur-defaults')
    router.check_pool()

    # Reapplying defaults on an upgrade must preserve the user's LAN subnet.
    router.run('/sbin/uci', 'set', 'network.lan.ipaddr=10.23.4.1/23')
    router.run('/sbin/uci', 'commit', 'network')
    router.apply('/tmp/arthur-defaults')
    assert router.get('network.lan.ipaddr') == '10.23.4.1/23'

    # A later administrator opt-in survives a defaults rerun on upgrade.
    router.run('/etc/init.d/dockerd', 'enable')
    router.run('/sbin/uci', 'set', 'dockerd.globals.auto_start=1')
    router.run('/sbin/uci', 'commit', 'dockerd')
    router.apply('/tmp/arthur-defaults')
    assert router.get('dockerd.globals.auto_start') == '1'
    router.run('/etc/init.d/dockerd', 'enabled')

    router.run('/sbin/uci', 'set', 'network.globals.ula_prefix=fd12:3456:789a::/48')
    router.run('/sbin/uci', 'commit', 'network')
    router.apply('/etc/uci-defaults/12_network-generate-ula',
                 '/etc/uci-defaults/991_set-network.sh')
    assert router.get('network.globals.ula_prefix') == 'fd12:3456:789a::/48'

    other = Router(Path(temporary) / 'other', board='example,other-router')
    other.generate()
    other.apply('/etc/uci-defaults/12_network-generate-ula')
    assert other.get('network.globals.ula_prefix') != str(ula)
    before = (other.etc / 'config/network').read_bytes()
    other.apply('/tmp/arthur-defaults')
    assert (other.etc / 'config/network').read_bytes() == before

print('First-boot checks passed: clean ARM64 initialization, LAN/WAN bridge mapping, '
      'DHCP pool and dnsmasq parsing, broken-state repair, custom subnet retention, '
      'random/custom ULA retention, Docker default-off and manual opt-in, '
      'board guard, LibWrt Wi-Fi NSS enabled at module load')
