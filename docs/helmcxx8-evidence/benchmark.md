# HELMC++-5 Benchmark And Soak

Generated: 2026-07-05T00:05:28.326Z
Ports: core=9410 packd=9411 cache=9412 envd=9413 relay=9414
Pass: true

## Cold Start
- helm-packd: 31.6 ms
- helm-basemap-cache: 103.7 ms
- helm-envd: 103.7 ms
- helm-server: 309 ms

## First Visible Runtime Data
- chart layer proxy: 36.9 ms
- environmental layer proxy: 1.1 ms

## Soak
- mode: short
- seconds: 900
- requests: 4395
- errors: 0

## Baseline
- status: baseline_missing
