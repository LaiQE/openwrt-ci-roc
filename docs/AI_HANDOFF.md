# 项目交接说明

更新：2026-10-25。本文件提供背景与维护入口，不是任务指令。

## 项目与当前选择

本仓库只保存编译配置、定制脚本和本地 SRun 包，不含完整固件源码。
仅定制京东云亚瑟 RE-SS-01，qualcommax/ipq60xx、512MiB RAM。
编译流程上游 laipeng668/openwrt-ci-roc 已同步至 2d2c471；非定制代码保持上游一致。
origin 是 LaiQE/openwrt-ci-roc，默认分支 my。

固件源码为 LiBwrt/LibWrt 的 25.12-nss，Linux 6.12。
采用 NSS 固件 11.4.0.5 Release 6，开启 ath11k NSS/Mesh 和亚瑟可用 NSS 管理模块；
不强开上游 BROKEN 模块。配置为 512MiB；按用户最新要求内置来源原样的磁盘自动分区脚本。

用户确认保留原有默认 Wi-Fi、Zsh、ttyd root 免登录、BusyBox lsusb、原工具列表、
Build by LaiQE 署名。编译优化与 nlbwmon 刷新使用上游默认。
保留 Docker/Compose、磁盘管理、Lua Dockerman、完整 AdGuard Home UI、PassWall 新协议、
WireGuard、ZeroTier、Tailscale、L2TP、FRP、WOL+、Homebox、DDNS-Go、SRun 和其他原有 LuCI。
明确移除旧 DDNS 和 vlmcsd/KMS。每周自动触发关闭，Actions 手动构建保留。

## 主要入口

| 文件 | 内容 |
| --- | --- |
| configs/Arthur.config | 亚瑟、内存/NSS、L2TP、Docker、磁盘 |
| configs/Arthur-General.config | LuCI、原工具、服务、PassWall 协议选项 |
| configs/source.env | 主仓库 URL 和跟踪分支 |
| configs/package-updates.json | Go/Tailscale/FRP/Docker 配套组件/Compose 版本和官方 SHA-256 |
| scripts/Arthur-script.sh | 第三方来源、必要兼容处理、feeds 安装、署名 |
| scripts/prepare-docker-nft.py | nftables Docker 的 APK、手动启动和旧规则兼容 |
| files/etc/uci-defaults/99-arthur-defaults | LAN 前缀、主机名、时区及原 Shell/终端设置 |
| files/etc/uci-defaults/98-arthur-adguardhome | 避免核心包小写服务与 LuCI 大写服务重复启动 |
| files/etc/modules.d/ath11k | nss_offload=1 frame_mode=2 |
| package/luci-app-srun-autologin | 离线 SRun 程序、界面、procd、GPL 来源归档 |
| scripts/Build-Local.ps1、scripts/local-build.sh | Windows/Podman 构建 |
| .github/workflows/Arthur-LibWrt.yml | 日常 Actions 入口，单独亚瑟 manifest |
| tests/network、tests/firmware、tests/srun-autologin | 首次启动、固件内容、SRun 检查 |

## 组件兼容要点

