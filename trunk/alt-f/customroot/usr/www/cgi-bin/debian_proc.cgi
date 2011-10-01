#!/bin/sh

cleanup() {
	echo "</pre><h4>An error has occurred, cleaning up.</h4>$(back_button)</body></html>"
	clean
	exit 0
}

clean() {
	rm -f data.tar.gz cdebootstrap-static_0.5.4_armel.deb

	for i in $filelist; do
		if test -f /$i; then
			rm -f /$i >& /dev/null
		fi
	done

	for i in $(echo $filelist | tr ' ' '\n' | sort -r); do
		if test -d /$i; then
			rmdir /$i  >& /dev/null
		fi
	done
}

. common.sh
check_cookie
read_args

#debug

if test -z "$part" -o "$part" = "none"; then
	msg "You have to specify the filesystem where to install Debian"
fi

DEBDEV=$part
DEBDIR=/mnt/$DEBDEV 

if ! test -d "$DEBDIR"; then
	DEBDIR="$(awk '/'$part'/{print $2}' /proc/mounts)"
fi

if test "$submit" = "Install"; then

	if test -z "$mirror" -o "$mirror" = "none"; then
		msg "You have to specify a mirror near you in order to download Debian"
	fi

	DEBMIRROR=$(httpd -d $mirror)

	if test -f $DEBDIR/boot/vmlinuz-*-orion5x -a -f $DEBDIR/boot/initrd.img-*-orion5x; then
		msg "Debian is already installed in this filesystem."
	fi

	write_header "Installing Debian"

	echo "<small><h4>Downloading installer...</h4><pre>"

	cd /tmp
	wget --progress=dot:binary $DEBMIRROR/pool/main/c/cdebootstrap/cdebootstrap-static_0.5.4_armel.deb
	if test $? != 0; then cleanup; fi

	echo "</pre><h4>Extracting installer...</h4><pre>"

	ar x cdebootstrap-static_0.5.4_armel.deb data.tar.gz
	if test $? != 0; then cleanup; fi

	filelist=$(tar -tzf data.tar.gz)
	tar -C / -xzf data.tar.gz
	if test $? != 0; then cleanup; fi

	echo "</pre><h4>Downloading and installing Debian, this might take some time...</h4><pre>"

	mkdir -p $DEBDIR 
	cdebootstrap-static --allow-unauthenticated --arch=armel \
		--include=linux-image-2.6.32-5-orion5x,openssh-server,kexec-tools,mdadm \
		squeeze $DEBDIR $DEBMIRROR
	if test $? != 0; then cleanup; fi

	echo "</pre><h4>Debian installed successfully.</h4>"

	echo "<h4>Updating packages....</h4><pre>"

	chroot $DEBDIR /usr/bin/apt-get update

	if mdadm --detail --test /dev/$DEBDEV >& /dev/null; then

		echo "</pre><h4>Adding RAID boot support....</h4><pre>"

		mount -o bind  /proc $DEBDIR/proc
		mount -o bind  /sys  $DEBDIR/sys
		mount -o bind  /dev  $DEBDIR/dev

		chroot $DEBDIR /usr/sbin/update-initramfs -u

		umount $DEBDIR/proc
		umount $DEBDIR/sys
		umount $DEBDIR/dev
	fi

	ver=$(cat /etc/Alt-F)
	echo "</pre><h4>Downloading and installing Alt-F $ver in Debian...</h4><pre>"
	
	wget --progress=dot:mega http://alt-f.googlecode.com/files/Alt-F-${ver}.tar 
	if test $? != 0; then cleanup; fi
	tar -xf Alt-F-${ver}.tar
	if test $? != 0; then cleanup; fi
	mv alt-f/rootfs.arm.cpio-sq.lzma $DEBDIR/boot/Alt-F-rootfs.arm.cpio-sq.lzma
	mv alt-f/zImage $DEBDIR/boot/Alt-F-zImage
	rm -rf alt-f Alt-F-${ver}.tar 

	echo "</pre><h4>Setting up some Debian installation details...</h4>"
	
	echo "<p>Enabling serial port acess..."

	sed -i 's/^[1-6]:/#&/' $DEBDIR/etc/inittab
	echo "T0:1235:respawn:/sbin/getty -n -l /bin/bash -L ttyS0 115200 vt100" >> $DEBDIR/etc/inittab

	echo "<p>Changing Debian the message of the day..."

	echo -e "\nYou leaved Alt-F, you are now on your own.\nTo return to Alt-F, execute the command 'alt-f',\n" >> $DEBDIR/etc/motd.tail

	echo "<p>Using same ssh host key as Alt-F is using now..."

	for i in ssh_host_dsa_key ssh_host_rsa_key ssh_host_dsa_key.pub ssh_host_rsa_key.pub; do
		mv $DEBDIR/etc/ssh/$i $DEBDIR/etc/ssh/${i}-orig
	done

	dropbearconvert dropbear openssh /etc/dropbear/dropbear_rsa_host_key $DEBDIR/etc/ssh/ssh_host_rsa_key 
	dropbearconvert dropbear openssh /etc/dropbear/dropbear_dss_host_key $DEBDIR/etc/ssh/ssh_host_dsa_key
	chmod og-rw $DEBDIR/etc/ssh/*
	chown root $DEBDIR/etc/ssh/*

	echo "<p>Setting root password the same as Alt-F web admin password..."

	chroot $DEBDIR /bin/bash -c "/bin/echo root:$(cat /etc/web-secret) | /usr/sbin/chpasswd"
	if test $? != 0; then cleanup; fi

if false; then # not working
	echo "<p>Predate runlevel 4 to perform an Alt-F kexec, using runlevel 6 initscripts..."

 	(
	cd $DEBDIR/etc/rc4.d
	rm *
	for i in ../rc6.d/*; do
		ln -s $i $(basename $i)
	done
	)

	rm $DEBDIR/etc/rc4.d/K01kexec-load
	cp $DEBDIR/etc/init.d/kexec-load $DEBDIR/etc/rc4.d/K01kexec-load
	sed -i 's|default/kexec|default/kexec-alt-f|g' $DEBDIR/etc/rc4.d/K01kexec-load

	rm $DEBDIR/etc/rc4.d/K09kexec
	cp $DEBDIR/etc/init.d/kexec $DEBDIR/etc/rc4.d/K09kexec
	sed -i 's|default/kexec|default/kexec-alt-f|g' $DEBDIR/etc/rc4.d/K09kexec

	cp $DEBDIR/etc/default/kexec $DEBDIR/etc/default/kexec-alt-f
	sed -i -e 's|^KERNEL_IMAGE.*|KERNEL_IMAGE="/boot/Alt-F-zImage"|' \
		-e 's|^INITRD.*|INITRD="/boot/Alt-F-rootfs.arm.cpio-sq.lzma"|' \
		$DEBDIR/etc/default/kexec-alt-f

	cat<<-EOF > $DEBDIR/usr/sbin/alt-f
		#!/bin/bash
		init 4
	EOF
	chmod +x $DEBDIR/usr/sbin/alt-f
else
	cp $DEBDIR/etc/default/kexec $DEBDIR/etc/default/kexec-debian
	cp $DEBDIR/etc/default/kexec $DEBDIR/etc/default/kexec-alt-f
	sed -i -e 's|^KERNEL_IMAGE.*|KERNEL_IMAGE="/boot/Alt-F-zImage"|' \
		-e 's|^INITRD.*|INITRD="/boot/Alt-F-rootfs.arm.cpio-sq.lzma"|' \
		$DEBDIR/etc/default/kexec-alt-f
	cat<<-EOF > $DEBDIR/usr/sbin/alt-f
		#!/bin/bash
		cp /etc/default/kexec-alt-f /etc/default/kexec
		reboot
	EOF
	chmod +x $DEBDIR/usr/sbin/alt-f
fi

	clean

	echo "<h4>Success.</h4>"
	cat<<-EOF
		<script type="text/javascript">
			setTimeout(function() {window.location.assign(document.referrer);}, 5000)
		</script>
	EOF
	exit 0

elif test "$submit" = "Uninstall"; then

	html_header
	echo "<h3><center>Uninstalling Debian...</center></h3>"
	busy_cursor_start

	for i in bin boot dev etc home initrd.img lib media mnt opt proc root sbin selinux \
			srv sys tmp usr var vmlinuz; do
		echo "Removing $DEBDIR/$i...<br>"
		rm -rf $DEBDIR/$i >& /dev/null
	done

	busy_cursor_end
	cat<<-EOF
		<script type="text/javascript">
			window.location.assign(document.referrer)
		</script></body></html>
	EOF

elif test "$submit" = "Execute"; then

	part=/dev/$(basename $DEBDIR)

	html_header 
	echo "<h3><center>Executing Debian...</center></h3><pre>"

	debian -kexec
	
	echo "</pre><h4>failed.</h4> $(back_button)</body></html>"
fi

#enddebug
