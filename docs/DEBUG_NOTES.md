# 调试记录

## 2026-10-24：更新与 LibWrt 迁移

- 合并编译项目上游，定制内容拆到 Arthur 配置/脚本；其他机型与通用工具保留上游版本。
- 首版 25.12 LAN 初始化漏掉 /24，地址被解析成 /32，导致 DHCP 池为空。改为 192.168.233.1/24，保留管理员自定义网段，并加入 ARM64 首次启动检查。
- 默认开放 AP 下，Wi-Fi NSS 开启时无法获取地址，关闭后恢复。一个局部 RX 布局候选补丁真机无效，已移除。后发现 LibWrt 维护者要求 Wi-Fi 设置密码，此前遗漏了该条件。
- 用户要求切换 LibWrt，选择 NSS 11.4 并启用 Mesh。删除旧 ImmortalWrt 容器、卷和产物，从空环境构建。用户自行导出、烧录后反馈基本使用无大问题，尚无各 NSS 路径的加速统计。
- 容器曾因僵尸进程达到 PID 限额而失败，构建容器改用 --init。

## 2026-10-25：恢复默认行为与主题更新

- 按用户确认恢复默认 Wi-Fi 开启、Zsh、ttyd root 免登录、原工具、BusyBox lsusb 和 Build by LaiQE 署名。编译优化与 nlbwmon 刷新保留上游默认，每周触发关闭。
- Tailscale 恢复 asvow 界面及服务配置；来源已使用 VPN 菜单。WOL+ 保留新版，WireGuard 跟随最新 LuCI。
- AdGuard Home 取消此前删除 YAML/模板的处理，保留来源默认设置，只做必要构建兼容；按用户要求停止专项测试。
- 旧版构建的 make 已完成，但后续服务检查失败：隔离测试没有 /tmp/lock，procd 无法创建锁文件。补齐测试环境后复验通过；不将该退出码 1 的流水线描述为全部验证成功。
- 当前 feeds Argon 为 2.4.7，改用原作者最新 master（当前 3.1.0），包含较新的对话框样式及稳定版模板兼容修复。未发现 LibWrt 官方专用分支；sbwml 的 25.12 分支较旧，本次未采用。按用户要求停止本地 UI 测试，实际页面留待刷机确认。
- Argon 3.x 自带配置页，移除会造成文件冲突的旧独立配置插件。
- 续编曾残留旧 Argon 翻译 APK，其版本号更高而拉回旧插件。清理旧 APK（含 staging 软链接）并重建索引后恢复；没有使用覆盖文件冲突的选项。
- Homebox 恢复原上游配方；旧配方调用 go-bindata 时遗漏 Go 工具路径，补构建路径，保留运行服务与默认配置。
- 恢复上游 automount，作用为挂载已有文件系统，不负责自动分区或格式化。
- LibWrt 实际 manifest 带设备名，Actions 亚瑟入口改用对应文件名；本地复制输入时同步清理已删除文件，避免旧输入残留。
- 01:43 最终构建及首次启动网络、固件内容校验全部通过，退出码 0，共 464 个内置包。factory 为 164253890 字节，sysupgrade 为 163584273 字节；导出后复核 SHA-256 一致。Argon 3.1.0、AdGuard Home 来源默认设置已编入，新版实际使用效果待用户刷机确认。

## 刷机后调整与二次编译

- 用户确认一次 DHCP 故障为网线误插 WAN，未修改 LAN /24 配置。
- Docker 默认关闭：首次初始化禁用未明确开启的 dockerd；Dockerman 的初始化重启也遵守自启状态，保留管理员后续的开启选择。
- ULA 空白来自上游 991_set-network.sh 主动删除，亚瑟定制只移除删除行，保留随机生成和手动设置的前缀。
- 用户确认清除浏览器缓存后概览署名正常；保留概览实现和缓存策略，页脚用署名替换发行版链接，LuCI 信息去掉 branch/修订号，保留 Argon 版本。
- Docker 关闭/手动开启保留、随机/自定义 ULA 已通过隔离 rootfs 的 ARM64 首次启动模拟；最新页脚替换及重复执行检查、ShellCheck 通过。
- 清理 base-files、Argon、Dockerman 后重新编译，02:25 完整构建及网络/固件检查退出码 0，仍为 464 个内置包。新镜像已导出并复核 SHA-256，待用户刷机验证；Tailscale 使用未修改的上游 VPN 菜单。

