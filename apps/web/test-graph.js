const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log(`[BROWSER ${msg.type().toUpperCase()}] ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    console.log(`[BROWSER UNCAUGHT] ${err.toString()}`);
  });

  try {
    await page.goto('http://localhost:3000/graph', { waitUntil: 'networkidle0', timeout: 15000 });
    console.log('Page loaded!');
    
    // Find canvas
    const canvas = await page.$('canvas');
    if (canvas) {
      console.log('Canvas found!');
      const box = await canvas.boundingBox();
      
      // Move mouse to center
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(500);
      
      // Click and hold (drag)
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2 + 50, box.y + box.height / 2 + 50, { steps: 10 });
      await page.waitForTimeout(1000);
      await page.mouse.up();
      
      console.log('Drag action completed.');
    } else {
      console.log('Canvas NOT found!');
    }
    
    await page.waitForTimeout(2000);
  } catch (err) {
    console.error('Error in script:', err);
  } finally {
    await browser.close();
  }
})();
