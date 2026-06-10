const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
const PORT = 8787;

function serve() {
  const server = http.createServer((req, res) => {
    let file = req.url === '/' ? '/index.html' : req.url;
    const full = path.join(ROOT, file);
    fs.readFile(full, (err, data) => {
      if (err) { res.statusCode = 404; res.end('Not found'); return; }
      const ext = path.extname(full).toLowerCase();
      const mime = { '.html':'text/html', '.js':'application/javascript', '.css':'text/css' }[ext] || 'application/octet-stream';
      res.setHeader('Content-Type', mime);
      res.end(data);
    });
  });
  return new Promise((resolve)=>{ server.listen(PORT, ()=> resolve(server)); });
}

(async ()=>{
  const server = await serve();
  console.log('Demo server listening on http://localhost:'+PORT);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  try {
    await page.goto('http://localhost:'+PORT, { waitUntil: 'domcontentloaded' });

    // MENU: open via Enter, navigate, activate
    await page.focus('#menuBtn');
    await page.keyboard.press('Enter');
    // menu should be visible and aria-expanded true
    const expanded = await page.getAttribute('#menuBtn', 'aria-expanded');
    if (expanded !== 'true') throw new Error('Menu did not expand');
    // ArrowDown to move focus to first item
    await page.keyboard.press('ArrowDown');
    const activeText = await page.evaluate(()=>document.activeElement.textContent.trim());
    if (!activeText) throw new Error('Menu item did not receive focus');

    // capture dialog from activation
    let dialogMsg = null;
    page.on('dialog', async dlg => { dialogMsg = dlg.message(); await dlg.accept(); });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(200);
    if (!dialogMsg || !dialogMsg.startsWith('Activated:')) throw new Error('Menu activation dialog missing');

    // TOOLTIP: focus to show
    await page.focus('#tooltipBtn');
    await page.waitForTimeout(100);
    const tipDisplay = await page.$eval('#tip', el => getComputedStyle(el).display);
    if (tipDisplay === 'none') throw new Error('Tooltip not visible on focus');

    // MODAL: open and test focus trap & esc
    await page.click('#openModal');
    await page.waitForSelector('#modalBackdrop', { state: 'visible' });
    // ensure focus is inside modal
    const activeInside = await page.evaluate(()=> document.querySelector('#modalBackdrop').contains(document.activeElement));
    if (!activeInside) throw new Error('Focus not inside modal on open');

    // press Tab many times and ensure focus stays inside
    for (let i=0;i<6;i++){ await page.keyboard.press('Tab'); }
    const stillInside = await page.evaluate(()=> document.querySelector('#modalBackdrop').contains(document.activeElement));
    if (!stillInside) throw new Error('Focus escaped modal while tabbing');

    // Esc to close
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
    const backdropDisplay = await page.$eval('#modalBackdrop', el => getComputedStyle(el).display);
    if (backdropDisplay !== 'none') throw new Error('Modal did not close on Escape');

    console.log('All accessibility tests passed');
    await browser.close();
    server.close();
    process.exit(0);
  } catch (err) {
    console.error('Test failed:', err);
    await browser.close();
    server.close();
    process.exit(2);
  }

})();
