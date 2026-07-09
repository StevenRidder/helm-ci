// Playwright config for QA-L-2 depth-on-sat screenshot proofs.
// Fiji mock-packd uses serve.py with the committed fiji-depth-userdata fixture served as
// /user-data/ (HELM_USER_DATA_ROOT below) on a dedicated port, so a developer's generic
// serve.py — whose /user-data/ is their real ~/.helm/data extract — is never reused.
// St Marys uses live helm-server when HELM_HARBOUR_E2E=1. Headed Chrome: HELM_QAL2_HEADED=1.
const path = require('path');
const { devices } = require('@playwright/test');
const harbour = require('./playwright.harbour.config.js');
const base = require('./playwright.config.js');

const headed = process.env.HELM_QAL2_HEADED === '1';
const harbourMode = !!process.env.HELM_HARBOUR_E2E;
const FIJI_PORT = process.env.HELM_E2E_PORT || 8078;
const FIJI_BASE_URL = process.env.HELM_E2E_URL || `http://localhost:${FIJI_PORT}`;
const FIXTURE_USER_DATA = path.join(__dirname, 'fixtures', 'fiji-depth-userdata');

const projects = [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }];
if (headed) {
  projects.push({
    name: 'chrome-headed',
    testMatch: /qa-l2-depth-on-sat-fiji-st-marys\.spec\.js/,
    use: {
      ...devices['Desktop Chrome'],
      headless: false,
      channel: 'chrome'
    }
  });
}

module.exports = harbourMode ? {
  ...harbour,
  projects
} : {
  ...base,
  timeout: Number(process.env.HELM_QAL2_TIMEOUT || 90000),
  use: { ...base.use, baseURL: FIJI_BASE_URL },
  webServer: {
    ...base.webServer,
    command: `python3 ${path.join(__dirname, '..', 'serve.py')} ${FIJI_PORT}`,
    url: FIJI_BASE_URL,
    env: { ...process.env, HELM_USER_DATA_ROOT: FIXTURE_USER_DATA }
  },
  projects
};
