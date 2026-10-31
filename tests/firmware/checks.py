#!/usr/bin/env python3
"""Validate the built Arthur image contents before local export or CI release."""
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys

root, target = (Path(argument).resolve() for argument in sys.argv[1:])
profiles = json.loads((target / 'profiles.json').read_text())['profiles']
assert set(profiles) == {'jdcloud_re-ss-01'}, list(profiles)
manifest, = target.glob('*.manifest')
packages = dict(line.split(' - ', 1) for line in manifest.read_text().splitlines()
                if ' - ' in line)
required = {
    'luci-app-srun-autologin', 'luci-app-ddns-go', 'ddns-go', 'luci-app-wolplus',
    'luci-app-dockerman', 'luci-lib-docker', 'dockerd', 'docker', 'docker-compose',
    'luci-app-diskman', 'luci-app-passwall', 'xray-core', 'sing-box', 'hysteria',
    'geoview', 'xl2tpd', 'ppp-mod-pppol2tp', 'luci-proto-wireguard',
    'luci-app-zerotier', 'luci-app-tailscale', 'luci-app-adguardhome',
    'adguardhome', 'luci-app-multi-frpc', 'luci-app-onliner', 'luci-app-homebox',
    'homebox', 'luci-theme-argon', 'luci-app-cpufreq', 'luci-app-ttyd',
    'luci-app-autoreboot', 'luci-app-irqbalance', 'luci-app-upnp', 'luci-app-arpbind',
    'kmod-usb3', 'kmod-usb-dwc3', 'kmod-usb-dwc3-qcom', 'kmod-usb-storage',
    'kmod-usb-storage-uas', 'kmod-qca-nss-drv', 'kmod-qca-nss-dp',
    'kmod-qca-nss-ecm', 'kmod-qca-nss-crypto', 'kmod-qca-mcs', 'kmod-nss-ifb',
    'nssinfo', 'automount', 'luci-app-oaf', 'appfilter', 'kmod-oaf',
    'luci-i18n-oaf-zh-cn',
    'git', 'git-http', 'git-lfs', 'vim', 'zsh', 'screen', 'dmesg', 'cfdisk',
    'gdisk', 'tune2fs', 'net-tools-netstat', 'net-tools-route', 'zoneinfo-asia',
}
managers = ('bridge-mgr', 'eogremgr', 'gre', 'igs', 'l2tpv2', 'lag-mgr',
            'map-t', 'match', 'mirror', 'netlink', 'pppoe', 'pptp', 'qdisc',
            'tun6rd', 'tunipip6', 'vlan-mgr', 'vxlanmgr', 'wifi-meshmgr')
required.update('kmod-qca-nss-drv-' + name for name in managers)
assert not required - packages.keys(), sorted(required - packages.keys())
for name in packages:
    assert name not in {'luci-app-ddns', 'vlmcsd', 'luci-app-vlmcsd',
                        'mwan3', 'luci-app-mwan3',
                        'luci-app-appfilter', 'open-app-filter'}, name
    assert not name.startswith(('ddns-scripts', 'luci-i18n-vlmcsd-')), name
    assert (not name.startswith('luci-i18n-ddns-') or
            name.startswith('luci-i18n-ddns-go-')), name
for name in ('kmod-qca-nss-drv', 'kmod-qca-nss-drv-l2tpv2',
             'kmod-qca-nss-drv-wifi-meshmgr'):
    assert '11.4.' in packages[name], (name, packages[name])
assert b'NSS.CP.11.4.0.5-6-R' in (
    root / 'lib/firmware/qca-nss0-retail.bin').read_bytes()