## Docker 原生 nftables 迁移

- 切换到 ysuolmai/openwrt-packages:main 的 dockerd 与 Lua Dockerman，保留独立 Docker 菜单及原有 Lua 客户端的 API v1.40 兼容修正。
- Docker/CLI 对齐 29.6.2，containerd 对齐官方 Dockerfile 的 2.2.6；runc 1.3.6、tini 0.19.0 保持配套。对官方源码计算 SHA-256，替代导入配方的 PKG_HASH=skip。
- 维持 Docker 出厂默认关闭；将 fw4 初始化放进手动启动路径，ACL 也支持手动启动且自启关闭的情况。移除会清空 DOCKER-USER 的旧规则自动清理。
- 用户最后要求保留来源原样的自动分区/格式化脚本，因此取消最初的排除处理；该首启脚本独立于 Docker 是否自启。为更新构建输入主动停止过一轮任务，日志中的退出码 141 对应这次中止。
- ARM64 隔离测试验证了手动启动的 daemon.json、fw4 出口转发和 nftables ACL 生成；没有执行真实磁盘分区或真机容器转发测试。
- 03:18 完整构建与网络/固件检查退出码 0，共 480 个内置包，镜像已导出并复核 SHA-256。自动分区脚本与导入来源逐字节一致。
- 额外运行 dockerd --validate 时，PRoot 对 faccessat2 的路径仿真导致 docker-proxy 查找失败；在真实 chroot 加 QEMU 环境下校验通过，无需修改引擎默认参数。

## 亚瑟 eMMC 分区与 swap 修复

- 03:18 镜像的来源脚本未能扩容：64GB eMMC 的 GPT 尾部仍指向约 3.9GB，parted 无法按 100% 使用剩余空间；脚本还会把 mmcblk0boot1 当作新分区。失败后仍 exit 0，导致首次启动脚本被删除。Docker 的 overlay 自绑定也会使原挂载检测误判。
- 按用户提供的 sgdisk 方案修复 GPT 并创建 storage；64GB 实机新增 p27，原 26 个 GPT 条目逐字节保持不变。新分区 ext4 挂载 /opt/docker，迁移并核对原 Docker 数据，保留旧 overlay 副本 /opt/docker-overlay-backup。分区表及数据备份已下载至忽略目录 .local/arthur-storage-backup。
- 初始化脚本写入仓库并装入 dockerd 包：先找 storage，再复用已有 p27；必须大于 1GiB，已有分区不格式化。没有时才创建新分区。对尚未迁移的挂载点数据拒绝覆盖，错误保留脚本重试。
- 实机 p26 标签为 swap，但实际是空 ext4；确认只有空 lost+found 后转为 512MiB swap，写入 fstab，优先级 10，zram 100 保留。已有有效 swap 不重复 mkswap；含数据的 ext4 占位分区拒绝转换。BusyBox mkswap 不生成 UUID，需支持 fstab 按设备启用。
- 实机 BusyBox find 没有 -quit，脚本使用兼容选项；lib/functions.sh 不兼容 set -u，按 OpenWrt 方式使用 set -e。Docker 启动为异步，等待 API 就绪后确认 0 容器、0 镜像及 /opt/docker 根目录正常，自启仍为 0。
- 编译前复查补齐 uci-defaults 条件 source 的兼容：这种调用方式会抑制 set -e，关键操作改为显式检查失败，避免挂载或配置保存失败后仍删除脚本。隔离测试模拟该调用方式，覆盖挂载和配置提交错误，接入本地与 Actions 流水线。
- 64GB/128GB 稀疏镜像以实际 ARM64 sgdisk 验证新算法，均保留原 26 个 GPT 条目。隔离逻辑检查覆盖创建、旧 p27 标签差异、容量门槛、重复运行、swap 数据保护和挂载失败。真机验证了未挂载 p27 的自动挂载、文件/UUID 保留及 block mount 重新启用 swap。128GB 尚未真机测试。
- 07:56 完整构建及分区、网络、固件校验全部通过，退出码 0，仍为 480 个包。factory 为 165007894 字节，sysupgrade 为 164546833 字节；已导出并复核 SHA-256。另从最终 sysupgrade 的 squashfs 直接核对了初始化脚本。新镜像待用户烧录，未自动刷机；本次未运行 GitHub Actions。

