# LibWrt 亚瑟固件

京东云 **亚瑟 RE-SS-01** 编译配置，`qualcommax/ipq60xx`、512MiB RAM。
固件使用 [LiBwrt/LibWrt](https://github.com/LiBwrt/LibWrt) 的 `25.12-nss` 分支，
编译流程同步 [laipeng668/openwrt-ci-roc](https://github.com/laipeng668/openwrt-ci-roc)。
仅定制亚瑟；其他机型配置和通用工具保持上游一致。

- LAN：**192.168.233.1/24**，DHCP 地址池 `.100–.249`；主机名 `Arthur`。
- IPv6 ULA 首次启动随机生成并保留，手动设置的前缀不覆盖。
- Linux 6.12，**NSS 固件 11.4.0.5 Release 6**，开启 Wi-Fi/Mesh 及上游可用 NSS 管理模块。
- 保留 **Zsh、ttyd 的 root 免登录、BusyBox lsusb、Build by LaiQE 署名**及原有工具。
- 署名显示在系统概览、Argon 登录页及主题页脚；页脚显示 LuCI 分支名（省略 branch/修订号）、Argon 版本及署名。
- 路由器管理员和 SRun 不预置用户密码；AdGuard Home 保留其来源默认设置。
- Docker 在全新刷机或恢复出厂后默认关闭，可在 Dockerman 中手动启动并启用自启；保留升级时已有的明确自启设置。
- 编译优化和 nlbwmon 刷新策略跟随上游；不再强制 O3 或 2 秒刷新。

## 内置功能

| 功能 | 内容 |
| --- | --- |
| 容器与磁盘 | Docker、Compose、Lua Dockerman（独立 Docker 一级菜单）、diskman、fdisk/cfdisk、gdisk/sgdisk、e2fsprogs/tune2fs/resize2fs、fstrim、mmc-utils、USB 3.0/UAS |
| 代理 | PassWall、Xray、Sing-box、Hysteria、Geoview；TUIC、Hysteria2、VLESS/Reality 等；Xray Plugin 和 MWAN3 只生成可选安装包 |
| DNS 与动态域名 | 完整 Lua AdGuard Home 界面和当前 feeds 核心、DDNS-Go；已按要求移除旧 DDNS 和 vlmcsd/KMS |
| VPN 与穿透 | WireGuard、ZeroTier、L2TPv2/NSS、FRP 多服务器、asvow 的 Tailscale 界面（上游已位于 VPN 菜单） |
| 系统与网络 | Argon 主题及配置、WOL+、UPnP、ARP 绑定、在线用户、Homebox、CPU 调频、ttyd、自动重启、IRQ balance、SFTP、zram |
| 工具 | Git/Git HTTP/Git LFS、Vim、Zsh、Screen、dmesg、net-tools、亚洲时区数据 |
| 校园网 | 离线内置 SRun 程序、LuCI 和 procd；默认关闭，账号密码留空；[使用参数](docs/SRUN.md) |

## 组件来源

- **Argon**：使用 [jerrykuku/luci-theme-argon](https://github.com/jerrykuku/luci-theme-argon) 最新 master，当前为 3.1.0。原作者已包含新的弹窗及稳定版兼容修复；3.x 自带「系统 → Argon 配置」，不再同时编译会产生文件冲突的旧独立配置插件。没有加入自行编写的主题样式补丁。
- **AdGuard Home**：恢复原来的 [kenzok8/openwrt-packages](https://github.com/kenzok8/openwrt-packages) 完整界面，默认 UCI、YAML 和配置模板保持来源原样。仅保留 LuCI/APK/fw4 必要兼容修改，以及避免两个同名核心服务重复启动的处理；默认配置为 `/etc/config/AdGuardHome`、`/etc/AdGuardHome.yaml`，管理端口 3000。
- **Tailscale**：恢复 [asvow/luci-app-tailscale](https://github.com/asvow/luci-app-tailscale) 界面，核心仍更新。按原项目方式由界面包提供 init/UCI，避免与核心包重复安装相同文件。
- **Docker/Dockerman**：从 [ysuolmai/openwrt-packages](https://github.com/ysuolmai/openwrt-packages) 的 main 分支引入原生 nftables 引擎配方及 Lua 界面，保留 Docker 一级菜单；配套库来自 ImmortalWrt openwrt-24.10，沿用 API v1.40 修正。Docker/CLI 29.6.2、containerd 2.2.6 与当前 runc/tini 配套。全新安装默认关闭，手动启动也初始化 fw4 和访问控制。自动分区改用下述亚瑟初始化脚本；去掉清空旧用户规则的迁移逻辑。原生 nftables 后端仍属 Docker 实验功能，不用于 Swarm。
- **WOL+**：使用支持现代 LuCI 的 sakura-builder1 维护版本。WireGuard 使用最新上游的原生协议与状态页。
- **Homebox**：使用 jjm2473/openwrt-apps 当前上游配方、服务和默认配置；只补构建所需的 Go 工具路径，不再替换后端或自行重写运行服务。
- **PassWall**：来自 Openwrt-Passwall 维护仓库；Sing-box 显式启用 QUIC/UTLS/gRPC/WireGuard，提供 TUIC/Hysteria2 支持，另内置独立 Hysteria2 核心。

Go、Tailscale、FRP、Docker 配套组件及 Compose 的版本覆盖和官方源码 SHA-256 记录在
`configs/package-updates.json`。实际主仓库、feeds 和第三方提交随本地产物导出。

## Wi-Fi 与 NSS

默认 Wi-Fi 的启用状态跟随 LibWrt，不额外强制关闭。
[LibWrt 维护者说明](https://github.com/LiBwrt/LibWrt/issues/167)要求 Wi-Fi 设置密码；
测试 NSS 时先通过有线配置 **WPA2-PSK/CCMP**，2.4GHz 20MHz，5GHz 80MHz/20dBm。
使用 11.4 是为兼容 Mesh NSS；驱动及客户端由上游配方自动选择配套版本。
上游标为 BROKEN 或不适用于亚瑟的 NSS 模块不强行启用。

用户已烧录第一版 LibWrt 镜像并反馈基本使用无大问题；各加速路径、吞吐和长期稳定性
仍以真机统计为准。NSS 不会自动加速 PassWall、Tailscale 等程序的用户态加密。
[NSS 配置限制与来源](docs/NSS-CONSTRAINTS.md) · [Wi-Fi 排查](docs/WIFI-NSS.md) · [L2TP 源码检查](docs/NSS-L2TP.md)

## 构建

日常在 GitHub Actions 选择 **Arthur-LibWrt → Run workflow**，成功后发布到
`Arthur` Release。保留 Actions，关闭批量每周定时触发。本次使用本机 Podman 编译。

Windows PowerShell，在仓库根目录执行：

```powershell
.\scripts\Build-Local.ps1 -Stage Prepare -Detach
# Prepare 完成后
.\scripts\Build-Local.ps1 -Stage Build -Jobs 8 -Detach
.\scripts\Build-Local.ps1 -Stage Status
.\scripts\Build-Local.ps1 -Stage Logs
# Build 及校验最终退出码为 0 后导出
.\scripts\Build-Local.ps1 -Stage Export
```

默认容器 `openwrt-arthur-libwrt-builder`，卷 `openwrt-arthur-libwrt-work`。
首次创建容器可加 `-RebuildImage` 重新拉取基础系统并跳过镜像层缓存；它不会清空已有卷。
源码、工具链、下载和缓存位于 Linux 数据卷中，以普通用户编译，容器使用 `--init`。
每次复制完整输入快照，包含文件删除；同一源码基线可以续编。
本地和 Actions 都跟踪配置分支；若主仓库已更新，本地会要求使用新容器/卷，避免混用旧工具链。

`artifacts/` 为已忽略的导出目录，包含固件、校验文件、manifest、实际配置、diffconfig、
源码提交和日志。构建会核对显式配置、首次启动 LAN/DHCP、磁盘初始化保护逻辑，以及必要包和正确版本的初始化脚本是否实际装入。
按用户要求不再进行 AdGuard Home 专项或本地主题界面测试。

2026-10-25 07:56 的 Podman 构建及上述校验全部通过，最终退出码 0；
仅生成亚瑟 factory/sysupgrade 镜像，内置 480 个包。导出后的镜像 SHA-256 已复核。
原生 nftables Docker、Lua 界面、默认关闭、亚瑟自动分区/挂载与 swap 修复、ULA 和页脚调整均已编入。
编译出的引擎在隔离 chroot 中通过配置校验；容器实际转发尚待验证。
已从最终 sysupgrade 的 squashfs 中逐字核对分区脚本；本轮新镜像待用户烧录验证。

## 磁盘与维护

`files/etc/uci-defaults/dockerd` 仅处理亚瑟的 `/dev/mmcblk0`，构建时替换 Docker 包内的初始化脚本：

- 优先复用已有 `storage` 分区；没有该标签时，复用已有第 27 分区。分区必须**大于 1GiB**且为 ext4，挂载到 `/opt/docker`，按 UUID 写入 fstab；不重新格式化已有分区。
- 没有数据分区时，先备份并用 `sgdisk -e` 修复 GPT 尾部位置，再使用实际剩余扇区创建 `storage`。仅格式化本次新建且无文件系统的分区，适应 64GB/128GB 容量。
- 保留有效的 swap；将标签为 `swap` 的空白分区或空 ext4 占位分区初始化为交换空间。有文件时拒绝格式化。eMMC swap 优先级 10，保留更高优先级的 zram。
- 已有 Docker 数据阻挡挂载时停止并记录日志，须先迁移数据；失败返回非零，保留初始化脚本供重试。磁盘初始化独立于 Docker 自启开关。

当前 64GB 真机已完成创建、挂载、Docker 数据迁移和 swap 修复；未挂载分区的复用、重复执行、fstab 重新启用 swap 均已验证。64GB/128GB 稀疏镜像验证了分区算法，原有 26 个 GPT 条目保持不变；128GB 尚未真机测试。
实机备份保存在本机已忽略的 `.local/arthur-storage-backup/`；仍应在刷机前备份磁盘数据。
隔离逻辑检查：`python3 tests/storage/checks.py`（需要 Bash）。

[AI 交接说明](docs/AI_HANDOFF.md) · [简短调试记录](docs/DEBUG_NOTES.md) · [项目约定](AGENTS.md)

保留项目 MIT 许可证；固件及第三方软件分别遵循各自许可证。
SRun 的 GPL 许可证与对应源码归档保留在本地包目录。
