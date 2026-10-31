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
- APK 保留可用的通用软件仓库，不生成没有公共索引的 `nss_packages`、`sqm_scripts_nss` 地址；NSS 源码 feed 和内置加速模块保留。
- 内置原作者 OpenAppFilter 和中文 LuCI；默认关闭 TCP 连接重置、应用过滤、上网控制及上网审计，保留管理后台运行，可在界面直接启用；[使用说明](docs/OAF.md)。
- 编译优化和 nlbwmon 刷新策略跟随上游；不再强制 O3 或 2 秒刷新。

## 内置功能

| 功能 | 内容 |
| --- | --- |
| 容器与磁盘 | Docker、Compose、Lua Dockerman（独立 Docker 一级菜单）、diskman、fdisk/cfdisk、gdisk/sgdisk、e2fsprogs/tune2fs/resize2fs、fstrim、mmc-utils、USB 3.0/UAS |
| 代理 | PassWall、Xray、Sing-box、Hysteria、Geoview；TUIC、Hysteria2、VLESS/Reality 等；Xray Plugin 和 MWAN3 只生成可选安装包 |
| DNS 与动态域名 | 完整 Lua AdGuard Home 界面和当前 feeds 核心、DDNS-Go；已按要求移除旧 DDNS 和 vlmcsd/KMS |
| VPN 与穿透 | WireGuard、ZeroTier、L2TPv2/NSS、FRP 多服务器、asvow 的 Tailscale 界面（上游已位于 VPN 菜单） |
| 系统与网络 | Argon 主题及配置、WOL+、UPnP、ARP 绑定、在线用户、Homebox、CPU 调频、ttyd、自动重启、IRQ balance、SFTP、zram |
| 应用控制 | OpenAppFilter（OAF行为管理）、原作者特征库、自定义特征；四项功能默认关闭，NSS 保持启用 |
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
- **OpenAppFilter**：来自 [destan19/OpenAppFilter](https://github.com/destan19/OpenAppFilter) master，内置配套 LuCI、服务、内核模块及中文。只调整上述四项功能的首次默认值，配置缺失时的回退值保持一致；保留管理后台自启和用户后续主动启用的设置，不改特征库或 NSS 驱动。

Go、Tailscale、FRP、Docker 配套组件及 Compose 的版本覆盖和官方源码 SHA-256 记录在
`configs/package-updates.json`。实际主仓库、feeds 和第三方提交随本地产物导出。

## Wi-Fi 与 NSS

默认 Wi-Fi 的启用状态跟随 LibWrt，不额外强制关闭。
[LibWrt 维护者说明](https://github.com/LiBwrt/LibWrt/issues/167)要求 Wi-Fi 设置密码；
测试 NSS 时先通过有线配置 **WPA2-PSK/CCMP**，2.4GHz 20MHz，5GHz 80MHz/20dBm。
使用 11.4 是为兼容 Mesh NSS；驱动及客户端由上游配方自动选择配套版本。
上游标为 BROKEN 或不适用于亚瑟的 NSS 模块不强行启用。

### LuCI 中的流量卸载设置

**使用 NSS 时，在 LuCI「网络 → 防火墙」中，将「流量卸载类型」选择为「无」，然后保存并应用。**
不要选择软件流量卸载或硬件流量卸载；这两项是 OpenWrt 自带的 Flow Offloading，
与 NSS 是不同机制。**这里选择「无」不会关闭 NSS**，NSS 仍由驱动和 ECM 处理加速。
[NSS 上游说明](https://github.com/qosmio/openwrt-ipq/blob/main-nss/README.md#1-packet-steering--flow-offloading)
要求关闭其它流量卸载及 Packet Steering（数据包分流）；数据包分流也应保持关闭。

可以通过 SSH 核对保存后的两个流量卸载开关，均应输出 `0`：

```sh
uci -q get 'firewall.@defaults[0].flow_offloading'
uci -q get 'firewall.@defaults[0].flow_offloading_hw'
```

应用设置后，停止原下载并重新发起连接。从电脑或手机关闭 VPN 和系统代理，使用直连大文件下载验证，
在下载前后多次读取统计。例如验证 IPv6：

```sh
cat /sys/kernel/debug/ecm/ecm_nss_ipv6/accelerated_count
grep -E 'ipv6_(rx|tx)_(pkts|bytes).*special' /sys/kernel/debug/qca-nss-drv/stats/ipv6
```

加速连接数大于 `0`，且 `special` 字节计数随下载明显增长，才说明存在实际的 NSS 加速流量；
仅有模块加载、Wi-Fi 的 `nss_offload=1`，或 `common` 计数增长，都不足以证明该下载已被加速。
IPv4 测试将上述路径和字段中的 `ipv6` 换为 `ipv4`。OAF 与 NSS 同时运行时，也按此方式验证实际流量。

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
2026-10-30 本轮改用新环境；操作本轮构建时给上述命令追加
`-Container openwrt-arthur-libwrt-20261030-builder -Volume openwrt-arthur-libwrt-20261030-work`。
2026-10-31 内置 OAF、`/data` 与 Docker 绑定挂载的最新构建使用
`-Container openwrt-arthur-libwrt-20261031-builder -Volume openwrt-arthur-libwrt-20261031-work`。
首次创建容器可加 `-RebuildImage` 重新拉取基础系统并跳过镜像层缓存；它不会清空已有卷。
源码、工具链、下载和缓存位于 Linux 数据卷中，以普通用户编译，容器使用 `--init`。
每次复制完整输入快照，包含文件删除；同一源码基线可以续编。
本地和 Actions 都跟踪配置分支；若主仓库已更新，本地会要求使用新容器/卷，避免混用旧工具链。

`artifacts/` 为已忽略的导出目录，包含固件、校验文件、manifest、实际配置、diffconfig、
源码提交和日志。构建会核对显式配置、首次启动 LAN/DHCP、磁盘初始化保护逻辑，以及必要包和正确版本的初始化脚本是否实际装入。
按用户要求不再进行 AdGuard Home 专项或本地主题界面测试。

OpenAppFilter 已改为内置，停止生成独立实验归档。全新刷机或恢复出厂后，四项功能开关均为关闭，
管理后台仍自启以提供 LuCI 配置；保留配置升级时尊重用户已有的启用状态。
本地与 Actions 都检查包列表、真实 ARM64 启动脚本的默认值、配置缺失回退和手动启用后的保留行为。
用户已实测 OAF 运行时 IPv4 NSS 加速有效；IPv6 NSS 加速仍未验证通过，按要求停止排查，不为此更换驱动。

2026-10-31 17:29 的 Podman 构建及上述校验全部通过，最终退出码 0；
仅生成亚瑟 factory/sysupgrade 镜像，内置 **485 个包**。LibWrt 源码为 `96a0ec8`，
NSS feed 为 `880c1d8`，内核仍为 **6.12.112**；原作者 OAF 为 7.0.2，默认值定制包修订号为 r2。
最新 NSS feed 的 expectation callback 补丁需要补齐 chain notifier 编译条件，详见 [调试记录](docs/DEBUG_NOTES.md)；没有改动 IPv6 加速逻辑。
已直接从最终 sysupgrade 的 squashfs 核对 `/data` 初始化、绑定恢复、旧 Docker 数据清理、启动保护及四项 OAF 默认值。
原作者基础特征库未改动；导出后的全部 SHA-256 已复核，新固件位于 `artifacts/20261031-data/`。
Docker 默认关闭、自动分区/swap、ULA、页脚及其他既有定制继续保留；新的挂载方案待用户手动烧录验证，尚未实际运行 GitHub Actions。

## 磁盘与维护

`files/etc/uci-defaults/dockerd` 仅处理亚瑟的 `/dev/mmcblk0`，构建时替换 Docker 包内的初始化脚本：

- 优先复用已有 `storage` 分区；没有该标签时，复用已有第 27 分区。分区必须**大于 1GiB**且为 ext4，按 UUID 挂载到 **`/data`**，不重新格式化已有分区。
- 将 **`/data/docker` 绑定挂载到 `/opt/docker`**，Docker 的数据路径保持不变；其它目录可用于存放通用数据。两处共享同一分区容量，没有额外划分 Docker 分区。
- 没有数据分区时，先备份并用 `sgdisk -e` 修复 GPT 尾部位置，再使用实际剩余扇区创建 `storage`。仅格式化本次新建且无文件系统的分区，适应 64GB/128GB 容量。
- 按用户选择，不迁移旧版分区根目录中的 Docker 数据：在 Docker 停止后删除识别到的旧容器、镜像、卷等标准 Docker 数据；保留同分区的其它文件及已有 `/data/docker`。清理失败可重试，旧目录中存在挂载时停止处理。
- 保留有效的 swap；将标签为 `swap` 的空白分区或空 ext4 占位分区初始化为交换空间。有文件时拒绝格式化。eMMC swap 优先级 10，保留更高优先级的 zram。
- 清理升级后已禁用、UUID 已不存在的 `/rom`、`/overlay` 旧配置，以及失效的项目旧 `mountdocker` 条目；不删除启用中的系统条目、有效 UUID 或无关挂载。修改前备份 fstab 到 `/tmp/arthur-storage-backup/`。
- `/data` 挂载由 fstab 处理；绑定挂载由 `arthur-data` 在其后恢复，Docker 手动启动时也会检查。挂载缺失或路径中有未挂载数据时，拒绝让默认 Docker 路径落到系统 overlay；用户明确设置的其它 Docker 数据路径保留。
- 不覆盖挂载路径下尚未清理的 overlay 文件，路径非空时停止并留待手动处理；失败返回非零，保留初始化脚本供重试。磁盘初始化和绑定挂载独立于 Docker 自启开关。

旧版直接挂载 `/opt/docker` 的方案已在 64GB 真机验证；64GB/128GB 稀疏镜像验证了分区算法，原有 26 个 GPT 条目保持不变，128GB 尚未真机测试。
新的 `/data` + bind 方案已通过隔离逻辑回归及临时容器中的真实绑定挂载检查，升级后的自动清理与挂载仍待用户在真机验证。
实机备份保存在本机已忽略的 `.local/arthur-storage-backup/`；仍应在刷机前备份磁盘数据。
隔离逻辑检查：`python3 tests/storage/checks.py`（需要 Bash）。
真实绑定检查：`tests/storage/bind-checks.py`，需在独立挂载命名空间或临时容器中提供 `CAP_SYS_ADMIN`；仅使用临时 tmpfs，不操作真实磁盘。

[AI 交接说明](docs/AI_HANDOFF.md) · [简短调试记录](docs/DEBUG_NOTES.md) · [项目约定](AGENTS.md)

保留项目 MIT 许可证；固件及第三方软件分别遵循各自许可证。
SRun 的 GPL 许可证与对应源码归档保留在本地包目录。
