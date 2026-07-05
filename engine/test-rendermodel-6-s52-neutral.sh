#!/usr/bin/env bash
#
# RENDERMODEL-6: the s52plib presentation stage must emit neutral commands
# whose S-52 decisions survive export into helm.render.model.v1.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
FIXTURE="$HERE/test/fixtures/vulkan-render/s52-semantics"
TMP="${TMPDIR:-/tmp}/helm-rendermodel-6-s52-neutral.$$"

cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

mkdir -p "$TMP"
"$ROOT/scripts/render-model-fixture-export" "$FIXTURE" --output-dir "$TMP" >/dev/null

node - "$TMP/render-model.json" <<'NODE'
const fs = require('fs');
const path = process.argv[2];
const model = JSON.parse(fs.readFileSync(path, 'utf8'));

function fail(message) {
  throw new Error(message);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

function primitive(id) {
  for (const layer of model.layers || []) {
    for (const prim of layer.primitives || []) {
      if (prim.primitive_id === id) return prim;
    }
  }
  fail(`missing primitive ${id}`);
}

assert(model.schema_version === 'helm.render.model.v1', 'wrong render-model schema');
assert(model.display_state.palette === 'day', 'palette display state was not preserved');
assert(model.display_state.display_category === 'standard', 'display category was not preserved');
assert(model.display_state.use_scamin === true, 'SCAMIN policy was not preserved');
assert(model.display_state.use_super_scamin === false, 'SUPER_SCAMIN policy was not preserved');

const depare = primitive('cmd.area.depare-shoal');
assert(depare.source_trace.presentation_authority === 'opencpn.s52plib',
  'S-52 presentation authority must be explicit');
assert(depare.safety.display_category === 'displaybase',
  'command-level display category must override scene default');
assert(depare.safety.safety_class === 'shoal', 'DEPARE safety class was not preserved');

const buoy = primitive('cmd.symbol.boyspp-standard');
assert(buoy.scale.native_scale === 12000, 'native scale was not preserved');
assert(buoy.scale.scamin_max_scale === 50000, 'command SCAMIN max scale was not preserved');
assert(buoy.order.display_priority === 7, 'S-52 display priority was not preserved');
assert(buoy.order.source_sequence === 30, 'S-52 source sequence was not preserved');

const sounding = primitive('cmd.sounding.soundg-shoal');
assert(sounding.kind === 'Sounding', 'SOUNDG must export as a Sounding primitive');
assert(sounding.payload.formatted_text === '7.4', 'sounding formatted_text was not preserved');
assert(sounding.safety.safety_class === 'shoal', 'sounding safety class was not preserved');

const diagnostics = model.diagnostics || [];
assert(diagnostics.some((d) => d.code === 'semantic.culled' && /SCAMIN/.test(d.message)),
  'SCAMIN cull diagnostic was not preserved');

console.log(`ok rendermodel-6-s52-neutral: ${path}`);
NODE

BRIDGE="$ROOT/engine/vendor/cli/helm_s52_scene.cpp"
test -f "$BRIDGE" || { echo "missing helm_s52_scene.cpp bridge"; exit 1; }
grep -q 'ObjectRenderCheckRules' "$BRIDGE" || { echo "bridge must use s52plib ObjectRenderCheckRules"; exit 1; }
grep -q 'obj->CSrules' "$BRIDGE" || { echo "bridge must preserve conditional-symbology rules"; exit 1; }
grep -q 'opencpn.s52plib' "$BRIDGE" || { echo "bridge must mark OpenCPN presentation authority"; exit 1; }
grep -q 'opencpn_line_vbo' "$BRIDGE" || { echo "bridge must emit OpenCPN line geometry"; exit 1; }
grep -q 'opencpn_area_triangles' "$BRIDGE" || { echo "bridge must emit OpenCPN area triangles"; exit 1; }
grep -q 'opencpn_multipoint_soundings' "$BRIDGE" || { echo "bridge must emit OpenCPN sounding geometry"; exit 1; }
grep -q 'fixed_bbox' "$BRIDGE" || { echo "bridge must support same-area SCAMIN captures"; exit 1; }
grep -q 'S52_MAR_SAFETY_CONTOUR' "$BRIDGE" || { echo "bridge must expose OpenCPN safety contour state"; exit 1; }
grep -q 'S52_MAR_SAFETY_DEPTH' "$BRIDGE" || { echo "bridge must expose OpenCPN safety depth state"; exit 1; }
grep -q 'add_executable(helm-s52-scene' "$ROOT/engine/patches/0003-cli-cmakelists-helm-targets.patch" || { echo "helm-s52-scene target missing from CMake patch"; exit 1; }
grep -q 'helm-s52-scene' "$ROOT/engine/bootstrap.sh" || { echo "helm-s52-scene missing from bootstrap build"; exit 1; }
echo "ok rendermodel-6 bridge contract is wired"
