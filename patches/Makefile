include $(TOPDIR)/rules.mk

ARCH:=aarch64
BOARD:=qualcommax
BOARDNAME:=Qualcomm Atheros 802.11ax WiSoC-s
FEATURES:=squashfs ramdisk fpu nand rtc emmc
KERNELNAME:=Image
CPU_TYPE:=cortex-a53
SUBTARGETS:=ipq807x ipq60xx ipq50xx

KERNEL_PATCHVER:=6.12

include $(INCLUDE_DIR)/target.mk
DEFAULT_PACKAGES += \
	autocore automount cpufreq e2fsprogs f2fsck mkf2fs losetup luci uboot-envtools wpad-openssl \
	kmod-dsa kmod-dsa-qca8k kmod-fs-ext4 kmod-fs-f2fs kmod-gpio-button-hotplug kmod-leds-gpio \
	kmod-ath11k kmod-ath11k-ahb kmod-ath11k-pci kmod-phy-aquantia kmod-phy-marvell kmod-phy-qca83xx \
	kmod-usb3 kmod-usb-dwc3 kmod-usb-dwc3-qcom kmod-qca-nss-dp \
	kmod-qca-nss-drv kmod-qca-nss-crypto \
	kmod-qca-nss-drv-bridge-mgr \
	kmod-qca-nss-drv-eogremgr \
	kmod-qca-nss-drv-gre \
	kmod-qca-nss-drv-igs \
	kmod-qca-nss-drv-lag-mgr \
	kmod-qca-nss-drv-map-t \
	kmod-qca-nss-drv-match \
	kmod-qca-nss-drv-mirror \
	kmod-qca-nss-drv-pptp \
	kmod-qca-nss-drv-qdisc \
	kmod-qca-nss-drv-tun6rd \
	kmod-qca-nss-drv-tunipip6 \
	kmod-qca-nss-drv-vlan-mgr \
	kmod-qca-nss-drv-vxlanmgr \
	kmod-qca-nss-drv-wifi-meshmgr \
	kmod-qca-nss-drv-l2tpv2 \
	kmod-qca-nss-drv-pppoe \
	# kmod-qca-nss-ecm\

$(eval $(call BuildTarget))
