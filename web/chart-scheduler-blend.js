/*
 * Helm — chart-scheduler-blend.js (SCHED-2)
 * Prefetch scheduler hints, hold stale artifacts during pan/zoom, composite WebGPU draw.
 */
(function (global) {
  'use strict';

  function HelmChartSchedulerBlend(map, chartLayer, opts) {
    if (!global.HelmChartViewportScheduler) throw new Error('HelmChartViewportScheduler required');
    if (!global.HelmChartArtifactCache) throw new Error('HelmChartArtifactCache required');
    opts = opts || {};
    this.map = map;
    this.chartLayer = chartLayer;
    this.scheduler = global.HelmChartViewportScheduler;
    this.cache = new global.HelmChartArtifactCache(opts.cache || {});
    this.opts = opts;
    this._destroyed = false;
    this._debounceMs = opts.debounceMs || 220;
    this._debounceTimer = null;
    this._lastResponse = null;
    this._lastRequest = null;
    this._gestureActive = false;
    this._bind();
  }

  HelmChartSchedulerBlend.prototype._scheduleOpts = function () {
    return {
      source_epoch: this.opts.source_epoch || 'synthetic-chart-1@2026-06-28',
      display_fingerprint: this.opts.display_fingerprint || 'day:standard:10:5:10:20:text:on:soundings:on',
      renderer_sha: this.opts.renderer_sha || 'fixture-renderer-sha'
    };
  };

  HelmChartSchedulerBlend.prototype._artifactUrlForEntry = function (entry) {
    if (this.opts.artifactUrlForEntry) return this.opts.artifactUrlForEntry(entry);
    return this.opts.packetUrl || 'data/render-artifact-chart-1.json';
  };

  HelmChartSchedulerBlend.prototype._fetchArtifactForEntry = function (entry) {
    var self = this;
    var url = this._artifactUrlForEntry(entry);
    return fetch(url, { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('artifact HTTP ' + r.status);
        return r.json();
      })
      .then(function (json) {
        var parse = global.HelmChartArtifactAuto && global.HelmChartArtifactAuto._test
          ? global.HelmChartArtifactAuto._test.parseArtifactJson
          : null;
        if (!parse) throw new Error('HelmChartArtifactAuto parser unavailable');
        var artifact = parse(json);
        var tile = entry.tile || {};
        artifact.viewport = self.scheduler.tileViewport(+tile.z, +tile.x, +tile.y);
        return artifact;
      });
  };

  HelmChartSchedulerBlend.prototype.refresh = function (intent) {
    if (this._destroyed) return Promise.resolve(null);
    var req = this.scheduler.buildScheduleRequestFromMap(this.map, Object.assign({}, this._scheduleOpts(), {
      intent: intent || 'visible',
      request_id: 'sched-' + Date.now()
    }));
    var resp = this.scheduler.buildScheduleResponse(req, { source_epoch: req.source_epoch_hint });
    this._lastRequest = req;
    this._lastResponse = resp;
    var self = this;
    return this.cache.prefetch(resp, function (entry) {
      return self._fetchArtifactForEntry(entry);
    }).then(function () {
      self._applyDraw(resp);
      return resp;
    });
  };

  HelmChartSchedulerBlend.prototype._applyDraw = function (response) {
    if (this._destroyed || !this.chartLayer) return;
    var cover = this.cache.coveringDrawEntries(response);
    var gpu = this.chartLayer.getGpuLayer && this.chartLayer.getGpuLayer();
    if (gpu && gpu.setCompositeEntries) {
      gpu.setCompositeEntries(cover.entries, {
        holdStale: this._gestureActive || cover.strictMissing,
        strictMissing: cover.strictMissing
      });
    } else if (cover.entries.length && this.chartLayer.setArtifact) {
      this.chartLayer.setArtifact(cover.entries[0].artifact);
    }
    global.__helmChartScheduler = {
      request: this._lastRequest,
      response: response,
      cache: this.cache.snapshot(),
      strictMissing: cover.strictMissing
    };
    if (global.HelmChartRendererStatus && global.HelmChartRendererStatus.publish) {
      global.HelmChartRendererStatus.publish();
    }
  };

  HelmChartSchedulerBlend.prototype._onMove = function () {
    if (this._destroyed) return;
    this._gestureActive = true;
    if (this._lastResponse) this._applyDraw(this._lastResponse);
  };

  HelmChartSchedulerBlend.prototype._onMoveEnd = function () {
    var self = this;
    if (this._destroyed) return;
    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(function () {
      self._gestureActive = false;
      self.refresh('visible').then(function () {
        return self.refresh('prefetch');
      }).catch(function (err) {
        console.warn('[chart-scheduler-blend] refresh failed:', err && err.message ? err.message : err);
      });
    }, this._debounceMs);
  };

  HelmChartSchedulerBlend.prototype._bind = function () {
    var self = this;
    this._handlers = {
      move: function () { self._onMove(); },
      moveend: function () { self._onMoveEnd(); },
      zoom: function () { self._onMove(); },
      zoomend: function () { self._onMoveEnd(); }
    };
    this.map.on('move', this._handlers.move);
    this.map.on('moveend', this._handlers.moveend);
    this.map.on('zoom', this._handlers.zoom);
    this.map.on('zoomend', this._handlers.zoomend);
  };

  HelmChartSchedulerBlend.prototype.init = function () {
    var self = this;
    return this.refresh('visible').then(function () {
      return self.refresh('prefetch');
    });
  };

  HelmChartSchedulerBlend.prototype.destroy = function () {
    if (this._destroyed) return;
    this._destroyed = true;
    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this.map.off('move', this._handlers.move);
    this.map.off('moveend', this._handlers.moveend);
    this.map.off('zoom', this._handlers.zoom);
    this.map.off('zoomend', this._handlers.zoomend);
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = HelmChartSchedulerBlend;
  else global.HelmChartSchedulerBlend = HelmChartSchedulerBlend;
})(typeof window !== 'undefined' ? window : this);
