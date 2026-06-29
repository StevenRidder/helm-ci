const { test, expect } = require('@playwright/test');

test('service worker caches app shell and reloads while offline', async ({ page, context }) => {
  await page.goto('/sw.js?client11-clean=' + Date.now(), { waitUntil: 'domcontentloaded' });
  await page.evaluate(async () => {
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(regs.map(reg => reg.unregister()));
    }
    if ('caches' in window) {
      const names = await caches.keys();
      await Promise.all(names.filter(name => name.startsWith('helm-')).map(name => caches.delete(name)));
    }
  });

  await page.goto('/?client11=' + Date.now(), { waitUntil: 'domcontentloaded' });
  await expect(page).toHaveTitle(/Helm/);

  await page.waitForFunction(async () => {
    const regs = await navigator.serviceWorker.getRegistrations();
    return regs.some(reg =>
      reg.active &&
      new URL(reg.active.scriptURL).pathname.endsWith('/sw.js') &&
      navigator.serviceWorker.controller);
  }, null, { timeout: 20000 });

  const readCacheState = async () => page.evaluate(async () => {
    const names = await caches.keys();
    const shellName = names.find(name => name.startsWith('helm-shell-client11-v1'));
    const tileName = names.find(name => name.startsWith('helm-tiles-client11-v1'));
    const runtimeName = names.find(name => name.startsWith('helm-runtime-client11-v1'));
    const shell = shellName ? await caches.open(shellName) : null;
    const hasIndex = !!(shell && await shell.match(new URL('index.html', location.href).href));
    const hasMapLibre = !!(shell && await shell.match(new URL('vendor/maplibre-gl/maplibre-gl.js', location.href).href));
    const hasGlyph = !!(shell && await shell.match(new URL('fonts/Noto%20Sans%20Regular/0-255.pbf', location.href).href));
    const healthCached = !!(await caches.match(new URL('health', location.href).href));
    const navCached = !!(await caches.match(new URL('nav', location.href).href));
    return { names, hasIndex, hasMapLibre, hasGlyph, healthCached, navCached, tileName, runtimeName };
  });

  await page.waitForFunction(async () => {
    const names = await caches.keys();
    const shellName = names.find(name => name.startsWith('helm-shell-client11-v1'));
    const tileName = names.find(name => name.startsWith('helm-tiles-client11-v1'));
    const runtimeName = names.find(name => name.startsWith('helm-runtime-client11-v1'));
    const shell = shellName ? await caches.open(shellName) : null;
    if (!shell || !tileName || !runtimeName) return false;
    const hasIndex = !!(await shell.match(new URL('index.html', location.href).href));
    const hasMapLibre = !!(await shell.match(new URL('vendor/maplibre-gl/maplibre-gl.js', location.href).href));
    const hasGlyph = !!(await shell.match(new URL('fonts/Noto%20Sans%20Regular/0-255.pbf', location.href).href));
    return hasIndex && hasMapLibre && hasGlyph;
  }, null, { timeout: 20000 });

  const cacheState = await readCacheState();

  expect(cacheState.names.some(name => name.startsWith('helm-shell-client11-v1'))).toBeTruthy();
  expect(cacheState.tileName).toBeTruthy();
  expect(cacheState.runtimeName).toBeTruthy();
  expect(cacheState.hasIndex).toBeTruthy();
  expect(cacheState.hasMapLibre).toBeTruthy();
  expect(cacheState.hasGlyph).toBeTruthy();
  expect(cacheState.healthCached).toBeFalsy();
  expect(cacheState.navCached).toBeFalsy();

  await context.setOffline(true);
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page).toHaveTitle(/Helm/);
  await expect(page.locator('#map')).toBeVisible();
  await context.setOffline(false);
});
