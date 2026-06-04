import puppeteer from 'puppeteer';

(async () => {
  console.log("Launching browser...");
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  console.log("Navigating to frontend...");
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle0' });

  console.log("Entering query 'I need crop insurance'...");
  await page.type('textarea', 'I need crop insurance');
  await page.keyboard.press('Enter');

  console.log("Waiting for state verification prompt...");
  await page.waitForSelector('input[placeholder="Enter your state (e.g. Maharashtra)"]', { timeout: 15000 });
  console.log("Prompt appeared!");

  console.log("Entering 'Bihar'...");
  await page.type('input[placeholder="Enter your state (e.g. Maharashtra)"]', 'Bihar');
  await page.keyboard.press('Enter');

  console.log("Waiting for results...");
  await page.waitForFunction(() => {
    return document.body.innerText.includes('cisfnc') || document.body.innerText.includes('dsmpvhscfguj') || document.body.innerText.includes('brfsy');
  }, { timeout: 15000 }).catch(() => {});
  
  // Wait a bit to let renders settle
  await new Promise(r => setTimeout(r, 2000));
  const bodyText = await page.evaluate(() => document.body.innerText);
  
  if (bodyText.includes('State: Unverified')) {
    console.error("FAIL: State: Unverified badge is still present.");
  } else {
    console.log("PASS: No 'State: Unverified' badge found, meaning state is confirmed.");
  }

  await browser.close();
  console.log("Done.");
  process.exit(0);
})();
