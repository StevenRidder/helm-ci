# Helm iOS WKWebView proof

`HelmWebViewProof` is the `NATIVE-2` proof shell. It is intentionally small:

- discovers the boat-side `helm-server` with Bonjour service type `_helm._tcp`;
- resolves the service host/port and reads `tls`, `name`, and `fp`/`fingerprint` TXT values when
  present;
- loads the existing Helm web UI in `WKWebView`;
- keeps the GPL/OpenCPN engine off the iPad/iPhone and speaks only HTTP/WebSocket through the web UI.

This is not the future SwiftUI/Metal chart client. It is a low-risk iPad proof that the current web
client can ride the boat-server contract before Helm invests in a native chart surface.

## Build

```sh
native/ios/build-ios-proof.sh
```

The script builds the app for an iOS Simulator SDK with signing disabled. It does not start or touch
the live Helm server on `:8080`.

## Run manually

1. Start a private Helm server, for example:

   ```sh
   scripts/start-helm.sh --port 9001
   ```

2. Open `native/ios/HelmWebViewProof.xcodeproj` in Xcode.
3. Run the `HelmWebViewProof` scheme on an iPad or iPhone simulator/device.
4. Use Bonjour discovery when a `_helm._tcp` service is visible, or the manual fallback
   `http://127.0.0.1:9001/` in Simulator.

The Info.plist scopes local-network permissions to Bonjour/local-network use. Plain HTTP is allowed
only for local-network development via `NSAllowsLocalNetworking`; the production path remains the
pinned-TLS/TOFU flow described in `docs/STREAMING-API.md`.
