#!/usr/bin/env python

import sys
import os
import struct
import logging
from hashlib import sha256
from ftplib import FTP, error_perm
from netrc import netrc
from optparse import OptionParser
from fnmatch import fnmatch

try:
    from Crypto.Cipher import AES
    HAS_CRYPTO=True
except ImportError:
    HAS_CRYPTO=False

class EncryptedFile(object):
    """ Wrapper object that takes a file object, encrypts it using AES. File
        is prepended with th e text bkptools, followed by 8 bytes for the file
        size. To get back the file size, decrypt the first 16 bytes of the file
        using: struct.unpack('<QQ', bytes) and use the second number of the
        tuple. """
    def __init__(self, key, iv, fp):
        self.crypter = AES.new(key, AES.MODE_CBC, iv)
        self.fp = fp

        fp.seek(0, os.SEEK_END)
        self.filesize = fp.tell()
        fp.seek(0)

        self.firstblock = True

    def read(self, blocksize=-1):
        # blocksize needs to be a multiple of 16. The default passed by
        # ftplib (8192) is a multiple of 16. If you override it, make sure your
        # block is also a multiple of 16. Otherwise this will break.

        # The first block of the file is 16 bytes indicating the size
        if self.firstblock:
            self.firstblock = False
            return 'bkptools' + struct.pack('<Q', self.filesize)

        block = self.fp.read(blocksize)
        if not block:
            return ''

        # Pad block up to 16 bytes if necessary
        l = len(block) & 15
        if l:
            padding = (16-l) * '\0'
            block += padding
            
        return self.crypter.encrypt(block)

    def close(self):
        self.fp.close()

def ftp_login(host):
    login, account, password = netrc().authenticators(host)
    server = FTP(host)
    server.login(login, password, account)
    return server

def cd_or_mkdir(server, subdir=None):
    if subdir:
        try:
            server.cwd(subdir)
        except error_perm:
            server.mkd(subdir)
            server.cwd(subdir)


def list_remote_files(server):
    files = server.nlst('.')
    files = [x for x in files if x not in ('.', '..')]
    files.sort()
    return files

def list_local_files(dir):
    files = os.listdir(dir)
    files.sort()
    return files


def check_backup(server, localpath, files, encryption=False):
    # Make sure we are in binary mode
    server.voidcmd("TYPE I")
    for f in files:
        status = os.stat(os.path.join(localpath, f))
        localsize = status.st_size
        remotesize = server.size(f)

        # If encryption is in use, the remote file must be larger than the
        # local one at the very least
        if encryption:
            assert localsize <= remotesize, f
            continue

        # This will cause the process to quit if the sizes mismatch, and
        # the return status will be 1.
        assert localsize == remotesize, f

def main(args):
    # option parsing
    usage = "%prog --server ftp.host.com --local /var/backup --remote backup"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--server",
        help="hostname:[port], hostname and optional port for ftp server")
    parser.add_option("-l", "--local",
        help="local path to backup")
    parser.add_option("-r", "--remote",
        help="remote path to backup to, without leading /")
    parser.add_option("-a", "--always",
        help="files that should always be copied/overwritten")
    parser.add_option("-k", "--key",
        help="key file for AES encryption, if you want to use encryption. "
             "The last 16 characters of the file name is used as the IV, "
             "padded with nulls if the filename is less than 16 characters")
    parser.add_option("-v", "--verbose", action="count",
        help="Increase verbosity", default=0)

    (options, args) = parser.parse_args()
    for option in (options.server, options.local):
        if option is None:
            parser.print_help()
            sys.exit(1)

    if options.key and not HAS_CRYPTO:
        print >>sys.stderr, "pycrypto not available"
        sys.exit(1)

    # Configure logging
    logging.basicConfig(level=max(4-options.verbose,1)*10)

    logging.info("Logging on to %s", options.server)
    server = ftp_login(options.server)
    logging.info("Changing/creating %s" % options.remote)
    cd_or_mkdir(server, options.remote)

    # Get a list of remote files
    logging.info("Obtaining list of files in %s" % (options.remote or "."))
    remote_files = list_remote_files(server)

    # Get a list of local files
    logging.info("Obtaining list of files in %s" % options.local)
    tmplist = list_local_files(options.local)

    # Filter out directories
    local_files = []
    for f in tmplist:
        if os.path.isdir(os.path.join(options.local, f)):
            logging.warn("Cannot handle directory %s" % f)
        else:
            local_files.append(f)

    # Calculate what to upload and delete
    logging.info("Calculating difference")
    to_upload = [f for f in local_files if \
                    f not in remote_files \
                    or options.always and fnmatch(f, options.always)]
    to_delete = [f for f in remote_files if f not in local_files]
    logging.info("%d new files on local end" % len(to_upload))
    logging.info("%d files to delete on remote end" % len(to_delete))

    # Delete files removed locally
    for f in to_delete:
        logging.debug("Deleting %s" % f)
        server.delete(f)

    # Copy new files
    for f in to_upload:
        logging.debug("Storing %s" % f)
        fp = open(os.path.join(options.local, f), "r")
        if options.key:
            key = open(options.key, 'r').read()
            iv = f[-16:].ljust(16, '\0')
            fp = EncryptedFile(sha256(key).digest(), iv, fp)
        server.storbinary('STOR %s' % f, fp)
        fp.close()

    # Now check the backup
    logging.info("Checking the backup")
    check_backup(server, options.local, local_files,
        encryption=(options.key is not None))

    server.quit()

if __name__ == '__main__':
    main(sys.argv)
