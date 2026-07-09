#!/usr/bin/env python3
"""ENC depth extract fallback when ogr2ogr is unavailable (uses pyogrio + geopandas)."""
import json
import os
import sys
import time

os.environ.setdefault(
    'OGR_S57_OPTIONS',
    'SPLIT_MULTIPOINT=ON,ADD_SOUNDG_DEPTH=ON,RETURN_PRIMITIVES=OFF,RETURN_LINKAGES=OFF,LNAM_REFS=OFF',
)

from pyogrio import read_dataframe, write_dataframe  # noqa: E402

enc = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/.helm/data')
cell = os.path.splitext(os.path.basename(enc))[0]
os.makedirs(out, exist_ok=True)

for layer, name in [('DEPARE', 'depare'), ('DEPCNT', 'depcnt'), ('SOUNDG', 'soundg')]:
    gdf = read_dataframe(enc, layer=layer)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    write_dataframe(gdf, os.path.join(out, f'{name}.geojson'), driver='GeoJSON')
    print(f'{name}: {len(gdf)} features')

prov = {
    'schema': 'helm.depth_provenance.v1',
    'source': 'enc',
    'cell': cell,
    'enc_path': os.path.abspath(enc),
    'enc_mtime': int(os.path.getmtime(enc)),
    'extracted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
}
with open(os.path.join(out, 'depth-provenance.json'), 'w', encoding='utf-8') as f:
    json.dump(prov, f, indent=2)
    f.write('\n')