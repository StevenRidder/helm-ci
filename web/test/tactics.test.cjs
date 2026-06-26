'use strict';
// tactics.test.cjs — pure opposite-tack maneuver math (web/tactics.js, HelmTactics.oppositeTack).
// twa is WX-13's signed true-wind angle (twa = twd − heading); twaSide 'S'/'P' = the side the wind is on.
const T = require('../tactics.js');
let pass = 0, fail = 0;
const ok = (c, m) => { console.log((c ? '  \x1b[32mPASS\x1b[0m  ' : '  \x1b[31mFAIL\x1b[0m  ') + m); c ? pass++ : fail++; };
const opp = T.oppositeTack;

ok((() => { const r = opp({ twd: 0, twa: 45, twaSide: 'S' });
  return r.maneuver === 'tack' && r.turn === 90 && r.turnSide === 'starboard' && r.newTack === 'port' && r.oppHeading === 45;
})(), '1. close-hauled stbd (45°) → TACK, head up 90° to stbd → 045°, onto port');

ok((() => { const r = opp({ twd: 0, twa: -120, twaSide: 'P' });   // the user's case
  return r.maneuver === 'gybe' && r.turn === 120 && r.turnSide === 'starboard' && r.newTack === 'starboard' && r.oppHeading === 240;
})(), '2. broad reach port (120°) → GYBE, bear away 120° to stbd → 240°, onto stbd (in-irons trap avoided)');

ok((() => { const r = opp({ twd: 0, twa: 120, twaSide: 'S' });
  return r.maneuver === 'gybe' && r.turn === 120 && r.turnSide === 'port' && r.newTack === 'port' && r.oppHeading === 120;
})(), '3. broad reach stbd (120°) → GYBE, bear away 120° to port → 120°, onto port');

ok((() => { const r = opp({ twd: 90, twa: 178, twaSide: 'S' }); return r.maneuver === 'gybe' && r.turn <= 8; })(),
  '4. near dead-run → GYBE, tiny turn');

ok((() => { const r = opp({ twd: 0, twa: 3, twaSide: 'S' }); return r && r.irons === true; })(),
  '5. ~head to wind → irons (no clean other tack)');

ok(opp(null) === null && opp({ twd: 0 }) === null, '6. missing wind → null');

ok((() => { const a = opp({ twd: 0, twa: 60, twaSide: 'S' }), b = opp({ twd: 0, twa: 150, twaSide: 'S' });
  return a.turn === 120 && a.maneuver === 'tack' && b.turn === 60 && b.maneuver === 'gybe';
})(), '7. turn = 2×off (tack) / 2×(180−off) (gybe)');

console.log('\n' + (fail ? '\x1b[31m' : '\x1b[32m') + 'tactics: ' + pass + ' passed, ' + fail + ' failed\x1b[0m');
process.exit(fail ? 1 : 0);
