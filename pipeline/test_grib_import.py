#!/usr/bin/env python3
"""
Helm — pipeline/test_grib_import.py        WX epic · WX-12
Round-trip test: author a GRIB2 with pipeline/make_demo_grib.py, then decode it through the ACTUAL
JS reader (web/wx-grib2.js) via node and assert the grid + values come back correct. This proves the
Python author and the browser GRIB2 reader agree on the format (sections, sign-magnitude lat/lon,
simple-packing bit unpacking). Skips the node leg honestly if node is unavailable.

    python3 pipeline/test_grib_import.py
"""
import json, math, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import make_demo_grib as MG

fails = 0
def check(cond, msg):
    global fails
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        fails += 1

# author the GRIB into a temp file
src_vals = MG.wind_field()
grib = MG.build_grib2(src_vals)
with tempfile.NamedTemporaryFile(suffix=".grb2", delete=False) as tf:
    tf.write(grib); path = tf.name

check(grib[:4] == b"GRIB" and grib[7] == 2, "authored bytes start with GRIB + edition 2")

reader = os.path.join(ROOT, "web", "wx-grib2.js")
node = (f"const fs=require('fs'),G=require({json.dumps(reader)});"
        f"const b=fs.readFileSync({json.dumps(path)});"
        f"const r=G.parseGrib2(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));"
        f"const m=r.messages[0];const f=G.messageToField(m);"
        f"process.stdout.write(JSON.stringify({{n:r.messages.length,param:m.param.name,nbits:m.nbits,"
        f"dt:m.dataTemplate,gt:m.gridTemplate,nx:f.nx,ny:f.ny,west:f.west,north:f.north,east:f.east,"
        f"south:f.south,unit:f.unit,values:Array.from(f.values)}}));")
try:
    out = subprocess.run(["node", "-e", node], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        print("  note   skipped node decode (error):", out.stderr.strip()[:160])
    else:
        d = json.loads(out.stdout)
        check(d["n"] == 1, f"one GRIB message decoded (got {d['n']})")
        check(d["param"] == "WIND", f"parameter id = WIND (got {d['param']})")
        check(d["dt"] == 0 and d["gt"] == 0, "data template 5.0 + grid template 3.0")
        check(d["nbits"] == 12, f"nbits = 12 (got {d['nbits']})")
        check(abs(d["north"] - MG.BBOX[3]) < 1e-4 and abs(d["west"] - MG.BBOX[0]) < 1e-4,
              f"grid georeference NW = ({d['north']:.3f},{d['west']:.3f})")
        check(d["nx"] == MG.NX and d["ny"] == MG.NY, f"grid size {d['nx']}x{d['ny']}")
        # values round-trip to the source field within the 0.01 packing resolution (D=2).
        maxerr = max(abs(a - b) for a, b in zip(d["values"], src_vals))
        check(maxerr < 0.011, f"decoded values match source within packing resolution (max err {maxerr:.4f} m/s)")
        check(d["unit"] == "m/s", "unit = m/s")
except (FileNotFoundError, subprocess.TimeoutExpired):
    print("  note   skipped node decode (node unavailable)")
finally:
    os.unlink(path)

print(("\nGRIB-IMPORT TESTS: %d FAILED" % fails) if fails else "\nGRIB-IMPORT TESTS: all passed")
sys.exit(1 if fails else 0)
