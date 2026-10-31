#!/usr/bin/env python3
"""Keep Arthur's startup policy and APK compatibility with the nftables fork."""
from pathlib import Path


# The imported generic script misidentifies mmcblk0boot1 as the new partition.
# Install the Arthur-specific initializer as part of the dockerd package.
initializer = Path(__file__).resolve().parent.parent / 'files/etc/uci-defaults/dockerd'
Path('feeds/packages/utils/dockerd/files/dockerd.uci-defaults').write_bytes(
    initializer.read_bytes())


def replace_once(filename, old, new):
    path = Path(filename)
    text = path.read_text()
    assert text.count(old) == 1, f'Unexpected Docker source layout: {filename}'
    path.write_text(text.replace(old, new))


replace_once('package/luci-app-dockerman/Makefile',
             'PKG_VERSION:=v0.5.26', 'PKG_VERSION:=0.5.26')

cli_recipe = Path('feeds/packages/utils/docker/Makefile')
text = cli_recipe.read_text()
old_helper = '$(CURDIR)/../dockerd/git-short-commit.sh'
new_helper = '$(CURDIR)/git-short-commit.sh'
assert old_helper in text or new_helper in text, 'Unexpected Docker CLI commit helper'
cli_recipe.write_text(text.replace(old_helper, new_helper))

# Manual start must initialize fw4 too, since Docker is disabled at first boot.
daemon = 'feeds/packages/utils/dockerd/files/dockerd.init'
replace_once(daemon, '\tuciadd\n\trc_procd start_service\n',
             '\trc_procd start_service\n')
replace_once(daemon, '\tprocess_config\n\n\tprocd_open_instance\n',
             '\t/usr/libexec/arthur-docker-mount --docker || return 1\n'
             '\tuciadd\n\tprocess_config\n\n\tprocd_open_instance\n')

helper = Path('package/luci-app-dockerman/root/etc/init.d/dockerman')
text = helper.read_text()
start = text.index('cleanup_legacy_rules(){\n')
end = text.index('\ndelete_dockerman_table(){', start)
text = text[:start] + text[end:]
assert text.count('\tcleanup_legacy_rules\n') == 1
text = text.replace('\tcleanup_legacy_rules\n', '')
# Apply access control to a manually started daemon even with autostart off.
old = '[ -x "$_DOCKERD" ] && $($_DOCKERD enabled) || return 0'
assert text.count(old) == 1
text = text.replace(old, '[ -x "$_DOCKERD" ] || return 0')
helper.write_text(text)

replace_once('package/luci-app-dockerman/root/etc/uci-defaults/luci-app-dockerman',
             '/etc/init.d/dockerd restart &\n',
             '/etc/init.d/dockerd enabled && /etc/init.d/dockerd restart &\n')
replace_once('feeds/luci/collections/luci-lib-docker/luasrc/docker.lua',
             '\theader = (http_method or "GET")',
             '\tpath = "/" .. options.version .. path\n\theader = (http_method or "GET")')
