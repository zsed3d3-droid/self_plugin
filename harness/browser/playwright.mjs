// Shared pinned dependency; this does not start a server or install a browser.
let runtime;
try { runtime = await import('playwright'); }
catch (error) {
  if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error;
  throw new Error('Run npm ci at the self_plugin repository root, then npx playwright install chromium.');
}
export const chromium = runtime.chromium;
