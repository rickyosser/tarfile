'''
©2024 Bluapp AB, Rickard Osser <rickard.osser@bluapp.com>

Example of python-script to untar a tar file on a CircuitPython implementation.
'''

import sys
import os
import tarfile
import storage

# Check if directory already exits
def dir_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) != 0
    except OSError:
        return False
# Check if file already exists        
def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


# Re-mount the CircuitPython disk as read-write
# The disk can't be mounted on the computer while doing this operation
storage.remount("/", readonly=False)

# Enter filename of tar-file stored on the CircuitPython disk
testfile = "<tar-file>"


t = tarfile.TarFile(testfile)
for i in t:
    if i.type == tarfile.DIRTYPE:
        if(not dir_exists(i.name)):
            os.mkdir(i.name)
    else:
        f = t.extractfile(i)
        with open(i.name, "wb") as of:
            of.write(f.read())

# Re-mount the CircuitPython disk as read-only (default)
storage.remount("/", readonly=True)
