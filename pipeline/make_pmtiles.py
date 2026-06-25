#!/usr/bin/env python3
"""
Helm — pipeline/make_pmtiles.py
--------------------------------------------------------------------------
Pack a directory of raster {z}/{x}/{y}.png tiles into a single PMTiles v3
archive, with no external tools (the canonical path uses `pmtiles convert`
from an .mbtiles — see make_pmtiles.sh — but that toolchain isn't always
present). Pure stdlib: Hilbert tile-id ordering + the v3 header/directory
byte layout per https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md

Usage: python3 pipeline/make_pmtiles.py web/data/relief web/data/key-west-sat.pmtiles
"""
import os, sys, glob, struct, gzip, json, math

# ---- varint (unsigned LEB128) ------------------------------------------
def uvarint(n):
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

# ---- Hilbert (z,x,y) -> tile id  (Wikipedia xy2d, full-side rotate) ------
def zxy_to_tileid(z, x, y):
    acc = 0
    for t in range(z):
        acc += (1 << t) * (1 << t)
    n = 1 << z
    d = 0
    s = n // 2
    while s > 0:
        rx = 1 if (x & s) > 0 else 0
        ry = 1 if (y & s) > 0 else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x = n - 1 - x
                y = n - 1 - y
            x, y = y, x
        s //= 2
    return acc + d

def serialize_directory(entries):
    """entries: sorted list of dicts {tile_id, offset, length, run_length}."""
    buf = bytearray()
    buf += uvarint(len(entries))
    last = 0
    for e in entries:
        buf += uvarint(e['tile_id'] - last)
        last = e['tile_id']
    for e in entries:
        buf += uvarint(e['run_length'])
    for e in entries:
        buf += uvarint(e['length'])
    for i, e in enumerate(entries):
        if i > 0 and e['offset'] == entries[i-1]['offset'] + entries[i-1]['length']:
            buf += uvarint(0)
        else:
            buf += uvarint(e['offset'] + 1)
    return bytes(buf)

def gz(b):
    return gzip.compress(b, mtime=0)

def main(src, out):
    paths = glob.glob(os.path.join(src, '*', '*', '*.png'))
    if not paths:
        print('no tiles under', src); sys.exit(1)
    tiles = []
    zs = set()
    for p in paths:
        z = int(os.path.basename(os.path.dirname(os.path.dirname(p))))
        x = int(os.path.basename(os.path.dirname(p)))
        y = int(os.path.splitext(os.path.basename(p))[0])
        zs.add(z)
        tiles.append((zxy_to_tileid(z, x, y), z, x, y, open(p, 'rb').read()))
    tiles.sort(key=lambda t: t[0])

    # concat tile data, dedup identical blobs
    data = bytearray()
    seen = {}
    entries = []
    for tid, z, x, y, blob in tiles:
        key = hash(blob)
        if key in seen:
            off, ln = seen[key]
        else:
            off, ln = len(data), len(blob)
            data += blob
            seen[key] = (off, ln)
        entries.append({'tile_id': tid, 'offset': off, 'length': ln, 'run_length': 1})

    root = gz(serialize_directory(entries))
    meta = gz(json.dumps({'name': os.path.basename(out),
                          'attribution': 'Helm offline relief pack — NOT FOR NAVIGATION'}).encode())

    HEADER = 127
    root_off = HEADER
    meta_off = root_off + len(root)
    leaf_off = meta_off + len(meta)
    leaf_len = 0
    data_off = leaf_off + leaf_len

    minz, maxz = min(zs), max(zs)
    # bounds from generator region (E7)
    minlon, minlat, maxlon, maxlat = -81.95, 24.38, -81.55, 24.66
    clon, clat = -81.77, 24.52

    h = bytearray(HEADER)
    h[0:7] = b'PMTiles'
    h[7] = 3
    struct.pack_into('<Q', h, 8, root_off)
    struct.pack_into('<Q', h, 16, len(root))
    struct.pack_into('<Q', h, 24, meta_off)
    struct.pack_into('<Q', h, 32, len(meta))
    struct.pack_into('<Q', h, 40, leaf_off)
    struct.pack_into('<Q', h, 48, leaf_len)
    struct.pack_into('<Q', h, 56, data_off)
    struct.pack_into('<Q', h, 64, len(data))
    struct.pack_into('<Q', h, 72, len(tiles))      # addressed tiles
    struct.pack_into('<Q', h, 80, len(entries))    # tile entries
    struct.pack_into('<Q', h, 88, len(seen))       # tile contents (unique)
    h[96] = 1   # clustered
    h[97] = 2   # internal compression: gzip
    h[98] = 1   # tile compression: none (PNG already compressed)
    h[99] = 2   # tile type: png
    h[100] = minz
    h[101] = maxz
    struct.pack_into('<i', h, 102, int(minlon * 1e7))
    struct.pack_into('<i', h, 106, int(minlat * 1e7))
    struct.pack_into('<i', h, 110, int(maxlon * 1e7))
    struct.pack_into('<i', h, 114, int(maxlat * 1e7))
    h[118] = (minz + maxz) // 2
    struct.pack_into('<i', h, 119, int(clon * 1e7))
    struct.pack_into('<i', h, 123, int(clat * 1e7))

    with open(out, 'wb') as f:
        f.write(bytes(h)); f.write(root); f.write(meta); f.write(bytes(data))
    print(f'wrote {out}: {len(tiles)} tiles ({len(seen)} unique), z{minz}-{maxz}, '
          f'{(HEADER+len(root)+len(meta)+len(data))/1024:.0f} KB')

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'web/data/relief'
    out = sys.argv[2] if len(sys.argv) > 2 else 'web/data/key-west-sat.pmtiles'
    main(src, out)
