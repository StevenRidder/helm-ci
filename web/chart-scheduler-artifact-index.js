/*
 * Helm — chart-scheduler-artifact-index.js (SCHED-3)
 * Resolves scheduler tile hints to server-fed render-artifact packets via
 * helm.render.artifact_index.v1 (RENDERMODEL-5 pyramid).
 */
(function (global) {
  'use strict';

  var INDEX_SCHEMA = 'helm.render.artifact_index.v1';

  function tileKey(tile) {
    return (+tile.z) + ',' + (+tile.x) + ',' + (+tile.y);
  }

  function HelmChartSchedulerArtifactIndex(opts) {
    opts = opts || {};
    this.indexUrl = opts.indexUrl || '/artifact/index.json';
    this.staticFallbackUrl = opts.staticFallbackUrl || null;
    this._index = null;
    this._byTile = Object.create(null);
    this._loadError = null;
    this._loadPromise = null;
    this._useServerUrls = false;
  }

  function ingestIndex(self, json, fromServer) {
    if (json.schema_version !== INDEX_SCHEMA) {
      throw new Error('unsupported artifact index schema: ' + (json.schema_version || 'missing'));
    }
    self._index = json;
    self._byTile = Object.create(null);
    self._useServerUrls = !!fromServer;
    (json.entries || []).forEach(function (entry) {
      if (entry && entry.tile) self._byTile[tileKey(entry.tile)] = entry;
    });
    return json;
  }

  HelmChartSchedulerArtifactIndex.prototype.load = function () {
    var self = this;
    if (this._loadPromise) return this._loadPromise;
    function tryUrl(url, fromServer) {
      return fetch(url, { cache: 'no-cache' })
        .then(function (r) {
          if (!r.ok) throw new Error('artifact index HTTP ' + r.status);
          return r.json();
        })
        .then(function (json) { return ingestIndex(self, json, fromServer); });
    }
    this._loadPromise = tryUrl(this.indexUrl, true).catch(function (err) {
      if (!self.staticFallbackUrl) throw err;
      return tryUrl(self.staticFallbackUrl, false);
    }).catch(function (err) {
      self._loadError = err && err.message ? err.message : String(err);
      throw err;
    });
    return this._loadPromise;
  };

  HelmChartSchedulerArtifactIndex.prototype.lookup = function (tile) {
    return this._byTile[tileKey(tile)] || null;
  };

  HelmChartSchedulerArtifactIndex.prototype.urlForTile = function (tile) {
    var entry = this.lookup(tile);
    if (!entry) return null;
    if (this._useServerUrls) {
      return '/artifact/' + (+tile.z) + '/' + (+tile.x) + '/' + (+tile.y) + '.json';
    }
    return entry.artifact_url || null;
  };

  HelmChartSchedulerArtifactIndex.prototype.urlForEntry = function (entry) {
    if (!entry || !entry.tile) return null;
    return this.urlForTile(entry.tile);
  };

  HelmChartSchedulerArtifactIndex.prototype.snapshot = function () {
    return {
      loaded: !!this._index,
      cell_id: this._index && this._index.cell_id,
      source_epoch: this._index && this._index.source_epoch,
      tile_count: this._index && this._index.tile_count,
      z_range: this._index && this._index.z_range,
      use_server_urls: this._useServerUrls,
      load_error: this._loadError
    };
  };

  HelmChartSchedulerArtifactIndex._test = {
    tileKey: tileKey,
    INDEX_SCHEMA: INDEX_SCHEMA
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = HelmChartSchedulerArtifactIndex;
  else global.HelmChartSchedulerArtifactIndex = HelmChartSchedulerArtifactIndex;
})(typeof window !== 'undefined' ? window : this);
