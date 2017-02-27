#!/bin/sh

. common.sh
check_cookie
read_args

#debug

CONF_MISC=/etc/misc.conf

uscript=$(httpd -d "$user_script")

if test -n "$uscript"; then

	sdir=$(dirname $uscript)
	if ! find_mp "$sdir" >& /dev/null; then
		msg "The script must be on a filesystem such as /mnt/sda2 or /mnt/md0."
	fi
	
	mkdir -p "$sdir"
	httpd -d "$userscript" | dos2unix > $uscript
	chmod +x,og-wx "$uscript" 
fi

if test -z "$create_log"; then
	create_log="no"
fi

sed -i -e '/^USER_SCRIPT/d' -e '/^USER_LOGFILE/d' $CONF_MISC >& /dev/null
echo -e "USER_SCRIPT=\"$uscript\"\nUSER_LOGFILE=\"$create_log\" >> $CONF_MISC

#enddebug
gotopage /cgi-bin/user_services.cgi

