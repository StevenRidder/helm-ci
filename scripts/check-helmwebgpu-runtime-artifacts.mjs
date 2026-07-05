#!/usr/bin/env node
/*
 * HELMWEBGPU-6: validate the WebGPU/Vulkan render-artifact runtime inventory.
 *
 * This guard is intentionally static and narrow. It does not claim renderer
 * parity; it fails if a runtime-facing WebGPU/native/C++ artifact path starts
 * depending on Python, uvicorn, or FastAPI as a launch/runtime requirement.
 */
import fs from 'node:fs';
import path from 'node:path';

const INVENTORY = 'docs/helmwebgpu-render-runtime-inventory.json';
const RUNTIME_INVENTORY = 'docs/runtime-inventory.json';
const ALLOWED_CLASSIFICATIONS = new Set([
  'browser-client-render-artifact',
  'native-cxx-render-proof',
  'required-cxx-runtime-source',
  'tooling-reference',
  'fixture-test'
]);
const FORBIDDEN_RUNTIME_RE = /\b(python3?|uvicorn|fastapi|FastAPI)\b/;
const REQUIRED_RUNTIME_IDS = new Set(['helm-server', 'helm-packd', 'helm-envd-target']);

function die(errors, context, message) {
  errors.push(`${context}: ${message}`);
}

function readJson(repoRoot, relPath, errors) {
  const full = path.join(repoRoot, relPath);
  try {
    return JSON.parse(fs.readFileSync(full, 'utf8'));
  } catch (err) {
    die(errors, relPath, `cannot read valid JSON: ${err.message}`);
    return null;
  }
}

