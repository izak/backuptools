#!/usr/bin/env python

import sys
import os
import struct
import logging
from hashlib import sha256
from optparse import OptionParser

try:
    from Crypto.Cipher import AES
    HAS_CRYPTO=True
except ImportError:
    HAS_CRYPTO=False

class DecryptedFile(object):
    """ Wrapper object that takes a file object, decrypts it using AES. File
        should be prepended with the text bkptools, followed by 8 bytes for the
        file size. """
    def __init__(self, key, iv, fp):
        self.crypter = AES.new(key, AES.MODE_CBC, iv)
        self.fp = fp

        # Read the file header, check that this is one of ours and retrieve
        # the file size
        head = struct.unpack('<QQ', fp.read(16))
        assert struct.pack('<Q', head[0]) == 'bkptools', \
            "Not a backuptools file"
        self.filesize = head[1]

    def read(self):
        # blocksize needs to be a multiple of 16.
        blocksize = 8192
        block = self.fp.read(blocksize)

        # Check for EOF
        if not block:
            return ''

        decrypted = self.crypter.decrypt(block)
        self.filesize -= len(decrypted)

        # Check for last padded block. If self.filesize becomes less than
        # zero, it means the input was not a multiple of 16 and we padded some
        # zeroes onto the file. Strip those off now.
        if self.filesize < 0:
            return decrypted[:self.filesize]

        return decrypted

    def close(self):
        # Truncate to size on closing
        self.fp.close()

def main(args):
    # option parsing
    usage = "%prog --key keyfile filename"
    parser = OptionParser(usage=usage)
    parser.add_option("-k", "--key",
        help="key file for AES decryption. "
             "The last 16 characters of the file name is used as the IV, "
             "padded with nulls if the filename is less than 16 characters")
    parser.add_option("-v", "--verbose", action="count",
        help="Increase verbosity", default=0)

    (options, args) = parser.parse_args()
    if options.key is None:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    if options.key and not HAS_CRYPTO:
        print >>sys.stderr, "pycrypto not available"
        sys.exit(1)

    # Configure logging
    logging.basicConfig(level=max(4-options.verbose,1)*10)

    # Decrypt the file and spit it out to stdout
    f = args[0]
    key = open(options.key, 'r').read()
    iv = os.path.basename(f)[-16:].ljust(16, '\0')
    fp = DecryptedFile(sha256(key).digest(), iv, open(f, "r"))
    block = fp.read()
    while block:
        sys.stdout.write(block)
        block = fp.read()
    fp.close()

if __name__ == '__main__':
    main(sys.argv)
