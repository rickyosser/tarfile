"""Subset of cpython tarfile class methods needed to decode tar files."""

"""
This was shamelessly stolen from Micropython stdlib to be able to untar files in CircuitPython which does not support uctypes.

©2024 Bluapp AB, Rickard Osser <rickard.osser@bluapp.com>


"""

import struct

# Minimal set of tar header fields for reading.
# http://www.gnu.org/software/tar/manual/html_node/Standard.html
# The "size" entry is 11 (not 12) to implicitly cut off the null terminator.
'''
_TAR_HEADER = {
    "name": (0 :uctypes.ARRAY | 0, uctypes.UINT8 | 100),
    "size": (uctypes.ARRAY | 124, uctypes.UINT8 | 11),
}
'''

DIRTYPE = "dir"
REGTYPE = "file"

# Constants for TarInfo.isdir, isreg.
_S_IFMT = 0o170000
_S_IFREG = 0o100000
_S_IFDIR = 0o040000

_BLOCKSIZE = 512  # length of processing blocks


def _roundup(val, align):
    return (val + align - 1) & ~(align - 1)


class FileSection:
    def __init__(self, f, content_len, aligned_len):
        self.f = f
        self.content_len = content_len
        self.align = aligned_len - content_len

    def read(self, sz=65536):
        if self.content_len == 0:
            return b""
        if sz > self.content_len:
            sz = self.content_len
        data = self.f.read(sz)
        sz = len(data)
        self.content_len -= sz
        return data

    def readinto(self, buf):
        if self.content_len == 0:
            return 0
        if len(buf) > self.content_len:
            buf = memoryview(buf)[: self.content_len]
        sz = self.f.readinto(buf)
        self.content_len -= sz
        return sz

    def skip(self):
        sz = self.content_len + self.align
        if sz:
            while sz:
                s = min(sz, 16)
                buf = bytearray(s)
                self.f.readinto(buf)
                sz -= s

class TarInfo:
    def __init__(self, name=""):
        self.name = name
        self.mode = _S_IFDIR if self.name[-1] == "/" else _S_IFREG

    @property
    def type(self):
        return DIRTYPE if self.isdir() else REGTYPE

    def __str__(self):
        return "TarInfo(%r, %s, %d)" % (self.name, self.type, self.size)

    def isdir(self):
        return (self.mode & _S_IFMT) == _S_IFDIR

    def isreg(self):
        return (self.mode & _S_IFMT) == _S_IFREG


class TarFile:
    def __init__(self, name=None, mode="r", fileobj=None):
        self.subf = None
        self.mode = mode
        self.offset = 0
        if mode == "r":
            if fileobj:
                self.f = fileobj
            else:
                self.f = open(name, "rb")
        else:
            try:
                self._open_write(name=name, mode=mode, fileobj=fileobj)
            except AttributeError:
                raise NotImplementedError("Install tarfile-write")

    def __enter__(self):
        return self

    def __exit__(self, unused_type, unused_value, unused_traceback):
        self.close()

    def next(self):
        if self.subf:
            self.subf.skip()
        buf = self.f.read(_BLOCKSIZE)
        if not buf:
            return None

        name, mode, owner, group, size, time, checksum, link, link_name, rest = struct.unpack("<100s8s8s8s12s12s8sb100s255s", buf)
        
        # Empty block means end of archive
        if name[0] == 0:
            return None

        # Update the offset once we're sure it's not the run-out.
        self.offset += len(buf)
        d = TarInfo(name.decode('utf-8').rstrip("\0"))
        d.size = int(size[:-1].decode('utf-8'), 8)
        self.subf = d.subf = FileSection(self.f, d.size, _roundup(d.size, _BLOCKSIZE))
        self.offset += _roundup(d.size, _BLOCKSIZE)
        return d

    def __iter__(self):
        return self

    def __next__(self):
        v = self.next()
        if v is None:
            raise StopIteration
        return v

    def extractfile(self, tarinfo):
        return tarinfo.subf

    def close(self):
        try:
            self._close_write()
        except AttributeError:
            pass
        self.f.close()

    # Add additional methods to support write/append from the tarfile-write package.
    try:
        from .write import _open_write, _close_write, addfile, add
    except ImportError:
        pass