function exists(repoRoot, relPath) {
  return fs.existsSync(path.join(repoRoot, relPath));
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function validateRuntimeInventoryCrosscheck(runtimeData, helmwebgpuEntries, errors) {
  if (!runtimeData || typeof runtimeData !== 'object') return;
  const runtimeEntries = new Map(asArray(runtimeData.entries).map((entry) => [entry.id, entry]));
  const referenced = new Set();
  for (const entry of helmwebgpuEntries) {
    for (const id of asArray(entry.required_runtime_inventory_ids)) referenced.add(id);
  }
  for (const id of REQUIRED_RUNTIME_IDS) {
    if (!referenced.has(id)) {
      die(errors, 'runtime-inventory crosscheck', `HELMWEBGPU inventory must reference ${id}`);
    }
    const runtimeEntry = runtimeEntries.get(id);
    if (!runtimeEntry) {
      die(errors, 'runtime-inventory crosscheck', `docs/runtime-inventory.json missing ${id}`);
      continue;
    }
    if (runtimeEntry.starts_python_daemon) {
      die(errors, id, 'runtime inventory says this renderer source starts a Python daemon');
    }
    if (runtimeEntry.python_allowed) {
      die(errors, id, 'required renderer runtime entry must not allow Python');
    }
    if (runtimeEntry.classification !== 'required-runtime') {
      die(errors, id, 'runtime inventory entry must be classification=required-runtime');
    }
    if (!/c\+\+|cpp/i.test(String(runtimeEntry.language))) {
      die(errors, id, 'runtime inventory entry must be C++');
    }
  }
}

function validateInventory(repoRoot, data, runtimeData, errors) {
  if (!data || typeof data !== 'object') return;
  if (data.schema !== 'helm.helmwebgpu_render_runtime_inventory.v1') {
    die(errors, 'inventory', 'schema must be helm.helmwebgpu_render_runtime_inventory.v1');
  }

  const declared = new Set(asArray(data.classifications));
  for (const expected of ALLOWED_CLASSIFICATIONS) {
    if (!declared.has(expected)) die(errors, 'inventory', `missing classification ${expected}`);
  }
  for (const actual of declared) {
    if (!ALLOWED_CLASSIFICATIONS.has(actual)) die(errors, 'inventory', `unknown classification ${actual}`);
  }

  const entries = asArray(data.entries);
  if (!entries.length) die(errors, 'inventory', 'entries must be non-empty');

  const seen = new Set();
  const coverage = { browser: 0, native: 0, cxx: 0, tooling: 0 };

  for (const entry of entries) {
    const id = entry && entry.id ? String(entry.id) : '<missing-id>';
    if (!entry || typeof entry !== 'object') {
      die(errors, id, 'entry must be an object');
      continue;
    }
    if (seen.has(id)) die(errors, id, 'duplicate id');
    seen.add(id);

    if (!entry.title) die(errors, id, 'title is required');
    if (!ALLOWED_CLASSIFICATIONS.has(entry.classification)) {
      die(errors, id, `invalid classification ${entry.classification}`);
    }
    if (!entry.language) die(errors, id, 'language is required');
    if (!entry.runtime_contract) die(errors, id, 'runtime_contract is required');
    if (typeof entry.required_python_runtime !== 'boolean') {
      die(errors, id, 'required_python_runtime must be boolean');
    }
    if (!entry.python_role) die(errors, id, 'python_role is required');

    const paths = asArray(entry.paths);
    const launch = asArray(entry.launch).map(String);
    const artifactContracts = asArray(entry.artifact_contracts);
    if (!paths.length) die(errors, id, 'paths must be non-empty');
    if (!artifactContracts.length) die(errors, id, 'artifact_contracts must be non-empty');
    for (const relPath of paths) {
      if (typeof relPath !== 'string' || !relPath) {
        die(errors, id, 'paths must contain non-empty strings');
      } else if (!exists(repoRoot, relPath)) {
        die(errors, id, `path does not exist: ${relPath}`);
      } else if (path.isAbsolute(relPath) || relPath.split(/[\\/]/).includes('..')) {
        die(errors, id, `path must stay repo-relative: ${relPath}`);
      }
    }

    if (entry.runtime_facing) {
      if (entry.required_python_runtime !== false) {
        die(errors, id, 'runtime-facing artifact must set required_python_runtime=false');
      }
      if (FORBIDDEN_RUNTIME_RE.test(launch.join('\n'))) {
        die(errors, id, 'runtime-facing launch path mentions Python/FastAPI/uvicorn');
      }
      if (/python|fastapi|uvicorn/i.test(String(entry.language))) {
        die(errors, id, 'runtime-facing language must not be Python/FastAPI/uvicorn');
      }
    }

    if (entry.classification === 'browser-client-render-artifact') coverage.browser += 1;
    if (entry.classification === 'native-cxx-render-proof') coverage.native += 1;
    if (entry.classification === 'required-cxx-runtime-source') coverage.cxx += 1;
    if (entry.classification === 'tooling-reference') coverage.tooling += 1;
  }

  if (!coverage.browser) die(errors, 'inventory', 'must cover at least one browser WebGPU artifact');
  if (!coverage.native) die(errors, 'inventory', 'must cover at least one native C++/VSG proof path');
  if (!coverage.cxx) die(errors, 'inventory', 'must cover at least one required C++ runtime source path');
  if (!coverage.tooling) die(errors, 'inventory', 'must classify Python/tooling reference paths');

  validateRuntimeInventoryCrosscheck(runtimeData, entries, errors);
}

function negativeSmoke(repoRoot) {
  const errors = [];
  const data = readJson(repoRoot, INVENTORY, errors);
  const runtimeData = readJson(repoRoot, RUNTIME_INVENTORY, errors);
  if (!data) return 2;
  data.entries = asArray(data.entries).concat([{
    id: 'negative-python-runtime',
    title: 'Negative smoke Python runtime',
    classification: 'browser-client-render-artifact',
    language: 'Python',
    runtime_facing: true,
    required_python_runtime: true,
    python_role: 'runtime',
    artifact_contracts: ['negative'],
    runtime_contract: 'must fail',
    paths: ['scripts/check-helmwebgpu-runtime-artifacts.mjs'],
    launch: ['python3 bad-runtime.py']
  }]);
  validateInventory(repoRoot, data, runtimeData, errors);
  const expected = errors.some((error) => error.includes('negative-python-runtime'));
  if (!expected) {
    console.error('HELMWEBGPU runtime artifact negative smoke: FAIL');
    console.error('  expected injected Python runtime entry to fail');
    return 1;
  }
  console.log('HELMWEBGPU runtime artifact negative smoke: PASS');
  return 0;
}

function main() {
  const repoRoot = process.cwd();
  if (process.argv.includes('--negative-smoke-python-runtime')) {
    return negativeSmoke(repoRoot);
  }

  const errors = [];
  const data = readJson(repoRoot, INVENTORY, errors);
  const runtimeData = readJson(repoRoot, RUNTIME_INVENTORY, errors);
  validateInventory(repoRoot, data, runtimeData, errors);

  if (errors.length) {
    console.error('HELMWEBGPU runtime artifact guard: FAIL');
    for (const error of errors) console.error(`  - ${error}`);
    return 1;
  }

  console.log('HELMWEBGPU runtime artifact guard: PASS');
  console.log(`  entries: ${data.entries.length}`);
  console.log('  runtime-facing Python requirement: none');
  console.log('  crosscheck: helm-server, helm-packd, helm-envd-target');
  return 0;
}

process.exitCode = main();
