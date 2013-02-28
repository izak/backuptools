Various tools used for backups. Currently contains two utilities:

  1. tarbackup.py: Essentially a wrapper for gnu tar. It uses the incremental
     backup options, and makes a full backup every N days, where you can define
     how long such a cycle should be. Each backup goes in a uniquely named
     tarball for easier management. Never overwrites previous files.

  2. ftpsync.py: A tool that synchronises a local directory with one on an
     ftp server. Uses a very simple protocol of only checking file names
     and file sizes. File sizes are not allowed to change. Combined with
     tarbackup.py, this will essentially upload your tarballs to an ftp server,
     adding any new incremental or full backups that were created locally,
     and deleting any that were removed locally.
