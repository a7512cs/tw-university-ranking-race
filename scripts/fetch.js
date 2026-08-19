// Fetch fully rendered HTML from www.com.tw via patchright (stealth playwright fork).
// Usage: node fetch.js <url> <outFile> false
//
// The last arg MUST be "false" (headed): the site sits behind a Cloudflare
// managed challenge that blocks headless mode and plain playwright (its CDP
// fingerprint is detected even headed). Only patchright + real Chrome
// (channel: 'chrome') + headed passes. The persistent chrome-profile/ next to
// this script keeps the cf_clearance cookie so later fetches skip the challenge.
const { chromium } = require('patchright');
const fs = require('fs');
const path = require('path');

const URL_TARGET = process.argv[2];
const OUT_FILE = process.argv[3];
const IS_HEADLESS = process.argv[4] !== 'false';

const WAIT_TEXT = '錄取分數';
const TIMEOUT_MS = 60000;
const POLL_MS = 1000;
const PROFILE_DIR = path.join(__dirname, 'chrome-profile');

async function main() {
  // Persistent context + real Chrome channel: recommended stealth setup.
  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    channel: 'chrome',
    headless: IS_HEADLESS,
    viewport: null,
  });
  const page = context.pages()[0] || (await context.newPage());

  try {
    await page.goto(URL_TARGET, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });

    const deadline = Date.now() + TIMEOUT_MS;
    let found = false;
    while (Date.now() < deadline) {
      const html = await page.content().catch(() => '');
      if (html.includes(WAIT_TEXT)) {
        found = true;
        break;
      }
      await page.waitForTimeout(POLL_MS);
    }

    const finalHtml = await page.content();
    fs.writeFileSync(OUT_FILE, finalHtml, 'utf8');

    if (found) {
      console.log('RESULT: SUCCESS');
    } else {
      console.log('RESULT: TIMEOUT (saved last snapshot)');
      console.log('PAGE TITLE:', await page.title().catch(() => '?'));
    }
  } finally {
    await context.close();
  }
}

main().catch((err) => {
  console.error('RESULT: ERROR', err.message);
  process.exit(1);
});
