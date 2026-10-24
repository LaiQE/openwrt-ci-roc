# 项目交接说明（供后续 AI 快速了解）

更新日期：2026-10-24。本文件是项目背景和操作说明。

## 项目用途与已确认需求

本仓库存放 ImmortalWrt 的编译配置和定制包，不包含完整固件源码。
自定义构建目标是京东云亚瑟 RE-SS-01，平台 `qualcommax/ipq60xx`，512MiB RAM。
上游通用代码、SDK 工具及其他机型配置保持同步；仅定制部分按本项目需求调整。

用户希望软件包尽量新，并保留原先启用的 LuCI 功能。Docker、Compose、磁盘管理、
AdGuard Home、PassWall、WireGuard、ZeroTier、Tailscale、L2TP、DDNS、FRP 多服务器、
WOL+、在线用户、内网测速和系统管理功能均在保留范围内；新增 DDNS-Go 和 SRun。
主要精简对象是重复依赖、失效选项、无关源码下载及 Git/Vim/Zsh 等开发工具。

管理地址为 `192.168.233.1`，主机名 `Arthur`，时区 `Asia/Shanghai`。
64GB/128GB eMMC 由用户手动分区：没有引入自动格式化或修改 GPT 的脚本。

## 主要文件

| 路径 | 内容 |
| --- | --- |
| `configs/Arthur.config` | 单一机型、NSS/L2TP、Docker 和磁盘配置 |
| `configs/Arthur-General.config` | 通用 LuCI、网络服务与 PassWall 协议选项 |
| `configs/Extras.config` | 开发工具参考选项，默认不加载；需要时复制到正式配置 |
| `configs/source.env` | 固件主仓库 URL、分支和固定提交 |
| `configs/package-updates.json` | Go、FRP、Tailscale、Compose 补丁版本和 SHA-256 |
| `scripts/Arthur-script.sh` | 引入第三方包、移植新配方、兼容性修补和 feeds 安装 |
| `scripts/Build-Local.ps1` | Windows 本机 Podman 构建入口 |
| `scripts/local-build.sh` | 容器内准备、配置、下载、编译和产物导出 |
| `scripts/verify-config.py` | 检查所有显式配置均被 Kconfig 接受，且只选择亚瑟 |
| `files/etc/uci-defaults/99-arthur-defaults` | 首次启动时设置 LAN 地址、主机名和时区 |
| `package/luci-app-srun-autologin/` | 本地 SRun 程序、LuCI 页面、配置、procd 服务与来源记录 |
| `package/homebox/` | 官方 Homebox 0.1.3 ARM64 musl 发布包的配方及 procd 服务 |
| `tests/srun-autologin/` | SRun 静态检查及模拟网络环境的运行测试 |
| `tests/network/first-boot-checks.py` | 使用实际 ARM64 用户态验证网络初始化、DHCP 地址池及升级保留网段；需 QEMU/proot |
| `docs/SRUN.md` | SRun 默认值及使用方法 |
| `docs/NSS-L2TP.md` | 旧版 NSS/L2TP 崩溃的源码核对结果及真机复现资料 |

上游 `General.config`、`Roc-script.sh`、其他机型配置及工作流保持原样。
通用 `Build-OpenWrt.yml` 增加可选定制输入（配置、脚本、LAN 地址）及亚瑟配置/首次启动验证；
其默认值仍与上游一致，独立 `Arthur-ImmortalWrt.yml` 传入本项目定制文件。
上游批量入口保留，但定时触发在本仓库关闭，避免自动构建其他机型。

## 源码与关键选择

编译项目上游是 `laipeng668/openwrt-ci-roc`，已合并上游提交 `2d2c471`。
固件源码使用 `laipeng668/immortalwrt` 的 `openwrt-25.12`，当前基线提交为
`0a98e096208584bf90982f59f6d5a43f89443276`；采用稳定内核 6.12、NSS 12.5。
旧配置中的 `master` 分支已失效。

PassWall 来自 `Openwrt-Passwall` 维护仓库，选择 Xray、Sing-box、Hysteria 和 Geoview。
TUIC 由 Sing-box 提供，`SING_BOX_BUILD_QUIC` 显式启用；Hysteria2 同时有独立核心。
旧的 PassWall TUIC 选项名不能直接沿用。WireGuard 使用当前 LuCI 协议模块，
Tailscale 使用 `luci-app-tailscale-community`，WOL+ 使用支持 JS/ucode 的维护版本。

L2TP 包括 `xl2tpd`、`ppp-mod-pppol2tp`、`luci-proto-ppp` 和 NSS L2TPv2 驱动。
配置启用加速支持，实际 offload 仍需刷机后检查 NSS/ECM 统计。
已核对两项已知上游崩溃修复：L2TP 会话引用计数和 ECM 重复获取 PPP 锁。
修复已存在于实际构建的源码中，没有额外叠加驱动补丁；仍待真机验证。
Docker Engine/CLI、containerd、runc 使用 feeds 配套版本，升级时需核对 vendor 依赖。

SRun 内置已核对官方 SHA-256 的 0.6.2 AArch64 musl 程序，首次离线即可认证。
默认账号密码为空、服务关闭；截图要求的默认值包括设备名称 `Windows 10`、
检查间隔 `600` 秒，其余参数见 `docs/SRUN.md`。默认值在 UCI、脚本回退值和 LuCI
表单中各有一份，需要一起修改。GPL 许可证和约 40KB 的对应源码归档保留在包目录，
不装入固件根文件系统；旧完整归档和重复安装资料已清理。

