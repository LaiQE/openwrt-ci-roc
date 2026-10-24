# SRun 校园网自动认证

本地包位于 `package/luci-app-srun-autologin/`，默认使用
`CONFIG_PACKAGE_luci-app-srun-autologin=y` 编译进亚瑟固件，无需开机后下载安装。
内置用户原组件中的 srun 0.6.2 AArch64 musl 静态程序，已与官方发布逐字节核对。

进入 LuCI「服务 → 校园网自动认证」，填写账号和密码，启用并保存应用。
账号、密码默认为空，服务默认关闭。开机服务启用后，每 600 秒检查一次；
在线时跳过认证，离线时调用 srun，认证后再次检查网络。

默认值已按提供的截图统一写入 UCI、脚本和 LuCI 页面：

| 参数 | 默认值 |
| --- | --- |
| 认证服务器 | `http://net.zju.edu.cn` |
| 认证网卡、固定 IP | 留空，自动探测 |
| 连通性地址 | `223.5.5.5` |
| 最多 ping 次数 / 单次超时 | `3` / `2` 秒 |
| 检查间隔 | `600` 秒 |
| 严格绑定 / 双栈 | 关闭 / 关闭 |
| 重试延迟 / 次数 | `1000` 毫秒 / `3` |
| n / type / AC ID | `200` / `1` / `60` |
| 操作系统 / 设备名称 | `Windows` / `Windows 10` |
| 二进制缺失时自动下载 | 开启，固定版本并校验 SHA-256 |

配置文件 `/etc/config/srun-autologin` 和临时认证 JSON 均限制为 root 可读。
系统内置的二进制可直接用于首次离线认证。恢复下载仅供二进制意外丢失时使用。

诊断命令：

```sh
srun-autologin status
srun-autologin run
logread -e srun-autologin
```

测试位于 `tests/srun-autologin/`，覆盖在线跳过、离线三次探测、认证后复检和日志脱敏。
旧目录中的重复安装包、完整归档、单独脚本副本和旧 SDK 构建工具不参与本项目。
保留了实际包源码、测试、来源校验记录、GPL 许可证及约 40KB 的对应 srun 源码归档；
这些构建资料不会进入固件根文件系统。

升级时保留配置会沿用旧 UCI 值；新默认值适用于全新安装或恢复默认配置。

上游：[zu1k/srun 0.6.2](https://github.com/zu1k/srun/releases/tag/0.6.2)。