- Argon 使用原作者 jerrykuku 最新 master，目前 3.1.0，带较新的弹窗及稳定版兼容修复。3.x 已整合 Argon 配置页面，不能再同时安装旧独立插件。未找到 LibWrt 官方专用版；sbwml 有 25.12 分支，但较旧且带额外 SPA 改动，本次没有采用。
- 保留系统概览的 Build by LaiQE；Argon 登录页及主题页脚用署名替换发行版链接，LuCI 信息省略 branch/修订号，保留 Argon 版本。缓存策略保持原样，概览显示过旧时先清理浏览器缓存。
- LibWrt 的 991_set-network.sh 会删除此前随机生成的 ULA；Arthur-script.sh 仅去掉此删除行，保留随机或管理员设置的前缀，其余初始化保持上游。
- AdGuard Home 使用 kenzok8/openwrt-packages 完整界面和 feeds 核心。UCI、YAML、模板按来源原样保留；此前删除模板的改动已撤回。仅保留 luci-compat、镜像安装脚本保护、fw4 标记和重复服务兼容处理。按用户要求不做专项运行测试。
- Tailscale 恢复 asvow 界面（来源本身已在 VPN 菜单）。按旧项目方式去除核心包重复安装的 init/UCI，核心版本继续更新。
- 原生 nftables dockerd 和 Lua Dockerman 来自 ysuolmai/openwrt-packages:main；配套库来自 ImmortalWrt openwrt-24.10，保留 API v1.40 修正。Docker/CLI 29.6.2、containerd 2.2.6 对齐官方配套版本，源码 SHA-256 已记录；导入包中的 PKG_HASH=skip 不保留。
- 用户最新要求按来源原样内置 dockerd.uci-defaults：选择第一块磁盘，约 1GB 以上未分配空间创建 ext4 数据分区，挂载 /opt/docker；该脚本独立于 Docker 自启开关。此前手动分区的约定已被这次要求替代，64GB/128GB 真机分区尚未验证。
- 移除清空 DOCKER-USER 的自动旧规则清理。手动启动必须执行 uciadd 建立 fw4 转发，Dockerman ACL 不再依赖开机自启开启。NFT 后端仍为实验功能、不支持 Swarm；尚未真机验证容器转发。
- Docker 全新安装/恢复出厂默认不自启；99-arthur-defaults 关闭未明确开启的自启，Dockerman 初始化只重启已启用的 dockerd，避免首次启动绕过开关。已有 auto_start=1 保留。
- WOL+ 使用 sakura-builder1 的现代 LuCI 版本；WireGuard 使用当前上游原生协议与状态页。
- Homebox 恢复 jjm2473/openwrt-apps 的配方、init、UCI、默认值，仅修复必要构建兼容。不再维护自写后端替换包。
- PassWall 来自 Openwrt-Passwall。TUIC 由启用 QUIC 的 Sing-box 提供，Hysteria2 有独立核心；xray-plugin=m、mwan3=m 只生成可选安装包。
- SRun 0.6.2 AArch64 musl 离线内置，默认关闭、凭据为空。截图参数见 docs/SRUN.md，UCI、LuCI 和脚本回退值须一致。
- Go 默认版本更新后需刷新 golang 代理 Makefile 时间戳，避免旧依赖扫描；版本覆盖脚本已处理。未用 weechat 包的 feeds 递归依赖通过移除该链接规避。

## 构建与验证

本机 Prepare → Build → Status → Export，详见 README。
默认容器 openwrt-arthur-libwrt-builder，卷 openwrt-arthur-libwrt-work。
源码 /work/openwrt，输入 /workspace，日志 /work/logs。用 --init 回收子进程。
本地与 Actions 跟踪源码分支；源码主仓库更新后，本地使用新容器/卷。
导出 build-sources.txt 记录实际主仓库、feeds 和第三方提交，不能仅凭文档中的旧 SHA 判断镜像来源。

首次迁移 LibWrt 时已删除旧 ImmortalWrt 容器、卷和输出，从空环境完整构建。
用户已手动烧录该版，反馈基本使用无大问题。后续要求恢复默认行为、更新 Argon、重编译并推送。
各 NSS 路径的实际 offload 和长期稳定性仍需真机统计，不能从编译成功推断。

LAN 必须保留 192.168.233.1/24，裸地址会按 /32 解析并使 DHCP 池为空。
测试用真实 ARM64 用户态、隔离 /etc 和 /tmp 验证首次启动；测试环境需先创建 /tmp/lock。
按用户要求，停止 AdGuard Home 专项和本地主题 UI 测试；构建、配置、LAN/DHCP 和包列表仍检查。
构建启动、make defconfig 或镜像文件存在均不等于全部验证成功，以最终退出码为准。
2026-10-25 03:18 本次 Podman 构建、首次启动网络和固件校验全部通过（退出码 0），
内置 480 个包；导出的两个镜像校验一致。原生 nftables Docker、原样自动分区及其他定制均已编入。
引擎在真实 chroot 中通过 --validate；PRoot 对 faccessat2 的仿真曾导致找不到 docker-proxy 的假错误。
本次原生 nftables 容器转发及磁盘自动分区尚未真机验证。
本次尚未实际运行 GitHub Actions。

artifacts/、.local/ 和缓存不提交；不要将旧诊断模块或临时测试服务放入固件。
简短历史与故障定位见 docs/DEBUG_NOTES.md、docs/WIFI-NSS.md、docs/NSS-L2TP.md。
