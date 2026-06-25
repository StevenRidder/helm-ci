# CONTRACT-7 — Channels / subscriptions + client-chosen nav rate

> **Status:** SHIPPED end-to-end. Client in [`web/nav-client.js`](../web/nav-client.js); server
> filtering + rate pacing + `sub.ack` in [`engine/vendor/cli/helm_server.cpp`](../engine/vendor/cli/helm_server.cpp)
> (CONTRACT touches it as a transport seam). Owned by **CONTRACT**. Verified by
> [`engine/contract-channels-smoke.js`](../engine/contract-channels-smoke.js) (client, 27 assertions) +
> [`engine/contract-channels-server-smoke.js`](../engine/contract-channels-server-smoke.js) (server
> end-to-end vs a running helm-server, 9 assertions). Gates **CONTRACT-8** (bbox-culled AIS).

## Why

One nav stream serves everything from a phone watching at anchor to a chartplotter underway. A client
should pay only for what it renders (bandwidth/battery over boat WiFi) and choose how fast it updates.
So the client **declares** the named channels it wants and a nav update **rate**; the server filters
frame content to the subscription and paces nav deltas to the rate.

## Channels

Named streams the client subscribes to. Known vocabulary (forward-compatible — unknown names are
forwarded with a warning):

| channel | frame content it gates |
|---|---|
| `nav` | core position/SOG/COG/HDG/depth/wind — **always subscribed, never droppable** (safety core) |
| `route` | active-route geometry + inspector (`active`, legs, ETA/DTG/XTE) |
| `alarms` | `t:"alarm"` / `alarm.clear` frames (CONTRACT-10) |
| `ais` | AIS targets array (`ais[]`) — the big one; bbox-culling rides this (CONTRACT-8) |
| `track` | own-ship breadcrumb trail |
| `conns` | per-connection live status |

A frame includes a channel's fields only if that channel is subscribed. **Absent `subscribe` ⇒ all
channels** (back-compat: a client that says nothing gets everything, as today).

## Nav rate

Integer **1–4 Hz**, the cadence the server emits nav `delta` frames at (keyframe/snapshot cadence and
the alarm/command planes are independent and **not** rate-paced — alarms are always immediate). The
client clamps out-of-range/non-numeric values and **surfaces** the coercion (fail-fast). **Absent
`rate` ⇒ the server default** (~1 Hz).

## Wire contract

**`hello`** (client → server, on connect/reconnect) — unchanged shape, two additive fields:
```json
{ "t": "hello", "lastSeq": 4810, "subscribe": ["nav","route","alarms","ais","track","conns"],
  "rate": 2, "lastAlarmAck": [ ... ] }
```
- `subscribe` — desired channels (always includes `nav`). Omit ⇒ all.
- `rate` — desired nav Hz (1–4). Omit ⇒ server default.

**`sub.update`** (client → server, runtime re-negotiation without reconnect):
```json
{ "t": "sub.update", "subscribe": ["nav","ais"], "rate": 3 }
```
Sent by `setRate()`/`subscribe()`/`unsubscribe()`. Send is false-tolerant — if the socket is down the
change still takes effect on the next `hello` (state persists), so it converges over a flaky link.

**`sub.ack`** (server → client) — the **effective** config the server applied (it MAY clamp the rate
or drop unavailable channels):
```json
{ "t": "sub.ack", "subscribe": ["nav","ais","conns"], "rate": 2 }
```
The client records it as `effective` and fires `opts.onSub(effective)`; it is **also** surfaced on the
command plane (`opts.onCommand`). It is **not** a nav frame — it never touches the age/staleness clock.

## Client API (`web/nav-client.js`)

```js
const c = HelmNavClient(applyNav, setSource, {
  subscribe: ['nav','ais','alarms'],   // optional; default = all known channels
  rate: 2,                              // optional; 1–4 Hz; default = server default
  onSub: eff => { /* eff = { subscribe:[...], rate } the server actually applied */ },
});
c.setRate(4);                 // → sends sub.update; returns the clamped desired rate
c.subscribe(['track']);       // add channels → sub.update; returns desired subscribe[]
c.unsubscribe(['ais']);       // remove channels ('nav' is refused) → sub.update
c.subscriptions();            // { desired:{subscribe,rate}, effective:{subscribe,rate}|null }
```

Desired state persists across reconnects (re-sent in `hello`). All sends are false-tolerant.

## Server implementation (`engine/vendor/cli/helm_server.cpp`)

Implemented onto the frozen contract (per-connection `ClientCfg` in `helm_server.cpp`):
1. **Parse `subscribe` + `rate`** from `hello` and `sub.update`; stored per-connection (keyed by the
   `ix::WebSocket*`, reconciled against live clients each tick). Absent `subscribe` ⇒ all channels;
   absent `rate` ⇒ default. `nav` is forced into every subscription (safety core).
2. **Filter frame content** by subscription — each channel is built once as a JSON fragment
   (`ais` / `conns` / `track` / `route`) and only spliced into a client's frame when subscribed; the
   `nav` core (pos/sog/cog/hdg/depth/wind/`active`) is always sent. (Note: the route *nav* fields ride
   the `nav` core; the `route` channel gates the route *geometry*.)
3. **Rate pacing** is per-client (`lastSentTick` + `everyN = NAV_SOURCE_HZ / rate`). **Effective rate
   is `min(requested, NAV_SOURCE_HZ)`** — and `NAV_SOURCE_HZ` is the ~1 Hz nav loop. The server
   **deliberately never streams faster than its data source**: upsampling would mean repeating or
   interpolating fixes, i.e. faking position between real samples — against Helm's honesty rule. So a
   client requesting 4 Hz honestly gets `sub.ack rate:1` today; wire a faster source/loop and higher
   effective rates follow with **no contract change**. (Snapshots/keyframes and the alarm/command
   planes are never rate-paced.)
4. **Reply `sub.ack`** with the effective `{subscribe, rate}` on `hello` and every `sub.update`.

**Remaining (additive):**
- **CONTRACT-8** narrows the `ais` channel to a client-supplied bbox (a `sub.update`/`hello` `bbox`
  field is the natural additive extension — the per-client `ClientCfg` is the place to hang it).
- A higher `NAV_SOURCE_HZ` (faster loop, time-based sim cadence) would make 2–4 Hz effective — only
  worth it with a sub-second-rate position source.
