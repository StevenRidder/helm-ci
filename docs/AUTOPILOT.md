# Helm Autopilot Control

> Scope: read pilot state, stage skipper-approved pilot commands, and adapt those commands to
> supported marine data paths. This is a control surface, not a generic dashboard feature.

## Safety Boundary

Helm's rule is simple:

- AIS, AI, alarms, and routing may advise.
- Only the `PILOT` epic may turn advice into a pilot command.
- Only an owner-role skipper may approve a motion-affecting command.

No v1 flow lets AIS or AI directly steer the boat. The first collision-avoidance target is
manual approval: Helm can compute and preview a maneuver, but the skipper confirms before the
server emits anything to the pilot.

Every pilot command must be source-honest and fail closed:

- reject commands when heading, position, route, or pilot state is stale/offline;
- reject view-only clients;
- log every staged, accepted, rejected, timed-out, and emitted command;
- preserve physical standby/override as the highest-priority escape path;
- field-test only on private ports and never from the live `:8080` screen.

## Supported Lanes

### 1. Read-only pilot state

First land the harmless path: detect and display pilot state without transmitting control frames.
The widget should show mode, current heading, target heading, rudder angle when available, active
source, and freshness. It can render as a dedicated Pilot panel and later as a Smart Board tile.

Expected inputs include Signal K autopilot paths, NMEA 0183/NMEA 2000-derived state, and
gateway-specific fields when they are clearly source-tagged.

### 2. Standard route or heading output

The first write-capable lane is standard marine output for route-following and heading intent.
B&G NAC-class autopilot computers document NMEA 0183 route/heading inputs such as APB, RMB, BOD,
BWC, and HSC, plus NMEA 2000 network integration. Helm should treat this as the cleanest
operational path: send route/heading intent, then let the installed pilot computer decide whether
it can engage or follow it.

This lane belongs behind the guarded `pilot.*` command contract. The adapter may emit Signal K,
NMEA 0183, or NMEA 2000 output only when that transport is explicitly configured and validated.

### 3. B&G/Navico proprietary course-change spike

The exact `+1/-1/+10/-10` button behavior appears technically feasible on B&G/Simrad/Navico
systems via reverse-engineered SimNet/NMEA 2000 proprietary command traffic. CANboat documents
Navico/SimNet autopilot command variants, including course-change commands with direction and
angle, commonly 1 or 10 degrees.

That evidence is promising, but it is not a vendor-supported contract for a shipped safety feature.
The Helm task is a hardware spike:

- capture the real boat bus while pressing the physical `+1`, `-1`, `+10`, `-10`, standby, and
  auto/nav controls;
- compare captures against the reverse-engineered PGNs;
- bench-test with the drive disengaged before any underway test;
- keep the adapter feature-flagged and device/firmware-specific until validated.

## AIS Maneuver Approval

AIS/CPA can propose an evasive maneuver, but it cannot actuate it directly.

The intended flow is:

1. AIS advisor computes a suggested alteration and reason.
2. Pilot UI stages the command with current heading, proposed target heading, freshness, and
   expected CPA effect.
3. The skipper explicitly confirms.
4. `PILOT` emits the command through the guarded adapter.
5. Helm records the command outcome and keeps a visible cancel/standby path.

Armed auto-assist, where Helm could act without a fresh confirmation, is a later product and
liability decision. It is not part of the v1 `PILOT` plan.

## Ownership

`PILOT` owns pilot semantics: state model, command schema, safety interlocks, approval UI, audit
log, and adapters that turn canonical commands into configured marine outputs.

`BOARD` may show pilot tiles and automation prompts, but it does not own pilot command semantics.
`CONN` owns connection plumbing. `CONTRACT` owns the shared command-plane and auth boundary.
`AIS` owns the maneuver recommendation. `PILOT` owns the approval and actuation bridge.

## Plan Board Mapping

- `PILOT-1` - read-only pilot state model and widget.
- `PILOT-2` - guarded `pilot.*` command contract.
- `PILOT-3` - standard Signal K/NMEA route and heading output adapter.
- `PILOT-4` - B&G/Navico proprietary `+1/-1/+10/-10` course-change spike.
- `PILOT-5` - route-follow / steer-to-waypoint approval UI.
- `PILOT-6` - AIS/CPA maneuver approval bridge.
- `PILOT-7` - safety interlocks, audit log, and self-test.

`BOARD-7` remains only the dashboard tile or automation surface for already-safe PILOT actions.

## Research References

- B&G NAC-3 product/spec page: NMEA 0183 input and NMEA 2000 network integration for
  autopilot computers. <https://www.bandg.com/bg/type/autopilots/autopilot-computers/nac-3-autopilot-computer/>
- CANboat NMEA 2000 reverse-engineering notes: Navico/SimNet autopilot status and command PGNs,
  including course-change commands. <https://canboat.github.io/canboat/canboat.html>
