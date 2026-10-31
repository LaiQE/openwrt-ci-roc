#!/usr/bin/env python3
"""Default OAF features off while retaining its upstream LuCI backend."""
from pathlib import Path
import sys


package = Path(sys.argv[1]) / 'open-app-filter'
replacements = (
    ("\toption tcp_rst '1'", "\toption tcp_rst '0'"),
    ('config appfilter appfilter\n\toption enable 1',
     'config appfilter appfilter\n\toption enable 0'),
    ('config macfilter macfilter\n\toption enable 1',
     'config macfilter macfilter\n\toption enable 0'),
    ("config record 'record'\n\toption enable '1'",
     "config record 'record'\n\toption enable '0'"),
)
for name in ('fwx.config', 'appfilter.init'):
    path = package / 'files' / name
    text = path.read_text()
    for before, after in replacements:
        assert text.count(before) + text.count(after) == 1, (name, before)
        text = text.replace(before, after)
    path.write_text(text)

# Ship the declared conffile so defaults are visible before the daemon starts.
# The original init script still creates missing configs and preserves existing
# configs, including a user's later opt-in. Do not change service autostart.
path = package / 'Makefile'
text = path.read_text()
assert '/etc/config/fwx\n' in text, 'Upstream dropped the fwx conffile'
install = '\t$(INSTALL_DATA) ./files/fwx.config $(1)/etc/config/fwx\n'
if install not in text:
    anchor = '\t$(INSTALL_DATA) ./files/custom_feature.cfg $(1)/etc/fwxd/custom_feature.cfg\n'
    assert text.count(anchor) == 1, 'Unexpected OAF install recipe'
    text = text.replace(anchor, anchor + install)
if 'PKG_RELEASE:=1\n' in text:
    text = text.replace('PKG_RELEASE:=1\n', 'PKG_RELEASE:=2\n')
else:
    assert 'PKG_RELEASE:=2\n' in text, 'Review the changed OAF release'
path.write_text(text)
print('OAF defaults: TCP RST/filter/access control/auditing off; LuCI backend retained')
