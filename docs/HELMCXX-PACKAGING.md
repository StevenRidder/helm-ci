# HELMC++ packaging and install proof

Status: HELMC++-6 packaging proof for the boat-side C++ runtime.

This document proves the install shape for the required C++ runtime. It is
separate from the NATIVE-13 macOS DMG, which packages the thin `HelmMac` client
and deliberately does not bundle OpenCPN, wxWidgets, or the boat server.

## Acceptance claim

The supported boat-runtime install path is:

1. build the C++ runtime with `engine/bootstrap.sh`;
2. install the built binaries, web cockpit, and durable S-52/tide assets with
   `scripts/install-helmcxx-runtime.sh`;
3. supervise the installed binaries with either the checked-in `systemd` units or
   the checked-in `launchd` plists;
4. put user-owned ENC, MBTiles/PMTiles, and environmental packs in deterministic
   runtime directories;
5. run smoke checks on private ports before enabling a live boat port.

The install path does not require Docker, a Python daemon, a virtual
environment, or build output left under a temporary checkout. Python may still be
used by developer/test/offline-bake tooling as allowed by
`docs/HELMCXX-ACCEPTANCE.md`; it is not part of the supervised runtime path here.

## Deterministic directories

The default install directories are intentionally conventional and boring:

| Path | Purpose |
|---|---|
| `/opt/helm/bin` | Installed C++ runtime binaries: `helm-server`, `helm-packd`, `helm-envd`, `helm-basemap-cache`. |
| `/opt/helm/web` | Static browser cockpit served by `helm-server`. |
| `/etc/helm` | Runtime config and generated `helm-runtime.env`. |
| `/var/lib/helm/runtime` | Durable runtime assets such as `s57data`, `tcdata`, and user-installed ENC cells. |
| `/var/lib/helm/data` | User-owned overlays and generated data exposed through `/user-data/`. |
| `/var/cache/helm` | Regenerable SENC, tide, basemap-fill, tile, and service caches. |
| `/var/log/helm` | Runtime logs for supervised services. |
| `/srv/helm/packs` | User-owned MBTiles/PMTiles packs served by `helm-packd`. |
| `/srv/helm/wx-packs` | Baked `helm.env.grid.v1` environmental pack releases for `helm-envd`. |

For CI and local review, `scripts/install-helmcxx-runtime.sh --staging-root
<dir>` prepends a staging root to every destination while preserving the target
paths in the generated runtime environment. That is how the proof can verify the
install shape without requiring root privileges.

## macOS fresh-machine path

Install prerequisites and build:

```sh
brew install wxwidgets@3.2 gpatch cmake libarchive libusb libsndfile mpg123 lame openssl@3 gdal node
engine/bootstrap.sh --smoke
scripts/install-sample-enc.sh
```

Install the C++ runtime:

```sh
sudo scripts/install-helmcxx-runtime.sh
```

Install launchd supervision:

```sh
sudo install -m 0644 packaging/launchd/com.6thelement.helm-server.plist /Library/LaunchDaemons/
sudo install -m 0644 packaging/launchd/com.6thelement.helm-packd.plist /Library/LaunchDaemons/
sudo install -m 0644 packaging/launchd/com.6thelement.helm-envd.plist /Library/LaunchDaemons/
sudo install -m 0644 packaging/launchd/com.6thelement.helm-basemap-cache.plist /Library/LaunchDaemons/

sudo launchctl bootstrap system /Library/LaunchDaemons/com.6thelement.helm-server.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/com.6thelement.helm-packd.plist
```

`helm-envd` and `helm-basemap-cache` are installed but not `RunAtLoad` by
default in launchd. Enable them only after the boat has local environmental packs
or online-fill/cache policy configured.

Smoke:

```sh
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/catalog
curl -fsS http://127.0.0.1:8091/catalog

sudo launchctl bootout system /Library/LaunchDaemons/com.6thelement.helm-packd.plist
sudo launchctl bootout system /Library/LaunchDaemons/com.6thelement.helm-server.plist
```

For public macOS distribution, the thin native client follows
`native/macos/package-macos-dmg.sh --notarize`. The boat-side runtime remains a
separate process/package with GPL/OpenCPN source and notice obligations. A
signed runtime installer package is allowed, but it must keep this process
separation and pass the same smoke checks before any release claim.

## Linux and Raspberry-Pi-style path

Install toolchain and dependencies through the target distro packages, then build
with the same source path:

```sh
engine/bootstrap.sh --smoke
scripts/install-sample-enc.sh
sudo useradd --system --home /var/lib/helm --shell /usr/sbin/nologin helm || true
sudo scripts/install-helmcxx-runtime.sh
sudo chown -R helm:helm /etc/helm /var/lib/helm /var/cache/helm /var/log/helm /srv/helm
```

Install systemd supervision:

```sh
sudo install -m 0644 packaging/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now helm-server.service helm-packd.service
```

`helm-envd.service` is gated by `/etc/helm/helm-envd-manifests.env`, which should
define `HELM_ENV_GRID_MANIFESTS` after environmental packs are baked and copied
under `/srv/helm/wx-packs`. `helm-basemap-cache.service` is optional for
online-fill or remote-pack cache policy.

Smoke:

```sh
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/catalog
curl -fsS http://127.0.0.1:8091/catalog
sudo systemctl stop helm-packd.service helm-server.service
```

## Proof command

The cheap CI-safe proof is:

```sh
scripts/helmcxx-packaging-proof.sh
```

It verifies the install script, service templates, deterministic directories, and
the absence of Docker/Python/temp-path runtime dependencies in the packaging
artifacts. It also stages a fake install tree and confirms the generated runtime
environment contains target paths rather than build-machine paths.

After a real `engine/bootstrap.sh`, run the fuller smoke:

```sh
scripts/helmcxx-packaging-proof.sh --run-smoke
```

That installs the real C++ binaries into a staging root, starts `helm-server` and
`helm-packd` on private ports, checks `/health`, core `/catalog`, local pack
`/catalog`, and shuts the processes down cleanly. It never uses the shared
`:8080` screen.

## Upgrading a running install

Replace runtime binaries **atomically** — never overwrite a running/mmap'd binary
in place. On macOS, a plain in-place `cp` over a binary that is currently running
(or was, and is still mapped by a supervisor's respawn) poisons the kernel's
cached code signature for that file's vnode; every subsequent `exec` is then
killed with `OS_REASON_CODESIGNING` (symptom: processes stuck in uninterruptible
`UE` state, 0 CPU, empty log, unkillable until reboot — even though `codesign -v`
reports the on-disk file as valid). `scripts/install-helmcxx-runtime.sh` does this
correctly: it copies to a temp path beside the destination and `mv`s it into place,
giving the destination a fresh inode.

Stop the service through its supervisor before (or after) the swap, and restart it
through the supervisor rather than launching a second copy by hand — a manual
launch races a `KeepAlive`/`Restart=always` respawn, and two concurrent chart
inits on the same runtime state wedge both. On systemd:

```sh
sudo systemctl stop helm-server.service
sudo scripts/install-helmcxx-runtime.sh
sudo systemctl start helm-server.service
```

On a launchd-managed macOS install, restart with
`launchctl kickstart -k gui/$(id -u)/<label>` rather than a manual `nohup`.
