# 修改默认IP & 固件名称 & 编译署名
sed -i 's/192.168.1.1/192.168.233.1/g' package/base-files/files/bin/config_generate
sed -i "s/hostname='.*'/hostname='Arthur'/g" package/base-files/files/bin/config_generate
sed -i "s/(\(luciversion || ''\))/(\1) + (' \/ Build by LaiQE')/g" feeds/luci/modules/luci-mod-status/htdocs/luci-static/resources/view/status/include/10_system.js

# 更改默认 Shell 为 zsh
sed -i 's/\/bin\/ash/\/usr\/bin\/zsh/g' package/base-files/files/etc/passwd

# TTYD 免登录
sed -i 's|/bin/login|/bin/login -f root|g' feeds/packages/utils/ttyd/files/ttyd.config

# 修正使用ccache编译vlmcsd的问题
mkdir -p feeds/packages/net/vlmcsd/patches
cp -f $GITHUB_WORKSPACE/patches/fix_vlmcsd_compile_with_ccache.patch feeds/packages/net/vlmcsd/patches

# 移除要替换的包
# rm -rf feeds/packages/net/open-app-filter
# rm -rf feeds/luci/applications/luci-app-appfilter
rm -rf feeds/packages/net/adguardhome
rm -rf feeds/packages/net/openlist
rm -rf feeds/luci/applications/luci-app-openlist
rm -rf feeds/packages/utils/mqttled

# Git稀疏克隆，只克隆指定目录到本地
function git_sparse_clone() {
  branch="$1" repourl="$2" && shift 2
  git clone --depth=1 -b $branch --single-branch --filter=blob:none --sparse $repourl
  repodir=$(echo $repourl | awk -F '/' '{print $(NF)}')
  cd $repodir && git sparse-checkout set $@
  mv -f $@ ../package
  cd .. && rm -rf $repodir
}

# Go & OpenList & AdGuardHome & AriaNg & WolPlus & Lucky & OpenAppFilter & 集客无线AC控制器 & 雅典娜LED控制
# git clone --depth=1 https://github.com/sbwml/luci-app-openlist package/openlist
git_sparse_clone master https://github.com/kenzok8/openwrt-packages adguardhome luci-app-adguardhome
git_sparse_clone main https://github.com/VIKINGYFY/packages luci-app-wolplus
# git clone --depth=1 https://github.com/gdy666/luci-app-lucky package/luci-app-lucky
git clone --depth=1 https://github.com/destan19/OpenAppFilter.git package/OpenAppFilter
# git clone --depth=1 https://github.com/lwb1978/openwrt-gecoosac package/openwrt-gecoosac
# git clone --depth=1 https://github.com/NONGFAH/luci-app-athena-led package/luci-app-athena-led
# chmod +x package/luci-app-athena-led/root/etc/init.d/athena_led package/luci-app-athena-led/root/usr/sbin/athena-led


# tailscale
git clone --depth=1 http://github.com/asvow/luci-app-tailscale package/luci-app-tailscale
sed -i '/\/etc\/init\.d\/tailscale/d;/\/etc\/config\/tailscale/d;' feeds/packages/net/tailscale/Makefile

# 多服务器的frpc
git clone --depth=1 http://github.com/justice2001/luci-app-multi-frpc package/luci-app-multi-frpc

# 在线用户
git_sparse_clone main http://github.com/haiibo/packages luci-app-onliner
# sed -i '$i uci set nlbwmon.@nlbwmon[0].refresh_interval=2s' package/emortal/default-settings/files/99-default-settings-chinese
# sed -i '$i uci commit nlbwmon' package/emortal/default-settings/files/99-default-settings-chinese
sed -i '$i uci set nlbwmon.@nlbwmon[0].refresh_interval=2s' package/emortal/default-settings/files/99-default-settings
sed -i '$i uci commit nlbwmon' package/emortal/default-settings/files/99-default-settings
chmod 755 package/luci-app-onliner/root/usr/share/onliner/setnlbw.sh

# 配置zsh提示符, 不然会乱码
sed -i '$i echo '\''PROMPT="%F{green}%n@%m%f:%F{blue}%~%f$ "'\'' >> /etc/zsh/zprofile' package/emortal/default-settings/files/99-default-settings
# 修复vim找不到defaults.vim的问题
sed -i '$i cp -n /usr/share/vim/vimrc /usr/share/vim/defaults.vim' package/emortal/default-settings/files/99-default-settings

# homebox
sed -i '$i src-git custom_app https://github.com/jjm2473/openwrt-apps.git' feeds.conf.default


./scripts/feeds update -a
./scripts/feeds install -a
