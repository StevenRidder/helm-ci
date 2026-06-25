// HelmAisRisk — single source of truth for AIS collision-risk tiers + palette across the app.
//
// "Is this target dangerous?" was previously defined SIX different ways with three threshold
// families: the CPA alarm (cpa<2.0 & tcpa<30), the tap-card popup and AIS list and moored-suppression
// guard (cpa<0.5 / cpa<1.5), and the chart symbol colour (cpa-only <0.2 / <0.5). So one vessel the
// CPA ALARM was firing on could read red on the chart-vector overlay, only "Caution" in the tap card
// and list, and a plain BLUE symbol on the chart. On safety software that is unacceptable.
//
// Now every surface routes through this module:
//   • JS:        tier(t) / isDanger(t) / color(t)
//   • MapLibre:  dangerExpr() / riskColorExpr()  (data-driven equivalents, built from the SAME
//                constants so a chart layer can never drift from the JS sites)
// DANGER == the CPA alarm's predicate EXACTLY (cpa < g_CPAWarn_NM && 0 < tcpa < g_TCPA_Max), so a
// target the alarm fires on is red EVERYWHERE. CAUTION is a wider pre-alarm "watch" band; the engine
// blesses neither caution nor normal — they are a UI gradient, not an engine assertion.
//
// AUTHORITATIVE & FORWARD-COMPATIBLE: cpa/tcpa/cpaValid come from the engine and are never recomputed
// here. If the engine ever emits a per-target `risk` string, tier() and the expressions PREFER it —
// so the thresholds can later move into the core that already owns g_CPAWarn_NM/g_TCPA_Max without
// touching a single client.
(function (global) {
  'use strict';

  var CPA_WARN = 2.0, TCPA_MAX = 30.0;          // == engine g_CPAWarn_NM / g_TCPA_Max (the alarm band)
  var CPA_CAUTION = 4.0, TCPA_CAUTION = 60.0;   // pre-alarm "watch" band — 2x the alarm horizon
  // Canonical palette in ONE place. danger/caution/normal for the risk tiers; lost/sart for the
  // symbology overrides (a SART is always distress-pink; a lost/aged target is always grey).
  var COL = { danger: '#ff5a52', caution: '#f5c451', normal: '#5bc0ff', lost: '#7d8a98', sart: '#ff3b8b' };

  function n(v) { return (v == null || v === '') ? null : (isFinite(+v) ? +v : null); }

  // tier(t) → 'danger' | 'caution' | 'normal', from the engine's authoritative cpa/tcpa.
  function tier(t) {
    if (!t) return 'normal';
    if (t.risk === 'danger' || t.risk === 'caution' || t.risk === 'normal') return t.risk;   // engine wins
    if (t.cpaValid === false || t.cpaValid === 'false') return 'normal';      // no valid CPA solution
    var cpa = n(t.cpa); if (cpa == null) return 'normal';
    var tcpa = n(t.tcpa);
    if (tcpa == null) return cpa < CPA_WARN ? 'caution' : 'normal';           // no tcpa: can't assert closing → cap at caution
    if (tcpa <= 0) return 'normal';                                           // opening / past CPA — not a threat
    if (cpa < CPA_WARN && tcpa < TCPA_MAX) return 'danger';                  // == the CPA alarm exactly
    if (cpa < CPA_CAUTION && tcpa < TCPA_CAUTION) return 'caution';
    return 'normal';
  }
  function isDanger(t) { return tier(t) === 'danger'; }
  function color(t) { return COL[tier(t)] || COL.normal; }

  // ---- MapLibre data-driven expressions, built from the SAME constants (read raw feature props) ----
  // Boolean: is this feature in the danger band? Mirrors isDanger() / the alarm.
  function dangerExpr() {
    return ['any',
      ['==', ['get', 'risk'], 'danger'],
      ['all',
        ['!=', ['get', 'cpaValid'], false],
        ['<', ['coalesce', ['get', 'cpa'], 99], CPA_WARN],
        ['>', ['coalesce', ['get', 'tcpa'], -999], 0],
        ['<', ['coalesce', ['get', 'tcpa'], 99], TCPA_MAX]]];
  }
  // Colour expression mirroring tier()→color for the danger/caution/normal tiers. Callers layer
  // SART / lost overrides on top (those are symbology concepts, not risk tiers).
  function riskColorExpr() {
    var cpa = ['coalesce', ['get', 'cpa'], 99];
    var tcpa = ['coalesce', ['get', 'tcpa'], -999];
    var danger = ['all', ['<', cpa, CPA_WARN], ['>', tcpa, 0], ['<', tcpa, TCPA_MAX]];
    var caution = ['all', ['<', cpa, CPA_CAUTION], ['>', tcpa, 0], ['<', tcpa, TCPA_CAUTION]];
    var cautionNoTcpa = ['all', ['!', ['has', 'tcpa']], ['<', cpa, CPA_WARN]];
    return ['case',
      ['==', ['get', 'risk'], 'danger'], COL.danger,
      ['==', ['get', 'risk'], 'caution'], COL.caution,
      ['==', ['get', 'risk'], 'normal'], COL.normal,
      ['==', ['get', 'cpaValid'], false], COL.normal,
      ['!', ['has', 'cpa']], COL.normal,
      danger, COL.danger,
      caution, COL.caution,
      cautionNoTcpa, COL.caution,
      COL.normal];
  }

  global.HelmAisRisk = {
    tier: tier, isDanger: isDanger, color: color,
    dangerExpr: dangerExpr, riskColorExpr: riskColorExpr,
    CPA_WARN: CPA_WARN, TCPA_MAX: TCPA_MAX, CPA_CAUTION: CPA_CAUTION, TCPA_CAUTION: TCPA_CAUTION, COL: COL
  };
})(typeof window !== 'undefined' ? window : this);
