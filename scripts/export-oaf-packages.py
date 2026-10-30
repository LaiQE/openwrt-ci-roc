#!/usr/bin/env python3
"""Collect matching experimental OAF APKs without adding them to the image."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile


source, root, target = (Path(value).resolve() for value in sys.argv[1:])
apk = source / 'staging_dir/host/bin/apk'
signing_key = source / 'private-key.pem'
assert signing_key.is_file(), 'Missing local APK signing key'
manifest, = target.glob('*.manifest')
installed = dict(line.split(' - ', 1) for line in manifest.read_text().splitlines()
                 if ' - ' in line)
core = {'luci-app-oaf', 'appfilter', 'kmod-oaf'}
assert not core.intersection(installed), 'OAF unexpectedly installed in firmware'
packages = list((source / 'bin/packages').rglob('*.apk'))
packages += list((target / 'packages').glob('*.apk'))
metadata = {}


def info(path):
    if path not in metadata:
        data = subprocess.check_output([str(apk), 'adbdump', '--format=json', str(path)])
        metadata[path] = json.loads(data)['info']
    return metadata[path]


def locate(name):
    matches = [path for path in packages if path.name.startswith(name + '-')
               and info(path)['name'] == name]
    assert len(matches) == 1, f'Expected one APK for {name}, got {matches}'
    return matches[0]


pending = sorted(core)
if any(path.name.startswith('luci-i18n-oaf-zh-cn-') for path in packages):
    pending.append('luci-i18n-oaf-zh-cn')
selected = {}
architecture = None
while pending:
    name = pending.pop()
    if name in selected or name in installed:
        continue
    path = locate(name)
    package = info(path)
    if package['arch'] not in ('all', 'noarch'):
        if architecture is None:
            architecture = package['arch']
        assert package['arch'] == architecture, package
    selected[name] = path
    for dependency in package.get('depends', []):
        if dependency.startswith('!'):
            continue
        if dependency.startswith('kernel='):
            assert dependency == 'kernel=' + installed['kernel'], dependency
        match = re.fullmatch(r'([A-Za-z0-9+_.-]+)([<>=~].*)?', dependency)
        assert match, f'Unhandled APK dependency: {dependency}'
        pending.append(match[1])

assert core.issubset(selected), selected
assert not (root / 'etc/init.d/appfilter').exists(), 'OAF service installed in image'
assert not list((root / 'lib/modules').rglob('oaf.ko*')), 'OAF module installed in image'
archive = target / 'Arthur.OAF-experimental.tar.gz'
instructions = (Path(__file__).resolve().parents[1] / 'docs/OAF-EXPERIMENT.md').read_text()
header = (f'Build architecture: {architecture}\nKernel ABI: {installed["kernel"]}\n'
          'These APKs are not installed in the firmware.\n\n')
with tempfile.TemporaryDirectory(prefix='arthur-oaf-') as temporary:
    bundle = Path(temporary)
    checksums = []
    package_info = {}
    for name, path in sorted(selected.items()):
        exported = bundle / path.name
        exported.write_bytes(path.read_bytes())
        # OpenWrt normally signs repository indexes, not individual APKs.
        # Sign only the exported copies with the key trusted by this firmware.
        # Allow reading the unsigned build output only while signing it;
        # installing the exported APKs still requires normal signature checks.
        subprocess.check_call([str(apk), 'adbsign', '--allow-untrusted',
                               '--sign-key', str(signing_key), str(exported)])
        checksums.append(f'{hashlib.sha256(exported.read_bytes()).hexdigest()}  {path.name}')
        package_info[name] = info(path)
    subprocess.check_call([str(apk), '--keys-dir', str(root / 'etc/apk/keys'),
                           'verify', *(str(path) for path in sorted(bundle.glob('*.apk')))])
    (bundle / 'SHA256SUMS').write_text('\n'.join(checksums) + '\n')
    (bundle / 'packages.json').write_text(json.dumps(package_info, indent=2) + '\n')
    (bundle / 'README.md').write_text(header + instructions)
    with tarfile.open(archive, 'w:gz') as output:
        for path in sorted(bundle.iterdir()):
            output.add(path, arcname='OAF-experimental/' + path.name)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
checksum_file = target / 'sha256sums'
lines = [line for line in checksum_file.read_text().splitlines()
         if line.split(maxsplit=1)[-1].lstrip('*') != archive.name]
checksum_file.write_text('\n'.join([*lines, f'{digest} *{archive.name}']) + '\n')
print(f'Experimental OAF bundle: {len(selected)} APKs, {architecture}, kernel {installed["kernel"]}')
print('OAF remains absent from firmware; runtime NSS compatibility is unverified.')
