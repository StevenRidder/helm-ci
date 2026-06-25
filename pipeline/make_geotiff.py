#!/usr/bin/env python3
"""
Helm — pipeline/make_geotiff.py
--------------------------------------------------------------------------
Author a small georeferenced single-band float32 GeoTIFF of the depth field,
for the cog:// integration (maplibre-cog-protocol / geotiff.js). No GDAL: we
write a baseline little-endian TIFF + the GeoTIFF tags (ModelPixelScale,
ModelTiepoint, GeoKeyDirectory=EPSG:4326) by hand.

The production path is `gdal_translate -of COG in.tif out.tif` on a real GRIB/
DEM (cloud-optimized = internal tiling + overviews + range reads). This file is
a single-strip baseline GeoTIFF — geotiff.js reads it the same way for a small
static overlay; swap it for a true COG when GDAL is in the pipeline.

EPSG:4326, NaN = no data. NOT FOR NAVIGATION (synthetic field).
"""
import os, struct, math

from gen_demo_data import elevation, BBOX

W = H = 256
OUT = os.path.join(os.path.dirname(__file__), '..', 'web', 'data', 'key-west-depth.tif')

def build():
    minlon, minlat, maxlon, maxlat = BBOX
    sx = (maxlon - minlon) / W
    sy = (maxlat - minlat) / H
    # pixel grid, row 0 = north (maxlat)
    pix = bytearray()
    for j in range(H):
        lat = maxlat - (j + 0.5) * sy
        for i in range(W):
            lon = minlon + (i + 0.5) * sx
            pix += struct.pack('<f', float(elevation(lon, lat)))

    entries = []  # (tag, type, count, value_or_offset, is_inline, raw_external)
    BYTE, ASCII, SHORT, LONG, RATIONAL, FLOAT, DOUBLE = 1, 2, 3, 4, 5, 11, 12

    # external data blocks get laid out after the IFD
    ext = bytearray()
    ext_base = None  # filled later

    def short_inline(v):  return (SHORT, 1, v, True, None)
    def long_inline(v):   return (LONG, 1, v, True, None)

    # GeoKeyDirectory: version,rev,minor,numkeys + per-key (id,loc,count,value)
    geo_keys = [1, 1, 0, 3,
                1024, 0, 1, 2,      # GTModelTypeGeoKey = 2 (geographic)
                1025, 0, 1, 1,      # GTRasterTypeGeoKey = 1 (PixelIsArea)
                2048, 0, 1, 4326]   # GeographicTypeGeoKey = WGS84
    geo_raw = b''.join(struct.pack('<H', v) for v in geo_keys)
    pixscale_raw = struct.pack('<3d', sx, sy, 0.0)
    tiepoint_raw = struct.pack('<6d', 0, 0, 0, minlon, maxlat, 0.0)

    # tags in ASCENDING order (TIFF requirement)
    tags = [
        (256, short_inline(W)),
        (257, short_inline(H)),
        (258, short_inline(32)),                 # BitsPerSample
        (259, short_inline(1)),                  # Compression = none
        (262, short_inline(1)),                  # Photometric = BlackIsZero
        (273, ('STRIP_OFF',)),                   # StripOffsets (filled later)
        (277, short_inline(1)),                  # SamplesPerPixel
        (278, short_inline(H)),                  # RowsPerStrip
        (279, long_inline(W * H * 4)),           # StripByteCounts
        (284, short_inline(1)),                  # PlanarConfig
        (339, short_inline(3)),                  # SampleFormat = IEEE float
        (33550, ('EXT', DOUBLE, 3, pixscale_raw)),
        (33922, ('EXT', DOUBLE, 6, tiepoint_raw)),
        (34735, ('EXT', SHORT, len(geo_keys), geo_raw)),
    ]

    n = len(tags)
    ifd_off = 8
    ifd_size = 2 + n * 12 + 4
    ext_off = ifd_off + ifd_size
    # place external blocks, remember offsets
    cur = ext_off
    placed = {}
    for tag, spec in tags:
        if spec[0] == 'EXT':
            _, typ, count, raw = spec
            placed[tag] = cur
            ext += raw
            cur += len(raw)
            if len(raw) % 2:  # word align
                ext += b'\x00'; cur += 1
    strip_off = cur  # image data right after external blocks

    # serialize IFD
    out = bytearray()
    out += b'II' + struct.pack('<HI', 42, ifd_off)
    assert len(out) == 8
    ifd = bytearray()
    ifd += struct.pack('<H', n)
    for tag, spec in tags:
        if spec[0] == 'STRIP_OFF':
            ifd += struct.pack('<HHII', tag, LONG, 1, strip_off)
        elif spec[0] == 'EXT':
            _, typ, count, raw = spec
            ifd += struct.pack('<HHII', tag, typ, count, placed[tag])
        else:
            typ, count, val, inline, _ = spec
            # inline value left-justified in the 4-byte field
            if typ == SHORT:
                ifd += struct.pack('<HHIHH', tag, typ, count, val, 0)
            else:  # LONG
                ifd += struct.pack('<HHII', tag, typ, count, val)
    ifd += struct.pack('<I', 0)  # next IFD = 0
    assert len(ifd) == ifd_size, (len(ifd), ifd_size)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(out)            # header (8)
        f.write(ifd)            # IFD
        f.write(ext)            # external tag data
        # pad to strip_off if needed
        here = 8 + len(ifd) + len(ext)
        if here < strip_off:
            f.write(b'\x00' * (strip_off - here))
        f.write(pix)            # image data
    print(f'wrote {OUT}: {W}x{H} float32 EPSG:4326, strip@{strip_off}, '
          f'{(strip_off + len(pix))/1024:.0f} KB')

if __name__ == '__main__':
    build()
