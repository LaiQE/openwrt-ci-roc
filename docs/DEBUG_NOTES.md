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

来源：
[LibWrt Wi-Fi 说明](https://github.com/LiBwrt/LibWrt/issues/167)、
[Argon 弹窗修复](https://github.com/jerrykuku/luci-theme-argon/commit/1055e79)、
[Argon 3.1.0](https://github.com/jerrykuku/luci-theme-argon/releases/tag/v3.1.0)。
