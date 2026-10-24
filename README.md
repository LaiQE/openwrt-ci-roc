# OpenWrt / ImmortalWrt 亚瑟固件

京东云 **亚瑟 RE-SS-01** 专用编译项目。以原有功能为基础同步
[laipeng668/openwrt-ci-roc](https://github.com/laipeng668/openwrt-ci-roc)
的新版流程，默认先用本机 Podman 编译。不会构建雅典娜或太乙。

- 管理地址：`192.168.233.1`；主机名：`Arthur`；用户：`root`。
- 源码：[laipeng668/immortalwrt](https://github.com/laipeng668/immortalwrt)，
  `openwrt-25.12` 分支，稳定内核 **6.12**、NSS **12.5**、512MiB 内存配置。
- 本地构建基线固定在 `configs/source.env`，完整 feeds/第三方提交记录随构建导出。
- 本项目不预置用户密码和校园网凭据。

## 内置功能

保留原配置中已启用的 LuCI 功能，清理重复依赖、失效符号和无关插件下载。

| 功能 | 配置 / 说明 |
| --- | --- |
| Docker、Compose、磁盘管理 | `luci-app-dockerman`、`docker-compose`、`luci-app-diskman` |
| 磁盘工具 | GPT/sgdisk、fdisk、e2fsprogs、resize2fs、fstrim、mmc-utils、block-mount |
| 代理 | PassWall + Xray + Sing-box + Hysteria；TUIC、Hysteria2、VLESS/Reality、VMess、Trojan、Shadowsocks 等 |
| DNS、动态域名 | AdGuard Home、DDNS、**DDNS-Go** |
| VPN、内网穿透 | WireGuard、ZeroTier、Tailscale、L2TP、FRP 多服务器客户端 |
| 唤醒与网络管理 | **Wake on LAN+**、UPnP、ARP 绑定、在线用户、Homebox 内网测速 |
| 系统管理 | Argon 配置、CPU 调频、ttyd、自动重启、IRQ balance、SFTP、zram、vlmcsd |
| 校园网 | **SRun 自动认证**，程序、LuCI 和开机服务内置；[配置说明](docs/SRUN.md) |
| 可选模块 | 保留 `luci-app-mwan3=m`，生成安装包但不装入默认根文件系统 |

旧 `luci-app-wireguard` 的功能由当前 `luci-proto-wireguard` 和 LuCI 状态页提供；
旧 Tailscale 界面更新为官方 feeds 的 `luci-app-tailscale-community`。
WOL+ 使用支持现代 LuCI 的 JS/ucode 版本。
Git/LFS、Vim、Zsh、Screen 等开发工具放在 `configs/Extras.config`，默认使用 BusyBox/ash。
不再强制切换 root shell，也不再配置 ttyd 免登录。

## 本机 Podman 编译（Windows PowerShell）

先启动 Podman machine。在仓库根目录执行：

```powershell
# 构建容器、克隆源码、更新 feeds，并严格核对每一个显式配置选项
.\scripts\Build-Local.ps1 -Stage Prepare

# 完整构建；可用 -Detach 使构建在容器后台继续
.\scripts\Build-Local.ps1 -Stage Build -Jobs 8 -Detach

# 查看运行状态与日志
.\scripts\Build-Local.ps1 -Stage Status
.\scripts\Build-Local.ps1 -Stage Logs

# 导出固件、解析后的配置、实际包列表、源码提交记录和日志
.\scripts\Build-Local.ps1 -Stage Export
```

默认容器为 `openwrt-arthur-builder`，持久数据卷为 `openwrt-arthur-work`。
源码、工具链、下载和编译缓存存放在 Podman 的 Linux 文件系统中，避免在 Windows
大小写不敏感的目录中构建。容器以普通用户编译，不需要 privileged。

`Config` 阶段只重新展开配置，`Download` 只下载，`Shell` 进入构建容器。
每次运行自动复制本项目的配置、脚本和本地包。容器中的同一数据卷可断点续编。
若修改 `configs/source.env` 中的源码提交，使用新的 `-Container` 和 `-Volume`，
以免将旧工具链混入新基线；命名卷不会自动删除。

导出目录为 `artifacts/`（已 gitignore）：

- `Arthur.config` / `Arthur.diffconfig`：实际展开的配置和最小差异。
- `selected-packages.txt`：Kconfig 选中的包符号，最终安装列表以固件 manifest 为准。
- `build-sources.txt` / `package-updates.json`：实际源码提交和补丁版本覆盖记录。
- `logs/`：准备、下载和编译日志；成功构建后同目录包含固件及校验文件。

如果 Kconfig 忽略了已请求的包或选项，`verify-config.py` 会直接报错，避免漏包后继续编译。

## L2TP 与 NSS

内置 `xl2tpd`、`ppp-mod-pppol2tp`、`luci-proto-ppp` 和
`kmod-qca-nss-drv-l2tpv2`，启用 `NSS_DRV_L2TP_ENABLE`，保留 NSS ECM。
LuCI「网络 → 接口 → 添加接口」可选择 L2TP 客户端。
这是 PPP/L2TPv2 客户端；L2TP/IPsec 和 L2TP 服务端需要另行配置。
实际连接能否 offload 取决于拓扑、对端与驱动限制，应在真机核对 NSS/ECM 统计。
代理流量和 QUIC 加密流量不因启用 NSS 而自动硬件加速。

## 磁盘分区

没有发现可确认适配亚瑟并自动兼容 64GB/128GB 的可靠首次启动分区脚本。
按用户要求保留手动分区，固件不会自动格式化、扩分区或修改 GPT。
上游 `automount` 只自动挂载已有分区，还会拉入 USB/NTFS/exFAT 等依赖，
亚瑟使用 `block-mount` 和 LuCI 磁盘管理即可。
Docker 数据目录先保留上游默认值，完成数据分区和持久挂载后再设置。

## 软件版本和更新

官方包优先使用匹配的 25.12 feeds 最新提交；PassWall 及其核心从目前的
[Openwrt-Passwall](https://github.com/Openwrt-Passwall) 维护仓库获取。
FRP、Compose 采用最新 master 配方；对 Tailscale、FRP、Compose 的新补丁版本
在 `configs/package-updates.json` 中固定版本及官方源码 SHA-256。
Docker Engine/CLI、containerd、runc 保留 feeds 维护者配套版本，避免单独升级破坏
vendor 版本校验。保留的旧 LuCI 插件也会拉取其维护仓库最新提交。

本地重复构建复用已经准备好的来源；要主动刷新 feeds/第三方来源，可在构建容器中
删除 `/work/openwrt/.prepared` 后重新运行 `Prepare`。源码主仓库仍受 `source.env` 固定。

GitHub Actions 新版通用流程已同步，手动入口为 `Arthur-ImmortalWrt`。
本次本地验证不触发 Actions，也不自动发布 Release。

## 许可与来源

保留项目的 MIT 许可证。固件与第三方软件分别遵循各自许可证。
SRun 包的 GPL 许可证及对应源码归档随本地包保存。

上游编译项目：[laipeng668/openwrt-ci-roc](https://github.com/laipeng668/openwrt-ci-roc)。
WOL+：[sakura-builder1/luci-app-wolplus](https://github.com/sakura-builder1/luci-app-wolplus)。
