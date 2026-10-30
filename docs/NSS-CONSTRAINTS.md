# LibWrt NSS 配置限制与来源

核对日期：2026-10-25。适用本项目的京东云亚瑟 RE-SS-01、IPQ60xx、LibWrt `25.12-nss`。

本文区分 LibWrt 维护者要求、官方链接的 NSS 上游注意事项，以及本项目的排障建议。无线参数按所述机型和驱动理解，不推广为所有高通芯片的硬件上限。

## Wi-Fi 参数

| 项目 | 要求或限制 | 性质与来源 |
| --- | --- | --- |
| 无线密码 | 设置密码，避免开放 AP | 维护者明确要求，[S1][s1] |
| **亚瑟 5GHz 最大传输功率** | **明确设为 20dBm**；维护者指出其他设置可能限制速率 | 亚瑟特定要求，[S1][s1] |
| IPQ6018 的 5GHz 带宽 | 最多 **80MHz**，不使用 160MHz | 维护者列出的配置上限，[S1][s1] |
| IPQ6018 的 2.4GHz 带宽 | 最多 **20MHz**，不使用 40MHz | 维护者列出的配置上限，[S1][s1] |
| WPA3 | 存在无法启用的用户反馈，原因未确定 | 兼容性提示，不能写成“一律不支持”，[S1][s1] |

20dBm 的要求针对**亚瑟的 5GHz**；该说明没有给出亚瑟 2.4GHz 的统一功率值。

本项目排障建议：先用 **WPA2-PSK/CCMP** 加密，按上表测试普通 AP 的 DHCP、重连和吞吐。这是排障基线，不是官方规定的唯一加密方式。

## NSS 网络配置注意事项

以下来自 qosmio NSS 上游 README。LibWrt 的 [Wiki][wiki] 和主仓库均将其链接为“重要提示”，来源层级与上述机型要求不同。

| 配置 | 上游注意事项 | 来源 |
| --- | --- | --- |
| Packet Steering（数据包分流） | 使用 NSS 时关闭，避免干扰 NSS 路径 | [S2：Packet Steering / Flow Offloading][offload] |
| 软件、硬件 Flow Offloading（流量分载） | 同样关闭；这些开关与 NSS 是不同机制，不是启用 NSS 的开关 | [S2：Packet Steering / Flow Offloading][offload] |
| Bridge VLAN filtering | 上游标明与 Wi-Fi NSS 不兼容；避免 `config bridge-vlan` 及桥端口的 DSA VLAN 标记配置 | [S2：Bridge VLAN filtering][vlan] |

VLAN 限制针对上述桥过滤方式，不代表所有 802.1Q VLAN 都不能使用。上游给出的替代示例是将 `lan1.20` 这类 VLAN 子接口加入单独的桥。实际改网前应对照本分支的设备结构；此处不提供直接覆盖配置的命令。[S2][vlan]

## 固件版本与功能边界

| 功能 | 官方说明 | 来源 |
| --- | --- | --- |
| Wi-Fi Mesh / WDS 的 NSS 卸载 | 依赖 NSS 固件 **11.4** | [S3：功能矩阵][matrix] |
| Mesh 编译选项 | 同时启用 `CONFIG_NSS_FIRMWARE_VERSION_11_4=y`、`CONFIG_ATH11K_NSS_MESH_SUPPORT=y` | [S1][s1] |
| Wi-Fi AP VLAN | 标为 ath11k 驱动存在故障 | [S3：功能矩阵][matrix] |
| IPsec、TLS、DTLS、CAPWAP、PVXLAN、CLMAP | 当前矩阵标为 NSS 固件 11.4–12.5 中不可用 | [S3：功能矩阵][matrix] |
| IPQ60xx 的 RMNET | 标为该平台不可用 | [S3：功能矩阵][matrix] |

矩阵描述的是 **NSS 卸载能力**；据此不能推断 Linux 上的软件 TLS/IPsec 服务不能运行。矩阵列为支持的功能，也仍需验证本机实际流量是否进入 NSS。

## 本项目已选配置与使用建议

[Arthur.config](../configs/Arthur.config) 已选择 NSS 11.4、ath11k NSS 和 Mesh NSS；[模块参数](../files/etc/modules.d/ath11k) 为 `nss_offload=1 frame_mode=2`。

