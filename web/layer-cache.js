// layer-cache.js — shared last-known-good cache for map overlays.
// ----------------------------------------------------------------------------------------------
// Network pulls must never directly blank a working chart layer. A fetch produces a candidate
// snapshot; only a validated candidate is promoted into the visible layer and this cache. When a
// later pull fails (429/offline/server down), feature modules can re-render the last known good
// snapshot and mark it stale instead of deleting pixels.
(function (root) {
  'use strict';

  var STORE = 'helm.layer-cache.v1';
  var VERSION = 1;
  var MAX_RECORDS = 48;
  var DEFAULT_TTL_MS = 6 * 60 * 60 * 1000;

  function now() { return Date.now ? Date.now() : +new Date(); }
  function iso(ms) { return new Date(ms || now()).toISOString(); }
  function finite(n) { return typeof n === 'number' && isFinite(n); }
  function clone(x) { return x == null ? x : JSON.parse(JSON.stringify(x)); }
  function storage() { try { return root.localStorage || null; } catch (_) { return null; } }
  function round(n, d) { var p = Math.pow(10, d == null ? 3 : d); return Math.round(n * p) / p; }

  function normalizeLon(lon) {
    var w = ((lon + 180) % 360 + 360) % 360 - 180;
    return w === -180 && lon > 0 ? 180 : w;
  }

  function bboxKey(bbox) {
    return Array.isArray(bbox) ? bbox.map(function (v) { return round(+v, 3); }).join(',') : 'global';
  }

  function recordKey(rec) {
    return rec.cacheKey || [
      rec.layerId,
      rec.scope || 'default',
      rec.variant || '',
      bboxKey(rec.bbox),
      rec.timeKey || ''
    ].join('|');
  }

  function readDb() {
    var s = storage(); if (!s) return { version: VERSION, records: [] };
    try {
      var raw = s.getItem(STORE);
      if (!raw) return { version: VERSION, records: [] };
      var db = JSON.parse(raw);
      if (!db || db.version !== VERSION || !Array.isArray(db.records)) return { version: VERSION, records: [] };
      return db;
    } catch (_) {
      try { s.removeItem(STORE); } catch (__) {}
      return { version: VERSION, records: [] };
    }
  }

  function writeDb(db) {
    var s = storage(); if (!s) return false;
    try {
      s.setItem(STORE, JSON.stringify({ version: VERSION, records: db.records || [] }));
      return true;
    } catch (_) {
      // If localStorage is full, keep the newest half and retry once. This avoids one over-large
      // layer snapshot poisoning every later layer.
      try {
        db.records = (db.records || []).sort(function (a, b) {
          return (b.storedAt || 0) - (a.storedAt || 0);
        }).slice(0, Math.max(1, Math.floor(MAX_RECORDS / 2)));
        s.setItem(STORE, JSON.stringify({ version: VERSION, records: db.records }));
        return true;
      } catch (__) { return false; }
    }
  }

  function expired(rec, t) {
    if (!rec) return true;
    if (rec.expiresAtMs && rec.expiresAtMs <= (t || now())) return true;
    return false;
  }

  function prune(db, t) {
    t = t || now();
    db.records = (db.records || []).filter(function (rec) { return rec && rec.layerId && !expired(rec, t); });
    db.records.sort(function (a, b) { return (b.storedAt || 0) - (a.storedAt || 0); });
    if (db.records.length > MAX_RECORDS) db.records = db.records.slice(0, MAX_RECORDS);
    return db;
  }

  function put(record) {
    if (!record || !record.layerId) throw new Error('LayerCache.put requires layerId');
    var t = now(), ttl = finite(record.ttlMs) ? record.ttlMs : DEFAULT_TTL_MS;
    var rec = clone(record);
    rec.schemaVersion = VERSION;
    rec.scope = rec.scope || 'default';
    rec.kind = rec.kind || 'snapshot';
    rec.storedAt = t;
    rec.fetchedAtMs = rec.fetchedAtMs || t;
    rec.fetchedAt = rec.fetchedAt || iso(rec.fetchedAtMs);
    rec.expiresAtMs = rec.expiresAtMs || (ttl > 0 ? t + ttl : 0);
    rec.expiresAt = rec.expiresAtMs ? iso(rec.expiresAtMs) : null;
    rec.cacheKey = recordKey(rec);

    var db = prune(readDb(), t);
    db.records = db.records.filter(function (r) { return recordKey(r) !== rec.cacheKey; });
    db.records.unshift(rec);
    prune(db, t);
    writeDb(db);
    return clone(rec);
  }

  function remove(layerId, opts) {
    opts = opts || {};
    var db = readDb();
    db.records = (db.records || []).filter(function (rec) {
      if (rec.layerId !== layerId) return true;
      if (opts.scope && rec.scope !== opts.scope) return true;
      if (opts.variant && rec.variant !== opts.variant) return true;
      return false;
    });
    writeDb(db);
  }

  function all(layerId, opts) {
    opts = opts || {};
    var t = now(), raw = readDb(), before = (raw.records || []).length, db = prune(raw, t);
    var changed = db.records.length !== before;
    var out = db.records.filter(function (rec) {
      if (layerId && rec.layerId !== layerId) return false;
      if (opts.scope && rec.scope !== opts.scope) return false;
      if (opts.variant && rec.variant !== opts.variant) return false;
      if (opts.kind && rec.kind !== opts.kind) return false;
      return true;
    });
    if (changed) writeDb(db);
    return clone(out);
  }

  function unwrapBbox(bbox) {
    if (!Array.isArray(bbox) || bbox.length < 4) return null;
    var w = +bbox[0], s = +bbox[1], e = +bbox[2], n = +bbox[3];
    if (!finite(w) || !finite(s) || !finite(e) || !finite(n)) return null;
    if (e < w) e += 360;
    return [w, s, e, n];
  }

  function coversBbox(outer, inner) {
    outer = unwrapBbox(outer); inner = unwrapBbox(inner);
    if (!outer || !inner) return false;
    if (outer[3] < inner[3] || outer[1] > inner[1]) return false;
    var iw = inner[0], ie = inner[2], mid = (iw + ie) / 2;
    var omid = (outer[0] + outer[2]) / 2;
    var shift = Math.round((omid - mid) / 360) * 360;
    iw += shift; ie += shift;
    if (ie - iw >= 360 && outer[2] - outer[0] >= 360) return outer[1] <= inner[1] && outer[3] >= inner[3];
    return outer[0] <= iw && outer[2] >= ie && outer[1] <= inner[1] && outer[3] >= inner[3];
  }

  function intersectsBbox(a, b) {
    a = unwrapBbox(a); b = unwrapBbox(b);
    if (!a || !b) return false;
    if (a[3] < b[1] || a[1] > b[3]) return false;
    var bw = b[0], be = b[2], amid = (a[0] + a[2]) / 2, bmid = (bw + be) / 2;
    var shift = Math.round((amid - bmid) / 360) * 360;
    bw += shift; be += shift;
    return a[2] >= bw && a[0] <= be;
  }

  function getBest(layerId, opts) {
    opts = opts || {};
    var records = all(layerId, opts);
    if (!records.length) return null;
    if (opts.bbox) {
      for (var i = 0; i < records.length; i++) if (coversBbox(records[i].bbox, opts.bbox)) {
        records[i].match = 'covers'; return records[i];
      }
      for (var j = 0; opts.allowIntersect && j < records.length; j++) if (intersectsBbox(records[j].bbox, opts.bbox)) {
        records[j].match = 'intersects'; return records[j];
      }
      if (!opts.allowAny) return null;
    }
    records[0].match = opts.bbox ? 'out-of-coverage' : 'latest';
    return records[0];
  }

  function status(rec, opts) {
    opts = opts || {};
    if (!rec) return { state: 'empty', label: 'no cached layer' };
    var ageMin = Math.max(0, Math.round((now() - (rec.fetchedAtMs || rec.storedAt || now())) / 60000));
    var cover = opts.bbox ? coversBbox(rec.bbox, opts.bbox) : true;
    return {
      state: cover ? 'cached' : 'out_of_coverage',
      label: (cover ? 'cached' : 'cached outside view') + ' · ' + (ageMin < 1 ? 'just now' : ageMin + ' min old'),
      ageMin: ageMin,
      covers: cover
    };
  }

  root.HelmLayerCache = {
    put: put, remove: remove, all: all, getBest: getBest, status: status,
    coversBbox: coversBbox, intersectsBbox: intersectsBbox,
    _readDb: readDb, _prune: prune, _recordKey: recordKey, _normalizeLon: normalizeLon
  };
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