repository_files = list((root / 'etc/apk/repositories.d').glob('*'))
repositories = [line.strip() for path in repository_files if path.is_file()
                for line in path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
assert repositories, 'No APK repositories installed'
for url in repositories:
    assert '/nss_packages/' not in url and '/sqm_scripts_nss/' not in url, url
for feed in ('base', 'luci', 'packages', 'routing'):
    assert any(url.endswith(f'/{feed}/packages.adb') for url in repositories), feed

images = [target / item['name'] for item in profiles['jdcloud_re-ss-01']['images']]
assert images and any('sysupgrade' in path.name for path in images), images
for path in images:
    assert path.is_file() and path.stat().st_size > 1024 * 1024, path
for line in (target / 'sha256sums').read_text().splitlines():
    digest, filename = line.split(maxsplit=1)
    path = target / filename.lstrip('*')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path

for program in ('srun', 'srun-autologin', 'sing-box', 'hysteria', 'xray',
                'dockerd', 'docker', 'homebox', 'zsh'):
    path = root / 'usr/bin' / program
    assert path.is_file() and os.access(path, os.X_OK), path
binary = (root / 'usr/bin/srun').read_bytes()
assert binary[:4] == b'\x7fELF' and struct.unpack('<H', binary[18:20])[0] == 183
config = root / 'etc/config/srun-autologin'
assert stat.S_IMODE(config.stat().st_mode) == 0o600
text = config.read_text()
for setting in ("option interval '600'", "option name 'Windows 10'",
                "option username ''", "option password ''", "option enabled '0'"):
    assert setting in text, setting
for service in ('S95srun-autologin', 'S99homebox'):
    assert (root / 'etc/rc.d' / service).is_symlink(), service
assert (root / 'etc/rc.d/S96appfilter').is_symlink(), 'OAF management backend not enabled'
assert list((root / 'lib/modules').rglob('oaf.ko*')), 'OAF module missing'
assert (root / 'etc/fwxd/feature.bin').is_file()
assert (root / 'usr/lib/lua/luci/controller/oaf.lua').is_file()
assert "option tcp_rst '0'" in (root / 'etc/config/fwx').read_text()

lua = root / 'usr/lib/lua/luci'
controller = (lua / 'controller/dockerman.lua').read_text()
assert '"admin", "docker"' in controller
assert 'path = "/" .. options.version .. path' in (lua / 'docker.lua').read_text()
assert not (root / 'usr/share/luci/menu.d/luci-app-dockerman.json').exists()
docker_config = (root / 'etc/config/dockerd').read_text()
assert "option firewall_backend 'nftables'" in docker_config
partition_script = (root / 'etc/uci-defaults/dockerd').read_text()
expected_initializer = Path(__file__).resolve().parents[2] / 'files/etc/uci-defaults/dockerd'
assert partition_script == expected_initializer.read_text(), 'Stale disk initializer'


def image_file(path):
    # APK alternatives can use absolute links (flock -> /usr/bin/util-linux-flock).
    # Resolve those inside the firmware, rather than against the build host.
    for _ in range(16):
        if not path.is_symlink():
            return path.is_file()
        destination = Path(os.readlink(path))
        path = (root / destination.relative_to('/') if destination.is_absolute()
                else path.parent / destination)
    return False


for program in ('sgdisk', 'partprobe', 'lsblk', 'mkfs.ext4', 'blkid',
                'block', 'flock', 'mkswap', 'swapon'):
    assert any(image_file(root / folder / program)
               for folder in ('bin', 'sbin', 'usr/bin', 'usr/sbin')), program
docker_helper = (root / 'etc/init.d/dockerman').read_text()
assert 'NFT_TABLE="dockerman"' in docker_helper
assert 'iptables -' not in docker_helper, 'Old iptables ACL or destructive cleanup retained'
assert '$($_DOCKERD enabled)' not in docker_helper, 'Manual start would skip access control'
assert '/etc/init.d/dockerd enabled && /etc/init.d/dockerd restart &' in (
    root / 'etc/uci-defaults/luci-app-dockerman').read_text()
assert packages['docker'].split('-r')[0] == packages['dockerd'].split('-r')[0]
tailscale = json.loads((root / 'usr/share/luci/menu.d/luci-app-tailscale.json').read_text())
assert 'admin/vpn/tailscale' in tailscale, tailscale
assert 'admin/services/tailscale' not in tailscale
assert 'Build by LaiQE' in (root / 'www/luci-static/resources/view/status/include/10_system.js').read_text()
argon = root / 'usr/share/ucode/luci/template/themes/argon'
for filename in ('footer.ut', 'footer_login.ut'):
    footer = (argon / filename).read_text()
    assert 'Build by LaiQE' in footer, filename
    assert 'version.disturl' not in footer, filename
    assert 'version.luciversion' not in footer, filename
assert (root / 'usr/share/argon/config-integrated').is_file()
assert 'luci-app-argon-config' not in packages, 'Legacy Argon settings package was pulled back in'
assert packages['luci-i18n-argon-config-zh-cn'] == packages['luci-theme-argon'], 'Stale Argon translation package'
generator = (root / 'lib/wifi/mac80211.uc').read_text()
assert "set ${si}.disabled='0'" in generator
assert (root / 'etc/modules.d/ath11k').read_text().split() == [
    'ath11k', 'nss_offload=1', 'frame_mode=2']

print(f'Firmware checks passed: {len(packages)} packages, Arthur only, SHA-256, '
      'NSS 11.4 managers, requested removals, nftables Lua Docker, integrated Argon, '
      'VPN menu, restored tools, offline SRun defaults, built-in OAF and Wi-Fi NSS policy')
for path in images:
    print(f'{path.name}: {path.stat().st_size} bytes')