## 2026-10-30：APK 仓库与 OpenAppFilter 核对

- 用户报告 apk update 的 nss_packages、sqm_scripts_nss 两个索引失效。分别核对 vsean 镜像和 ImmortalWrt 下载站：两者这两个路径均为 404，而 base/luci/packages/routing 均为 200。include/feeds.mk 确认 CONFIG_FEED_* 控制镜像内仓库条目；关闭这两个标志，保留源码 feed 和内置 NSS 包。固件检查增加对应的仓库条目与包列表约束。
- 使用已有固件公钥，在隔离 root 中删除这两条地址后执行真正的 apk update；两个站均返回 0、9469 个可用包。distfeeds.list 是自动生成的文件，apk 仅将 customfeeds.list 声明为 conffile，因此没有修改用户自定义源文件。
- 原作者 destan19/OpenAppFilter master 0814b87（服务 7.0.2）仍提示硬件加速会影响 DPI，并以提高 ECM accel_delay_pkts 到 1000000 处理禁用加速；作者 Issue #287 也说明卸载可能绕过 DPI。用户明确 NSS 优先，随后又明确要求 OAF 编为独立实验包，因此不改变 NSS 配置，不预装 OAF，将核心、内核模块和 LuCI 设为 m。Netify 5 NFQUEUE 等替代方向没有找到可靠的亚瑟 NSS/LuCI 拦截配套证据，不宣称兼容。
- 为加入独立实验包，主动停止一轮尚在 host tools 阶段的构建，退出码 143 对应该次中止；随后按新配置继续构建。独立归档验证内核 ABI，并收集新固件未内置的必要依赖，便于手动安装。
- 新容器首次完整编译暴露 Homebox host 构建需要 npm，而 Containerfile 未声明 Node.js/npm；补齐镜像依赖并在本轮容器安装对应工具后续编，不修改 Homebox 运行默认值。
- 独立归档适配 APK 的 noarch 标记。模拟安装又发现常规 OpenWrt APK 依赖仓库索引签名，离线文件默认没有独立签名；导出时只对副本使用本轮构建密钥签名，保留固件公钥验证，不以 allow-untrusted 绕过检查。
- LibWrt 25.12-nss 从 3a3d0b0 更新到 a151272；本轮使用新容器 openwrt-arthur-libwrt-20261030-builder 和新卷 openwrt-arthur-libwrt-20261030-work，从新的源码、工具链和构建目录开始。
- 17:48 完整构建及分区、网络、固件检查通过，退出码 0；内核 6.12.112，仍内置 480 个包。factory 为 165054682 字节，sysupgrade 为 164618513 字节。修复源在最终公钥下对两个站实际 apk update 均通过；最终 squashfs 复核源条目及 OAF 缺席。
- OAF 独立归档包含 5 个 APK（7.0.2 核心、6.12.112 模块、LuCI、中文、SQLite），签名验证及同轮固件数据库模拟安装通过；包内 SHA-256、导出固件/归档 SHA-256 均核对。本轮未刷机、未在路由器上安装实验包，运行兼容性不作保证。

## 2026-10-31：OAF 内置与 NSS 运行设置

