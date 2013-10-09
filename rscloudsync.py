#!/usr/bin/env python
import sys
import pyrax
from netrc import netrc
from optparse import OptionParser
import logging

def main():
    # option parsing
    usage = "%prog --local /var/backup --remote backup"
    parser = OptionParser(usage=usage)
    parser.add_option("-i", "--identity", default="rackspace",
        help="Pyrax identity class")
    parser.add_option("-l", "--local", help="local path to backup")
    parser.add_option("-r", "--remote", help="remote container to backup to")
    parser.add_option("-v", "--verbose", action="count",
        help="Increase verbosity", default=0)

    (options, args) = parser.parse_args()
    for option in (options.local, options.remote):
        if option is None:
            parser.print_help()
            sys.exit(1)

    # Get login details from .netrc.
    login, account, password = netrc().authenticators(
        'pyrax.%s' % options.identity)

    # Configure logging
    logging.basicConfig(level=max(4-options.verbose,1)*10)

    logging.info("Logging on to %s", options.identity)
    pyrax.set_setting("identity_type", options.identity)
    pyrax.set_credentials(login, password)

    logging.info("Synchronising")
    pyrax.cloudfiles.sync_folder_to_container(
        options.local, options.remote, delete=True, ignore_timestamps=True)


if __name__ == '__main__':
    main()
