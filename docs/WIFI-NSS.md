# Wi-Fi NSS 排查与 LibWrt 迁移

更新：2026-10-25。亚瑟 RE-SS-01，512MiB。

## 目前结论

此前 ImmortalWrt 上默认开放 AP 的 Wi-Fi DHCP 故障与 NSS 开关相关，但尚未确定驱动根因。
后续发现 [LibWrt 维护者的置顶说明](https://github.com/LiBwrt/LibWrt/issues/167)：
无线必须设置密码；亚瑟 5GHz 发射功率设为 20dBm，带宽最多 80MHz，2.4GHz 最多 20MHz；
WPA3 存在兼容反馈，建议先测试 WPA2。此前遗漏了密码条件，不能把开放 AP 的测试结果
推广为所有 Wi-Fi NSS 都不可用。

用户要求迁移 LibWrt 并尽量启用所有可用 NSS。当前采用官方 `LiBwrt/LibWrt` 的
`25.12-nss`，实际提交随构建导出，Linux 6.12；使用 **NSS 固件 11.4** 并开启
`ATH11K_NSS_SUPPORT` 和 `ATH11K_NSS_MESH_SUPPORT`。上游配置明确将 Mesh 依赖到 11.4，
相关驱动和客户端自动使用配套来源及 patches-11.4，不混用 12.5 二进制固件。

## 之前实际完成的对照

1. LAN 子网前缀修复后，有线 DHCP 正常；Wi-Fi 接口已加入 br-lan，客户端已关联及授权。
2. 原驱动 NSS 开启时手机获取地址失败；关闭并重启后成功；再次开启失败，再次关闭成功。
3. 已核对 ath11k NSS、mac80211、NSS driver、Wi-Fi offload/扩展 vdev、ECM、桥接等关键项，未发现漏编译。
4. 参考 AgustinLorenzo/openwrt 的 `655c8cabc496e39d3b73fa90cb77bb4fb3aee099`，尝试局部恢复 NSS RX 布局（跳过低内存 RXDMA 覆盖、恢复 2048 字节接收长度），用户实测仍失败。这不是完整上游 revert，现已删除候选补丁。
5. 原模块及关闭 Wi-Fi NSS 的状态已恢复，临时测试回退服务已移除。之后用户拔掉路由器。

以上对照使用开放 AP；尚无设置 WPA2 后的结果。LibWrt 与原源码属于不同维护分支，
切换有测试价值，不能仅凭项目名称保证修复。官方 [Wiki](https://github.com/LiBwrt/Wiki)
说明其集成 qosmio NSS；实际 feeds 按所选分支的 feeds.conf.default 保留。

## 本次镜像与测试步骤

- 使用空 Podman 卷、重新生成的基础镜像完整构建，不复用旧下载、工具链、staging、ccache 或产物。
- 保留 512MiB 内存配置，模块参数明确为 `ath11k nss_offload=1 frame_mode=2`。
- 启用亚瑟稳定可用的 NSS 管理模块、组播支持及 nssinfo；上游 BROKEN 模块不强开。
- 按用户确认，默认无线启用状态恢复为 LibWrt 上游行为；测试 NSS 时仍需先设置 WPA2 密码。

用户手动全新烧录后：通过有线访问 `192.168.233.1`，设置管理员密码和无线 WPA2-PSK/CCMP
密码，再启用 AP。2.4GHz 20MHz、5GHz 80MHz/20dBm，先测试普通 AP DHCP，
再测试吞吐、断开重连、长时间负载；Mesh 是另一个需要实际配置和验证的场景。

如仍故障，采集无线配置（隐藏密钥）、ubus 无线/接口状态、bridge link、hostapd/netifd/
ath11k 日志，以及 `/sys/module/ath11k/parameters/nss_offload`、NSS/ECM 统计。
运行 nssinfo 或读取 debugfs 计数确认实际加速，不以低 CPU 占用单独判断。
只有再次证实加密 AP 也失败后，才决定是否关闭 Wi-Fi NSS；有线 NSS 可独立保留。
