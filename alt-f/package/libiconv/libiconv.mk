#############################################################
#
# libiconv
#
#############################################################
LIBICONV_VERSION = 1.12
LIBICONV_SOURCE = libiconv-$(LIBICONV_VERSION).tar.gz
LIBICONV_SITE = $(BR2_GNU_MIRROR)/libiconv
LIBICONV_AUTORECONF = NO
LIBICONV_INSTALL_STAGING = YES
LIBICONV_INSTALL_TARGET = YES
LIBICONV_INSTALL_TARGET_OPT = DESTDIR=$(TARGET_DIR) install

LIBICONV_DEPENDENCIES = uclibc

$(eval $(call AUTOTARGETS,package,libiconv))

# a patch in uClibc removes iconv.h. Added a patch to undo part of that patch

$(LIBICONV_HOOK_POST_INSTALL):
	# jc: added and now commented cp -f $(LIBICONV_DIR)/include/iconv.h.inst $(STAGING_DIR)/usr/include/iconv.h
	# jc: added and now commented chmod -w $(STAGING_DIR)/usr/include/iconv.h
	# Remove not used preloadable libiconv.so
	rm -f $(STAGING_DIR)/usr/lib/preloadable_libiconv.so
	rm -f $(TARGET_DIR)/usr/lib/preloadable_libiconv.so
ifneq ($(BR2_ENABLE_DEBUG),y)
	$(STRIPCMD) $(STRIP_STRIP_UNNEEDED) $(TARGET_DIR)/usr/lib/libiconv.so.*
	$(STRIPCMD) $(STRIP_STRIP_UNNEEDED) $(TARGET_DIR)/usr/lib/libcharset.so.*
endif
	touch $@
