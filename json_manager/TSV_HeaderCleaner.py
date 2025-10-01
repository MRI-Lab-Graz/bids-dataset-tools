#!/usr/bin/env python3
from pathlib import Path
import os, sys, struct

FEXTRA   = 0x04
FNAME    = 0x08
FCOMMENT = 0x10
FHCRC    = 0x02

def parse_gzip_header(f):
    h = f.read(10)
    if len(h) < 10 or h[0:2] != b"\x1f\x8b" or h[2] != 0x08:
        raise ValueError("Not a gzip member")
    flg = h[3]
    idx = 10
    # FEXTRA
    if flg & FEXTRA:
        xlen = struct.unpack("<H", f.read(2))[0]
        f.seek(xlen, os.SEEK_CUR)
        idx += 2 + xlen
    # FNAME
    if flg & FNAME:
        while f.read(1) not in (b"", b"\x00"):
            idx += 1
        idx += 1
    # FCOMMENT
    if flg & FCOMMENT:
        while f.read(1) not in (b"", b"\x00"):
            idx += 1
        idx += 1
    # FHCRC
    if flg & FHCRC:
        f.seek(2, os.SEEK_CUR)
        idx += 2
    return h, idx

def clean_member(inf, outf):
    orig, data_start = parse_gzip_header(inf)
    # neuen "neutralen" Header schreiben
    new_header = bytearray(10)
    new_header[0:3] = b"\x1f\x8b\x08"    # magic + method
    new_header[3]   = 0x00               # flags cleared
    new_header[4:8] = b"\x00\x00\x00\x00"  # mtime=0
    new_header[8]   = orig[8]            # extra flags
    new_header[9]   = orig[9]            # os
    outf.write(new_header)

    # Rest 1:1 kopieren
    inf.seek(data_start, os.SEEK_SET)
    while True:
        chunk = inf.read(1024 * 1024)
        if not chunk:
            break
        outf.write(chunk)

def clean_gzip_file(path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(path, "rb") as inf, open(tmp, "wb") as outf:
        clean_member(inf, outf)
    os.replace(tmp, path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 clean_gzip_headers.py /path/to/rawdata")
        sys.exit(1)
    root = Path(sys.argv[1])
    targets = [p for p in root.rglob("*.tsv.gz") if "func" in p.parts]
    for p in targets:
        print(f"Fixing {p}")
        try:
            clean_gzip_file(p)
        except Exception as e:
            print(f"  -> skipped: {e}")

if __name__ == "__main__":
    main()
