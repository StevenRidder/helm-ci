# RENDERMODEL-6: S-52 Compiler To Neutral Commands

RENDERMODEL-6 replaces the production capture path that currently depends on
GDAL-derived approximate command streams. The target is a headless OpenCPN
`s52plib` presentation stage that emits `helm.render.model.v1` semantics before
any WebGPU, Vulkan, VSG, or raster backend sees the scene.

## Boundary

`s52plib` owns:

- object visibility, including display category, mariner category, and no-show
  decisions;
- SCAMIN and native-scale filtering;
- conditional symbology output;
- safety depth, safety contour, sounding class, and danger class decisions;
- text and sounding formatting before backend glyph work;
- S-52 display priority and source order.

The render backend owns:

- batching;
- buffers;
- atlas or glyph resource binding;
- target framebuffer/tile output.

The backend must not reinterpret S-57 object classes, SCAMIN, display category,
safety contours, conditional symbology, or sounding text.

## Command Contract

The production `s52plib` bridge should emit `vulkan.render_scene.v0`
`scene.commands.json` records with command-level `s52_semantics`. The exporter
now treats those fields as authoritative when converting to
`helm.render.model.v1`.

Required command-level fields:

```json
{
  "s52_semantics": {
    "presentation_authority": "opencpn.s52plib",
    "source_object_id": "BOYSPP-123",
    "object_class": "BOYSPP",
    "display_category": "standard",
    "display_priority": 7,
    "native_scale": 12000,
    "scamin_max_scale": 50000,
    "safety_class": "aid_to_navigation",
    "order_key": [1, 1, 7, 3, 30]
  }
}
```

Text and soundings must be emitted as data commands:

- `draw_text` carries `text`, `font_ref`, position, placement hints, and
  provenance.
- `draw_sounding` carries `formatted_text`; downstream backends must not
  reformat depth values.

Culled objects are not emitted as draw primitives. Debug captures should keep a
diagnostic with `code: "semantic.culled"`, a provenance ref, and the explicit
reason such as `scamin` or `display_category`.

## Current Guard

The current repository guard is:

```bash
engine/test-rendermodel-6-s52-neutral.sh
```

It exports the existing `s52-semantics` fixture and fails if the neutral model
loses:

- OpenCPN presentation authority;
- display category;
- SCAMIN native/max-scale fields;
- S-52 order keys;
- safety classes;
- sounding `formatted_text`;
- SCAMIN cull diagnostics.

This is not the full OpenCPN instrumentation. It is the narrow contract the
headless `s52plib` bridge must satisfy before the GDAL capture path can be
retired for production real-cell rendering.

## OpenCPN Bridge

The maintained OpenCPN overlay now includes:

```bash
engine/vendor/cli/helm_s52_scene.cpp
```

Bootstrap wires this as `helm-s52-scene`, linked against the same
`ocpn::chart-render` library used by `helm-tiles`. The CLI loads a real ENC
through OpenCPN, performs a headless no-text render warm-up, walks the resolved
`s57chart::razRules`, and calls `s52plib::ObjectRenderCheckRules` before
emitting neutral `vulkan.render_scene.v0` commands. If OpenCPN generated
conditional-symbology rules during the warm-up, the bridge emits those
`obj->CSrules` commands as part of the same object stream.

Example after `engine/bootstrap.sh`:

```bash
~/.helm/build/helm-opencpn/build/cli/helm-s52-scene \
  ~/.helm/runtime/enc/US5GA2BC/US5GA2BC.000 \
  --z 13 --x 2182 --y 3263 \
  --palette day --category standard \
  --out /tmp/us5ga2bc-z13.scene.commands.json
```

For same-area semantic proof, the bridge also accepts an explicit geographic
bbox with an independent display-scale denominator:

```bash
~/.helm/build/helm-opencpn/build/cli/helm-s52-scene \
  ~/.helm/runtime/enc/US5GA2BC/US5GA2BC.000 \
  --bbox -81.5625,30.751277776257798,-81.38671875,30.90222470517145 \
  --scale-denom 14645.89479670859 \
  --palette day --category standard \
  --out /tmp/us5ga2bc-z15-same-area.scene.commands.json
```

The bridge preserves object class, display category, SCAMIN/native scale,
display priority, source order, CS expansion, safety contour/depth display
state, text/sounding instructions, and cull diagnostics. It also emits
target-space geometry from OpenCPN's resolved objects:

- line commands carry `polyline` points from the OpenCPN line VBO;
- area commands carry tessellated `triangles` from `PolyTessGeo`;
- symbol and text commands carry object-derived target positions;
- sounding commands carry per-sounding positions, depths, and formatted text.

The area shape is currently emitted as triangles, not reconstructed contour
rings. That is intentionally honest: it is the geometry OpenCPN already draws
and is directly consumable by a neutral backend.

## US5GA2BC Evidence

Current local evidence from the OpenCPN bridge, using the private bootstrap
build and no live `:8080` runtime:

| Probe | Result |
| --- | --- |
| z13 Standard/day tile `13/2241/3357` | PNG reference served by private `helm-server` on port `9096`: HTTP 200, `X-Helm-Renderer: legacy`, 256x256 PNG, 60,153 bytes. Matching neutral capture: 893 visited, 120 visible, 773 culled, 153 commands, 59 CS-expanded objects. |
| Same bbox SCAMIN at z11-equivalent scale `234334.3167` | 376 visible objects, 460 commands, 376 `scamin` cull diagnostics. |
| Same bbox SCAMIN at z13-equivalent scale `58583.57919` | 376 visible objects, 460 commands, 376 `scamin` cull diagnostics. |
| Same bbox SCAMIN at z15-equivalent scale `14645.8948` | 623 visible objects, 798 commands, zero `scamin` cull diagnostics, 250 sounding points. |
| Display category toggle, same z15-equivalent bbox | displaybase: 380 visible / 460 commands; standard: 623 visible / 798 commands; other: 755 visible / 934 commands. |
| Safety contour toggle, same z15-equivalent bbox | 3 m: 623 visible / 798 commands; 10 m: 599 visible / 774 commands; command signatures changed without recompiling the ENC. |

The z13 PNG reference is a legacy s52plib raster render. The neutral capture
uses the same ENC, display state, and OpenCPN/s52plib rule path, then records
the resolved objects and commands for backend consumption.