## 本机构建与查看结果

在仓库根目录的 PowerShell 中运行：

```powershell
.\scripts\Build-Local.ps1 -Stage Prepare
.\scripts\Build-Local.ps1 -Stage Build -Jobs 8 -Detach
.\scripts\Build-Local.ps1 -Stage Status
.\scripts\Build-Local.ps1 -Stage Logs
.\scripts\Build-Local.ps1 -Stage Export
```

默认容器 `openwrt-arthur-builder`，数据卷 `openwrt-arthur-work`。
容器内项目输入为 `/workspace`，固件源码 `/work/openwrt`，日志 `/work/logs`。
编译在 Linux 数据卷上以普通用户执行；Windows 目录只负责提供输入和接收导出。
新主仓库基线使用新的容器名及卷名，现有卷保留工具链、下载和编译缓存。
本地验证固定主仓库提交；Actions 跟踪配置分支的最新提交，升级后以实际来源记录为准。

修改第三方来源、本地包或依赖后需要重新 `Prepare`；`Config` 只展开现有来源下的配置。
`artifacts/` 和 `.local/` 不纳入 Git。导出包含实际配置、diffconfig、源码提交记录、
包版本覆盖记录和日志；完整构建成功后还包含固件、manifest、profiles 和校验文件。

构建判断依据是容器内 `/work/status` 的最终退出码、固件文件与实际 manifest。
`make defconfig` 通过只证明配置被接受；后台命令启动成功也不代表固件编译完成。
此次本机验证没有触发 GitHub Actions；后续日常构建使用独立的 `Arthur-ImmortalWrt` 工作流，与本地路径共用同一套亚瑟配置及定制脚本。

## 已处理的兼容性问题与验证状态

- `CCACHE` 需要 `DEVEL=y`；zram 使用 `KERNEL_ZRAM_*` 选项。
- `xz` 的 Kconfig 依赖包含 `xz-utils`，SRun 包已声明两者。
- 旧 FRP 界面有未使用的 `luci.model.ipkg` 导入，已移除并补充 LuCI 兼容依赖。
- Homebox 旧配方仍用 2020 年 Go 源码；已保留 LuCI 并换用官方 0.1.3 ARM64 musl 程序，固定归档 SHA-256，启动命令改为 `homebox serve`。其 LuCI 版本号也已适配 APK。
- 当前 feeds 的未使用 `luci-app-weechat` 有递归依赖，安装后移除该链接以避免阻断 Kconfig。
- 配置校验、ShellCheck、PowerShell/JavaScript/YAML 语法和 SRun 模拟运行测试已通过。
- 最新 Xray/Tailscale 要求 Go 1.27（Tailscale 至少 1.27.3），已在版本覆盖中升级 Go 并切换默认主机编译器。
- 更改 Go 默认版本后必须刷新代理包的 Makefile 时间戳，否则包扫描缓存仍依赖旧 Go；版本覆盖脚本已处理，避免并行构建时找不到新工具链。
- 首版 25.12 定制脚本将 LAN 的 `192.168.1.1/24` 覆盖成裸地址，且新版没有独立 netmask，netifd 按 `/32` 解析，导致 DHCP 地址池为空、有线和无线 LAN 均不可用。已改为 `192.168.233.1/24`，并在升级时保留其他自定义 LAN 网段。
- 新增的首次启动测试会在临时 `/etc` 和 `/tmp` 中运行实际 ARM64 配置生成、网络迁移及定制脚本，再验证 DHCP 池和 dnsmasq 配置。旧脚本已确认失败，修复版通过；本地与 Actions 的亚瑟构建均已接入检查。
- 网络故障排查还检查了 125 个动态链接及 9 个静态 ARM64 程序，未发现缺库/架构问题。在隔离容器网络使用实际 dnsmasq 2.93 完成 DHCP Discover/Offer/Request/ACK，地址、`/24` 掩码及网关均正确；这不能代替真机网口/无线验证。
- DHCP 修复版于 2026-10-24 19:19（Asia/Shanghai）完成 Podman 编译，退出码 0，自动首次启动网络测试通过；已直接读取 sysupgrade 的 SquashFS，确认镜像内包含修复脚本。导出修复版位于 `artifacts/dhcp-fixed/`，旧首版镜像不要继续使用。
- 2026-10-24 本机 Podman 完整编译通过（最终退出码 0）；89 项显式配置、475 个内置包符号均通过校验，实际 manifest 为 447 个包，仅生成亚瑟 factory/sysupgrade 镜像。
- 最终镜像 SHA-256、必要功能包、USB 3.0/存储/UAS、SRun 默认值和权限、开机服务已核验。实际 ARM64 Sing-box/Xray/Hysteria 已在 QEMU 运行，TUIC/Hysteria2 配置解析通过；Homebox 0.1.3 网页及 ping/上传/下载接口通过。
- rootfs 为 130.5MiB，内核为 5.31MiB（上游 6MiB 内核布局）。刷机前核对系统分区容量；整盘 64GB/128GB 不等于 rootfs 分区大小。
- 用户首版真机测试发现 LAN/DHCP 故障，修复版尚待重新刷机确认；NSS/L2TP 连接及稳定性仍待实测。尚未实际运行 GitHub Actions，云端工作流已通过 actionlint 静态检查。

GitHub 仓库为 `LaiQE/openwrt-ci-roc`，默认分支 `my`；`origin` 指向个人仓库，
`upstream` 指向编译项目上游。完整构建通过后再整理并正常推送，可保留上游合并历史。
