#!/usr/bin/env python

import sys
import os
import logging
import time
from optparse import OptionParser
from glob import glob

DEFAULTCYCLE = 7
DEFAULTPREFIX = "backup"

class BackupFailure(Exception):
    pass

def tarbackup(snapshot, destination, dirs, excludes):
    args = ["tar", "-z", "-c", "--listed-incremental", snapshot, "-f", destination]
    for exclude in excludes:
        args.append("--exclude=%s" % exclude)
    status = os.spawnvp(os.P_WAIT, args[0], args + dirs)
    if status == 2:
        # tar returns 2 for a critical failure
        raise BackupFailure("failed for arguments %s", " ".join(args))

def cleanup(path, pattern, exclude):
    includepattern = os.path.join(path, pattern)
    excludepattern = os.path.join(path, exclude)
    excluded_files = glob(excludepattern)
    files = [f for f in glob(includepattern) if f not in excluded_files]
    for f in files:
        logging.debug("Deleting %s" % f)
        os.remove(f)

def main():
    # option parsing
    usage = "%prog --prefix mybackupname --target /var/backup --snapshot dir dir1 [ dir2 ... ]"
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--prefix", help="A unique prefix for this backup",
                      default=DEFAULTPREFIX)
    parser.add_option("-t", "--target", help="Where to store the tarball files")
    parser.add_option("-s", "--snapshot", help="Where to store the snapshot files")
    parser.add_option("-c", "--cycle", help="Make a full backup this often (in days)",
                      default=DEFAULTCYCLE, type="int")
    parser.add_option("-e", "--exclude", help="Files to exclude from the backup",
                      default=[], action="append")
    parser.add_option("-v", "--verbose", action="count", help="Increase verbosity",
                      default=0)

    (options, args) = parser.parse_args()

    # Check all required parameters
    for option in (options.target, options.snapshot):
        if option is None:
            parser.print_help()
            sys.exit(1)

    # We need at least one thing to back up
    if len(args) < 1:
        parser.print_help()
        sys.exit(1)

    # Configure logging
    logging.basicConfig(level=max(4-options.verbose,1)*10)

    # Calculate filename and current cycle
    timestamp = int(time.time())
    rightnow = time.localtime(timestamp)
    currentcycle = rightnow[7] / options.cycle

    snapshotfile = "snapshot.%s.%03d" % (options.prefix, currentcycle)
    snapshotpath = os.path.join(options.snapshot, snapshotfile)

    targetfile = "%s.%03d.%d.tar.gz" % (options.prefix, currentcycle, timestamp)
    targetpath = os.path.join(options.target, targetfile)

    # Create paths if they do not exist
    for p in (options.snapshot, options.target):
        if not os.path.exists(p):
            os.makedirs(p)

    # Call tar to do the deed
    logging.info("Running tar backup for %s" % ", ".join(args))
    logging.info("snapshot at %s, destination at %s" % (snapshotpath, targetpath))
    tarbackup(snapshotpath, targetpath, args, options.exclude)

    # Cleanup
    logging.info("Cleaning up")
    cleanup(options.snapshot, "snapshot.%s.*" % options.prefix, snapshotfile)
    cleanup(options.target, "%s.*" % options.prefix,
        "%s.%03d.*.tar.gz" % (options.prefix, currentcycle))

if __name__ == '__main__':
    main()
