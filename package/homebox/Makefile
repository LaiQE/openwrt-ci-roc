include $(TOPDIR)/rules.mk

PKG_NAME:=homebox
PKG_VERSION:=0.1.3
PKG_RELEASE:=1

# Official static musl release: no second Rust/Node toolchain is needed.
PKG_SOURCE:=homebox-$(PKG_VERSION)-linux-arm64-musl.tar.gz
PKG_SOURCE_URL:=https://github.com/XGHeaven/homebox/releases/download/v$(PKG_VERSION)/
PKG_SOURCE_URL_FILE:=homebox-linux-arm64-musl.tar.gz
PKG_HASH:=793c5c273e09155b7ac35c23dd0638afefa5f9d453b6350b8bd8e0ca0d87c9e9

include $(INCLUDE_DIR)/package.mk

define Package/homebox
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=Web Servers/Proxies
  TITLE:=Home network speed test
  URL:=https://github.com/XGHeaven/homebox
  DEPENDS:=@aarch64
endef

define Package/homebox/conffiles
/etc/config/homebox
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(HOST_TAR) -xzf $(DL_DIR)/$(PKG_SOURCE) -C $(PKG_BUILD_DIR)
endef

define Build/Compile
endef

define Package/homebox/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/etc/config $(1)/etc/init.d
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/homebox-linux-arm64-musl $(1)/usr/bin/homebox
	$(INSTALL_CONF) ./files/homebox.config $(1)/etc/config/homebox
	$(INSTALL_BIN) ./files/homebox.init $(1)/etc/init.d/homebox
endef

$(eval $(call BuildPackage,homebox))
