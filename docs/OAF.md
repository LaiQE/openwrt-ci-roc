# OpenAppFilter

使用原作者 [destan19/OpenAppFilter](https://github.com/destan19/OpenAppFilter) master，实际提交记录在构建产物的 `build-sources.txt`。
按用户要求内置 `luci-app-oaf`、`appfilter`、同轮内核的 `kmod-oaf` 及中文翻译；不再另行生成独立实验归档。

## 默认状态与启用

全新刷机或恢复出厂后，LuCI「服务 → OAF行为管理 → 设置」中四项均为关闭：

| 界面选项 | UCI 配置 | 默认值 |
| --- | --- | --- |
| TCP连接重置 | `fwx.global.tcp_rst` | `0` |
| 开启应用过滤 | `fwx.appfilter.enable` | `0` |
| 启用上网控制 | `fwx.macfilter.enable` | `0` |
| 上网审计 → 启用 | `fwx.record.enable` | `0` |

管理后台 `appfilter` 仍自启，提供 LuCI/ubus 接口；这是用户选择的“功能关闭、界面可用”，不是禁用整个服务。
需要时在上述设置页打开对应功能并保存。现有配置升级及服务重启会保留用户主动启用的状态。
界面菜单未出现时可先清理浏览器缓存；初次实验中已确认此现象。

## 特征库

- 内置基础库：`/etc/fwxd/feature.bin`，保持来源原样，可在 LuCI「特征库」页在线切换版本。
- 自定义特征：`/etc/fwxd/custom_feature.cfg`，默认空文件；可在同一页面添加自定义特征。
- 「更新列表」仅获取可用版本，需在目标版本旁点击「切换」才会实际应用。

## NSS

用户在真机确认了 OAF 运行与 IPv4 NSS 加速共存；IPv6 NSS 加速未验证通过，已按用户要求停止排查。
在 LuCI「网络 → 防火墙」将「流量卸载类型」设为「无」，保存并应用；这不会关闭 NSS。
验证方法与上游来源见 [README](../README.md#luci-中的流量卸载设置) 和 [NSS 说明](NSS-CONSTRAINTS.md)。

OAF 的 `fwx.advanced.disable_hnat` 仍为上游默认的 `0`。若手动开启禁用加速，原作者脚本会将 ECM 的 `accel_delay_pkts` 提高到 1000000。
作者对 [NAT 卸载可能绕过 DPI 的说明](https://github.com/destan19/OpenAppFilter/issues/287)保留供参考；共存测试结果不替代对具体应用拦截规则的验证。
