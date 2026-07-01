(function () {
  'use strict';

  function loudError(code, message, details) {
    var err = new Error(message || code);
    err.code = code;
    err.details = details || {};
    return err;
  }

  function manifestBase(url) {
    return new URL(url, window.location.href);
  }

  function packUrl(manifest, manifestUrl) {
    var transport = manifest && manifest.transport || {};
    var raw = transport.packUrl || transport.url || transport.pmtilesUrl;
    if (!raw) throw loudError('missing_pack_url', 'Environmental grid manifest has no packUrl', { packId: manifest && manifest.packId });
    return new URL(raw, manifestBase(manifestUrl)).href;
  }

  function bytesToHex(bytes) {
    return Array.prototype.map.call(bytes, function (b) { return b.toString(16).padStart(2, '0'); }).join('');
  }

  async function sha256Hex(bytes) {
    if (!window.crypto || !window.crypto.subtle) {
      throw loudError('unsupported_checksum', 'SHA-256 verification is unavailable in this client');
    }
    var digest = await window.crypto.subtle.digest('SHA-256', bytes);
    return bytesToHex(new Uint8Array(digest));
  }

  function getChunk(manifest, chunkKey) {
    var chunks = manifest && manifest.chunks || {};
    var chunk = chunks[chunkKey];
    if (!chunk) {
      throw loudError('missing_chunk', 'Environmental grid chunk is missing from the pack index', {
        packId: manifest && manifest.packId,
        chunkKey: chunkKey
      });
    }
    if (!Array.isArray(chunk.byteRange) || chunk.byteRange.length !== 2) {
      throw loudError('missing_range', 'Environmental grid chunk has no byte range', {
        packId: manifest && manifest.packId,
        chunkKey: chunkKey
      });
    }
    return chunk;
  }

  function parseEnvelope(bytes, chunkKey) {
    var view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    var magic = new TextDecoder().decode(bytes.slice(0, 8));
    if (magic !== 'HELMGRID') throw loudError('bad_chunk_magic', 'Environmental grid chunk has invalid magic', { chunkKey: chunkKey });
    var version = view.getUint16(8, true);
    if (version !== 1) throw loudError('unsupported_chunk_version', 'Unsupported environmental grid chunk version', { chunkKey: chunkKey, version: version });
    var headerLen = view.getUint32(12, true);
    var headerStart = 16;
    var headerEnd = headerStart + headerLen;
    if (headerEnd > bytes.byteLength) throw loudError('truncated_chunk_header', 'Environmental grid chunk header is truncated', { chunkKey: chunkKey });
    var header = JSON.parse(new TextDecoder().decode(bytes.slice(headerStart, headerEnd)));
    if (header.schema !== 'helm.env.grid.chunk.v1') throw loudError('bad_chunk_schema', 'Environmental grid chunk schema mismatch', { chunkKey: chunkKey });
    return { header: header, payload: bytes.slice(headerEnd) };
  }

  async function fetchManifest(url) {
    var resp = await fetch(url, { cache: 'no-store' });
    if (!resp.ok) throw loudError('missing_manifest', 'Environmental grid manifest could not be loaded', { url: url, status: resp.status });
    var manifest = await resp.json();
    if (manifest.schema !== 'helm.env.grid.pack.v1' || manifest.encoding !== 'helm.env.grid.v1') {
      throw loudError('unsupported_manifest', 'Unsupported environmental grid manifest', { url: url, schema: manifest.schema, encoding: manifest.encoding });
    }
    return manifest;
  }

  async function fetchChunk(manifest, manifestUrl, chunkKey) {
    var chunk = getChunk(manifest, chunkKey);
    var offset = Number(chunk.byteRange[0]);
    var length = Number(chunk.byteRange[1]);
    if (!Number.isFinite(offset) || !Number.isFinite(length) || offset < 0 || length <= 0) {
      throw loudError('missing_range', 'Environmental grid chunk byte range is invalid', { chunkKey: chunkKey, byteRange: chunk.byteRange });
    }
    var resp = await fetch(packUrl(manifest, manifestUrl), {
      // Default cache mode: HTTP caches do not key on the Range header, so
      // 'force-cache' could replay one chunk's bytes for another range.
      headers: { Range: 'bytes=' + offset + '-' + (offset + length - 1) }
    });
    if (!(resp.status === 206 || resp.status === 200)) {
      throw loudError('missing_range', 'Environmental grid chunk byte range could not be loaded', { chunkKey: chunkKey, status: resp.status });
    }
    var bytes = new Uint8Array(await resp.arrayBuffer());
    if (bytes.byteLength !== length) {
      throw loudError('missing_range', 'Environmental grid chunk byte range returned the wrong length', {
        chunkKey: chunkKey,
        expected: length,
        actual: bytes.byteLength
      });
    }
    var checksum = String(chunk.checksum || '');
    if (!checksum.startsWith('sha256:')) throw loudError('missing_checksum', 'Environmental grid chunk has no SHA-256 checksum', { chunkKey: chunkKey });
    var actual = await sha256Hex(bytes);
    if (actual !== checksum.slice(7)) throw loudError('checksum_mismatch', 'Environmental grid chunk checksum mismatch', { chunkKey: chunkKey });
    return parseEnvelope(bytes, chunkKey);
  }

  window.HelmWxGridPacks = {
    fetchManifest: fetchManifest,
    fetchChunk: fetchChunk,
    loudError: loudError
  };
}());
