# Helm Clean-room Symbol Proof Package

This directory is the public proof surface for the generated Helm maritime symbol package.

Open `compare-opencpn.html` after running the Forge proof generators. The page loads
`package-proof-data.json` and renders each row with:

- OpenCPN comparison images where available.
- Helm S-57 generated day/dusk/night renders.
- Helm S-101 trace/render evidence where available.
- Committed Helm SVG palette assets where available.
- Runtime gate reasons and remediation hints.

The page does not approve runtime use. Runtime export is blocked by the FORGE-47 gate until every row has the required proof, provenance, and approval.
