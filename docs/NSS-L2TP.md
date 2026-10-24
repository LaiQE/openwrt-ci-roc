# NSS 与 L2TP 崩溃检查

检查日期：2026-10-24。针对用户报告的“旧固件启用 NSS 后使用 L2TP 导致崩溃”。

## 结论

发现与症状高度一致的[上游问题 #69](https://github.com/qosmio/openwrt-ipq/issues/69)：
PPPoL2TP 的引用计数错误及 ECM 重复获取 PPP 锁可引发 panic、死锁和 RCU stall。
LibWrt 基线的内核补丁和所选 NSS feed 已包含对应修复，并已核对实际应用补丁后的 C 代码。
目前没有确认需要另外修改驱动的具体问题。

旧固件没有提供崩溃堆栈，不能断定其原因；源码检查和编译也不能代替真机连接、
负载及断线重连测试。本固件继续保留 NSS/L2TPv2 支持，待刷机验证。

## 核对的源码

主仓库基线：`LiBwrt/LibWrt@3a3d0b08595530070ad9cd8a20c0ae4ea3e77f70`，
Linux `6.12.108`，NSS feed `qosmio/nss-packages@0d970dbf0185e3f53709bd803e8a466598023c57`。
采用 NSS 固件 11.4.0.5 Release 6，并由配方自动选择 11.4 驱动和客户端。
ECM 继续使用该 feed 的当前维护版本和修复，不应仅凭包版本号将它降级。

| 检查项 | 本次实际代码 |
| --- | --- |
| 会话引用释放 | 内核 `net/l2tp/l2tp_ppp.c` 的 `pppol2tp_get_channel_protocol_ver()`、`pppol2tp_get_addressing()` 使用 `l2tp_session_put(session)`，不再错误地释放 socket |
| PPP 锁重复获取 | ECM `ecm_interface.c` 的相关接口识别路径使用 `__ppp_is_multilink()`、`__ppp_hold_channels()`；对应内核函数已定义并导出 |
| 修复来源 | 内核 `target/linux/qualcommax/patches-6.12/0603-2-qca-nss-clients-add-l2tp-support.patch` 已整合引用计数修复；NSS feed 包含 `qca-nss-ecm/patches/0025-ecm_interface-fix-ppp-deadlock-use-lockless-functions.patch` |
| L2TPv2 驱动 | `qca-nss-clients/l2tp/l2tpv2/nss_connmgr_l2tpv2.c` 包含 PPP 通道检查、L2TPv2/UDP 检查以及接口 UP/DOWN 管理路径 |

ECM 死锁修复已在上游 [nss-packages PR #71](https://github.com/qosmio/nss-packages/pull/71)
合并。本项目直接使用上游现有修复，没有再叠加一份同功能补丁。
上游问题讨论中的个别加速能力判断不能直接套用：当前驱动确实包含 L2TPv2 路径，
但是否成功 offload 应以真机计数和日志为准。

## 真机验证与复现资料

连接 L2TP 后测试实际流量、断开重连及较长时间运行。区分两个结果：系统是否稳定、
L2TP 流量是否真正进入 NSS。仅看 CPU 占用不能确认 offload。

如果复现，保留以下信息；账号、密码和公网地址先脱敏：

```sh
ubus call system board
uname -a
lsmod | grep -E 'l2tp|ppp|nss|ecm'
logread | grep -Ei 'l2tp|ppp|nss|ecm|panic|stall|refcount'
dmesg
```

重点需要 panic/Oops 调用栈、RCU stall 前后的日志、L2TP 接口配置、是否经过 PPPoE、
IPv6、MTU/MRU，以及故障出现在首次连接、传输还是断线重连。
重启会丢失普通内存日志；可在电脑上保持 SSH `logread -f`，有条件时用串口保存内核输出。