使用时先通过有线连接 LuCI，给无线设置密码及上表参数，再测试普通 AP。Packet Steering、Flow Offloading 和桥 VLAN 设置应另行核对；编译选项已启用不代表运行中的网络配置已逐项符合要求。

运行状态及旧故障排查见 [Wi-Fi NSS 记录](WIFI-NSS.md)，L2TP 的已知修复和验证边界见 [NSS/L2TP 记录](NSS-L2TP.md)。本文件整理使用约束，不改动固件默认配置。

## OpenAppFilter 与 NSS

补充核对日期：2026-10-30。检查原作者 [destan19/OpenAppFilter](https://github.com/destan19/OpenAppFilter) 的 `0814b87f57181ef238b9a21604c999e98de73cf2`，服务版本 7.0.2。

- 作者在 [Issue #287](https://github.com/destan19/OpenAppFilter/issues/287) 说明 NAT 卸载可能让流量绕过 OAF DPI，导致过滤失效。
- 当前源码的 [hnat.sh](https://github.com/destan19/OpenAppFilter/blob/0814b87f57181ef238b9a21604c999e98de73cf2/open-app-filter/files/hnat.sh#L13-L26) 在用户选择禁用加速时，将 ECM 的 `accel_delay_pkts` 提高到 1000000；这是延迟进入 NSS 加速的措施，不是让已加速流量接受完整 DPI。
- 上游默认 `disable_hnat=0`，并非装入 OAF 就一定关闭 NSS。但保留 NSS 与保证 OAF 对所有流量可靠识别、过滤，不能据此视为已兼容。

本项目保留 NSS，不内置 OAF 核心、模块及 LuCI。按用户后续明确授权，另外将原作者上游编成独立实验 APK，供手动安装验证；这不表示已确认兼容，见 [实验包说明](OAF-EXPERIMENT.md)。此结论针对当前检查到的实现，不宣称所有未来版本都无法兼容。

### 其它应用识别/拦截方案

本次尚未找到同时满足“LuCI 可配置、非单纯 DNS、可靠保留亚瑟 NSS、可直接安装”的成熟替代品：

- [Netify 5 NFQUEUE](https://www.netify.ai/documentation/agent/v5/configuration/network-interfaces) 支持先识别再交给快速路径，但默认 NFQUEUE 判定为接受，拦截还需要策略和防火墙联动；通用硬件卸载说明不能视为已验证 Qualcomm NSS。当前 25.12 feed 的 netifyd 仍为 4.4.7，也不能直接替代其 5.x 方案。
- [SecuBox 的 LuCI 模块](https://github.com/CyberMind-FR/secubox-openwrt/blob/master/README.zh.md) 提供 netifyd/nDPId 面板，但面板存在不等于 NSS 流量拦截已适配。
- [nDPId](https://github.com/utoni/nDPId) 主要提供流量识别和 JSON 事件；仍需拦截策略层及 NSS 路径适配，不能单独当作本项目可用的应用封锁包。

因此没有把这些未确认的方案编成“已兼容”的替代包；本轮独立实验包只包含用户明确要求尝试的 OAF。

## 来源索引

- **S1**：[LibWrt 置顶 Issue #167：WiFi 有问题的请进来][s1]。作者为维护者 laipeng668；2025-07-04 开立，本文按核对日期的正文整理。WPA3 条目保留原文的“用户反馈、原因未知”性质。
- **S2**：[qosmio/openwrt-ipq：Important Note][notes]。这是 LibWrt 官方 Wiki/README 引用的 NSS 上游文档，本文使用其 Packet Steering / Flow Offloading、Bridge VLAN filtering 两节。
- **S3**：[LibWrt `25.12-nss` README：NSS 功能支持矩阵][matrix]。用于核对固件版本及功能边界；不能替代具体机型的真机测试。

[s1]: https://github.com/LiBwrt/LibWrt/issues/167
[wiki]: https://github.com/LiBwrt/Wiki#其中对于高通nss的wikiwiki
[notes]: https://github.com/qosmio/openwrt-ipq/blob/main-nss/README.md#important-note
[offload]: https://github.com/qosmio/openwrt-ipq/blob/main-nss/README.md#1-packet-steering--flow-offloading
[vlan]: https://github.com/qosmio/openwrt-ipq/blob/main-nss/README.md#2-bridge-vlan-filtering-dsa-syntax
[matrix]: https://github.com/LiBwrt/LibWrt/blob/25.12-nss/README.md
