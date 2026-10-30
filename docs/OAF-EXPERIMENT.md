# OpenAppFilter 独立实验包

这些 APK 只供用户手动实验，**没有预装到固件，也没有确认与 NSS 可靠兼容**。
来源为原作者 [destan19/OpenAppFilter](https://github.com/destan19/OpenAppFilter) 的 master；实际提交记录在同一轮产物的 `build-sources.txt`。

## 包与适用范围

- `luci-app-oaf`：LuCI 界面。
- `appfilter`：用户态服务和特征库。
- `kmod-oaf`：与同一轮固件一起编译的内核模块。
- 归档还包含中文翻译（若生成）及该轮固件尚未内置的必要依赖。
- 导出的 APK 已使用本轮构建密钥单独签名，匹配同轮固件中的公钥；不需要跳过签名检查。

**先烧录同一轮固件，再安装这些 APK**。归档开头标明架构与完整内核 ABI；旧固件或其它版本的内核不能仅凭同为 6.12 就混装。不要强制绕过内核依赖检查。

## 手动实验

解压归档并将 `OAF-experimental` 目录传至路由器，在该目录执行：

```sh
sha256sum -c SHA256SUMS
apk add ./*.apk
```

安装使用同轮固件的签名信任和依赖检查。若失败，保留报错，不使用 `--force-*` 跳过检查。
安装后检查 LuCI 的 OAF 页面和 `appfilter` 服务；首次配置沿用来源默认值，固件没有替你设置拦截规则。

## NSS 兼容边界

作者说明 [NAT 卸载可能绕过 OAF DPI](https://github.com/destan19/OpenAppFilter/issues/287)。
当前原作者实现的 `disable_hnat` 默认为 `0`；开启禁用加速选项时，`hnat.sh` 会将 ECM 的 `accel_delay_pkts` 提高到 1000000。
因此，界面出现应用记录或规则保存成功，不能证明对 NSS 已加速流量仍可可靠拦截。

通过有线管理路由器，分别验证目标应用被拦截、允许的应用正常、IPv4/IPv6、UDP/QUIC，以及连接建立后的策略变化。
同时记录 NSS/ECM 统计，区分“过滤有效”和“实际保留 NSS 加速”两个结果；详见 [NSS 配置说明](https://github.com/LaiQE/openwrt-ci-roc/blob/my/docs/NSS-CONSTRAINTS.md)。
本包没有添加自动关闭 NSS 或替换其驱动的定制逻辑；OAF 自身的禁用加速选项仍按来源实现。