- 用户安装独立 APK 后，菜单缺失最终确认为浏览器缓存；特征库在线更新显示成功但应用目录不变时，实机没有加载 oaf 模块，/proc/sys/fwx 不存在。重启后用户反馈 OAF 恢复正常。
- 用户在 LuCI 手动开启了软件/硬件 Flow Offloading，运行值为 1/1，而构建默认值是 0/0。根据 NSS 上游说明，改为 LuCI「网络 → 防火墙 → 流量卸载类型：无」；README 增加界面操作与 special 加速统计的判断方法。
- 随后的 IPv4 直连测试中，special 接收字节在 10 秒内增加约 624MB，确认实际 NSS 加速；IPv6 加速仍为 0，用户明确停止这部分排查，不据此更换 NSS 驱动或固件。
- 用户要求正式内置 OAF，并选择保留管理后台自启、仅默认关闭功能。luci-app-oaf/appfilter/kmod-oaf 改为 y；TCP 重置、应用过滤、上网控制、上网审计的 UCI 模板和缺失配置回退均改为 0，其他来源默认值保留。新增 prepare-oaf.py，停止导出独立实验归档。
- 临时 ARM64 固件副本验证通过：四项默认值为 0，启动仍注册 oafd/rule_manager，删除配置后回退为 0，用户手动启用后重启不覆盖。检查接入本地及 Actions，最终镜像仍须通过同样验证。
- LibWrt 跟踪分支已推进至 96a0ec8，因此新建 openwrt-arthur-libwrt-20261031-builder / openwrt-arthur-libwrt-20261031-work；仅复用带构建哈希校验的下载缓存，源码、工具链及构建目录重新生成。
- 16:15 首轮完整编译退出 2：最新 NSS feed 880c1d8 的 0028 补丁新增 ecm_conntrack_exp_event，但 LibWrt 开启 CONFIG_NF_CONNTRACK_CHAIN_EVENTS，回调未使用，被 -Werror=unused-function 拒绝。仅将新增函数的编译条件加上 !defined(CONFIG_NF_CONNTRACK_CHAIN_EVENTS)，与原有使用条件一致；不关闭编译错误检查，不改运行加速逻辑。
- ECM 包清理后单独重建通过，再完成整轮编译：16:29 最终退出码 0，内置 485 个包，内核仍为 6.12.112。分区、ARM64 首次启动网络、OAF 默认值/回退/保留和固件检查均通过。
- 最终 sysupgrade 的 squashfs 已复核：四项 OAF 开关均为 0，管理后台 S96appfilter、oafd、oaf.ko 及 LuCI 已装入，APK 源条目保持修复；基础特征库与原作者源码一致。factory 为 166219498 字节，sysupgrade 为 165796113 字节，导出至 artifacts/20261031-oaf/ 后全部 SHA-256 一致；新镜像尚未烧录，Actions 尚未实际运行。

## 2026-10-31：共享数据分区与 Docker bind

- 用户要求将末尾数据分区用于通用存储：保留 storage/p27、大于 1GiB、64/128GB GPT 扩容及 swap 保护逻辑，分区改挂 /data，/data/docker 再绑定到 /opt/docker，Docker data_root 路径不变。
- 用户截图的 p27 已实际挂载正常；“不存在”是禁用的旧 /rom、/overlay UUID 条目。初始化先备份 fstab，仅清理这类禁用且 UUID 无法解析的系统条目和项目旧 mountdocker 无效条目，保留有效或启用的用户配置。
- 当前 fstools block.c 的 main_mount 只遍历设备，不执行目录来源的 bind。因此增加 S12arthur-data（fstab 为 S11），以及 dockerd 手动/自动 start 的挂载前置检查；验证 mountinfo 的设备号与 /docker 根，避免绑定缺失后写入 overlay。
- 用户随后明确无需迁移旧 Docker 数据，改为停机后删除识别到的旧根标准 Docker 数据；保留一般文件和已有 /data/docker。UUID 标记支持清理中断后重试，旧数据目录中有挂载时拒绝递归删除；未挂载的 overlay 数据也不覆盖。17:16 启动的一轮构建因此主动中止，退出 143 对应该次中止。
- 新布局和旧布局回归均通过；无真实磁盘映射的临时容器中，真实 tmpfs/bind 的 inode、写入、重复启动及覆盖保护检查通过。
- 17:29 最终构建退出 0，485 个包；存储、ARM64 首次启动网络、OAF 及固件检查全部通过。直接从 sysupgrade 的 squashfs 复核最终挂载与清理脚本、S12 恢复入口、Docker 启动保护和 OAF 四项默认关闭。
- factory 为 166221902 字节，sysupgrade 为 165796113 字节；导出至 artifacts/20261031-data/，全部 7 条 SHA-256 记录复核通过。已有 /data/docker 完整保留的用例通过，新的挂载方案尚未真机刷入验证。

来源：
[LibWrt Wi-Fi 说明](https://github.com/LiBwrt/LibWrt/issues/167)、
[Argon 弹窗修复](https://github.com/jerrykuku/luci-theme-argon/commit/1055e79)、
[Argon 3.1.0](https://github.com/jerrykuku/luci-theme-argon/releases/tag/v3.1.0)。
