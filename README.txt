Various tools used for backups
==============================

Currently contains two utilities:

  1. tarbackup.py: Essentially a wrapper for gnu tar. It uses the incremental
     backup options, and makes a full backup every N days, where you can define
     how long such a cycle should be. Each backup goes in a uniquely named
     tarball for easier management. Never overwrites previous files.

  2. ftpsync.py: A tool that synchronises a local directory with one on an
     ftp server. Uses a very simple protocol of only checking file names
     and file sizes. File sizes are not allowed to change. Combined with
     tarbackup.py, this will essentially upload your tarballs to an ftp server,
     adding any new incremental or full backups that were created locally,
     and deleting any that were removed locally. FTP login details uses a
     conventional .netrc file in your home directory.

Use with zope/repozo
--------------------

ftpsync.py has been optimised to work with the zodb backup tool named repozo.
Because repozo also leaves old files unmodified, and only creates an
incremental file for whatever has changed since the previous backup, this fits
right in with our policy. The only exception is that repozo does update a .dat
file. To accomodate this, ftpsync.py has a --always option whereby you can
instruct it to always resync .dat files.

Example .netrc file
--------------------
machine ftpbackup.yourserver.tld login username password secret


Example shell script
--------------------

#!/bin/sh -e
SERVER="ftpbackup.yourserver.tld"

# /etc
/usr/bin/python /usr/bin/tarbackup.py --prefix=myserver_etc \
    --snapshot=/backups/snapshot --target=/backups/other /etc

# zope
sudo -u zope /path/to/zope/bin/repozo -BvzQ -f \
    "/path/to/zope/var/filestorage/Data.fs" -r /backups/zope

# Postgresql
stamp=`date +%s`
weekday=`date +%w`
sudo -u postgres pg_dumpall | gzip > /backups/pgsql/$weekday.$stamp.sql.gz
find "/backups/pgsql" -type f -name "$weekday.*.sql.gz" \
  -a -not -name "$weekday.$stamp.sql.gz" | xargs -r rm -f
  
/usr/bin/python /usr/bin/ftpsync.py --server $SERVER \
    --local /backups/other --remote other
/usr/bin/python /usr/bin/ftpsync.py --server $SERVER \
    --local /backups/zope --remote zope --always="*.dat"
/usr/bin/python /usr/bin/ftpsync.py --server $SERVER \
    --local /backups/pgsql --remote pgsql

# Notify nagios (passive check). This step will only be reached if nothing
# fails above, because sh is called with -e.
echo -e "myhost\tbacktup\tOK:completed" | \
  /usr/sbin/send_nsca -H monitor.host.tld -c /etc/send_nsca.cfg
