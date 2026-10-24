include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-srun-autologin
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_LICENSE:=GPL-3.0-or-later
PKG_LICENSE_FILES:=LICENSE
PKG_MAINTAINER:=srun-autologin contributors

include $(INCLUDE_DIR)/package.mk

SRUN_VARIANT_aarch64:=aarch64
SRUN_VARIANT:=$(SRUN_VARIANT_$(ARCH))
SRUN_BINARY_SHA256:=04b46c45a5b83c9721b09962b5c0b2d31a03c26c81b928a5ac5ffa10d4ddb358

define Package/luci-app-srun-autologin
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=3. Applications
  TITLE:=LuCI support for srun campus network auto-login
  URL:=https://github.com/zu1k/srun
  DEPENDS:=@aarch64 +luci-base +rpcd +rpcd-mod-file +jshn +xz-utils +xz +ca-bundle +uclient-fetch
endef

define Package/luci-app-srun-autologin/description
 A procd connectivity watchdog and LuCI configuration page for automatic
 SRun/Deepin campus portal authentication. The matching static srun 0.6.2
 AArch64 binary is included for JDCloud RE-SS-01 (qualcommax/ipq60xx), so
 first-time authentication does not require Internet.
endef

define Package/luci-app-srun-autologin/conffiles
/etc/config/srun-autologin
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./LICENSE $(PKG_BUILD_DIR)/LICENSE
endef

define Build/Compile
	@test -n "$(SRUN_VARIANT)" || \
		( echo "This package is tailored for ARCH=aarch64 (JDCloud RE-SS-01)" >&2; false )
	@echo "$(SRUN_BINARY_SHA256)  $(CURDIR)/prebuilt/$(SRUN_VARIANT)/srun" | sha256sum -c -
endef

define Package/luci-app-srun-autologin/install
	$(INSTALL_DIR) $(1)/etc/config
	$(INSTALL_CONF) ./files/etc/config/srun-autologin $(1)/etc/config/srun-autologin
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/etc/init.d/srun-autologin $(1)/etc/init.d/srun-autologin
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) ./files/usr/bin/srun-autologin $(1)/usr/bin/srun-autologin
	$(INSTALL_BIN) ./prebuilt/$(SRUN_VARIANT)/srun $(1)/usr/bin/srun
	$(INSTALL_DIR) $(1)/usr/share/luci/menu.d
	$(INSTALL_DATA) ./files/usr/share/luci/menu.d/luci-app-srun-autologin.json \
		$(1)/usr/share/luci/menu.d/luci-app-srun-autologin.json
	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) ./files/usr/share/rpcd/acl.d/luci-app-srun-autologin.json \
		$(1)/usr/share/rpcd/acl.d/luci-app-srun-autologin.json
	$(INSTALL_DIR) $(1)/www/luci-static/resources/view/srun-autologin
	$(INSTALL_DATA) ./files/www/luci-static/resources/view/srun-autologin/config.js \
		$(1)/www/luci-static/resources/view/srun-autologin/config.js
endef

define Package/luci-app-srun-autologin/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
	chmod 0600 /etc/config/srun-autologin
	/etc/init.d/srun-autologin enable
	/etc/init.d/srun-autologin start
}
exit 0
endef

define Package/luci-app-srun-autologin/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
	/etc/init.d/srun-autologin disable
	/etc/init.d/srun-autologin stop
}
exit 0
endef

$(eval $(call BuildPackage,luci-app-srun-autologin))
