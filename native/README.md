# Helm native core

`native/` is the App-Store-clean client-side C++ seam for Helm native clients. It is deliberately
not the OpenCPN engine and deliberately does not include `engine/vendor`, `wxWidgets`, OpenCPN
headers, chart rendering, serial drivers, or networking.

The boat still owns safety-critical navigation in the C++ `helm-server` process. Native Apple
clients link this small core to consume the documented HTTP/WebSocket protocol:

- snapshot/delta nav-state reduction from `docs/STREAMING-API.md`;
- explicit LIVE/LAGGING/STALE/OFFLINE age classification;
- TOFU/pairing trust metadata storage shape from `CONTRACT-14`;
- no transport/channel implementation yet, so NATIVE-1 depends on the core protocol, not channel
  optimization.

That boundary keeps GPL/wx/OpenCPN code out of iOS/iPadOS clients while still letting every client
share the same deterministic reducer and safety-state rules.

## Build

```sh
./native/test-native-core.sh
```

Or directly:

```sh
cmake --preset macos-debug -S native
cmake --build --preset macos-debug
ctest --test-dir native/build/macos-debug --output-on-failure
```

Apple static-library presets are provided for the first native compile gate:

```sh
cmake --preset ios-simulator-release -S native
cmake --build --preset ios-simulator-release
cmake --preset iphoneos-release -S native
cmake --build --preset iphoneos-release
```

The iOS presets build only `libhelm_native_core.a`; tests remain macOS-hosted.

## iOS WKWebView proof shell

`native/ios/` contains the `NATIVE-2` proof app. It does not reimplement the chart client and does
not embed the GPL/OpenCPN engine. It discovers a boat-side `helm-server` advertised as `_helm._tcp`
over Bonjour, then loads the existing Helm web UI in a `WKWebView`.

```sh
native/ios/build-ios-proof.sh
```

That script builds the iOS Simulator app with signing disabled. It does not start any Helm runtime
or touch the shared live `:8080` instance.
