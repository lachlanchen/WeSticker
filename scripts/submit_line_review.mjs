// Owner-authorized review of an already uploaded, verified LINE edition.
import { chromium } from 'playwright-core';
import fs from 'node:fs/promises';
import { parseArgs } from 'node:util';

const { values: args } = parseArgs({ options: {
  cdp: {type:'string'}, receipt: {type:'string'}, 'confirm-review': {type:'boolean'},
}});
if (!args.cdp || !args.receipt || !args['confirm-review']) {
  throw Error('Require --cdp URL --receipt PRIVATE_JSON --confirm-review');
}
const source = JSON.parse(await fs.readFile(args.receipt));
const metadata = JSON.parse(await fs.readFile(new URL('./line_japanese_metadata.json', import.meta.url)))[source.pack];
if (!metadata || ![8,16,24].includes(source.count) ||
    !/^https:\/\/creator\.line\.me\/my\/[^/]+\/sticker\/\d+$/.test(source.url)) throw Error('Invalid uploaded pack receipt');
const intent = args.receipt + '.review-intent.json';
const result = args.receipt + '.review.json';
const accepted = new Set(['Waiting for Review','In Review','Approved','On Sale']);
const browser = await chromium.connectOverCDP(args.cdp);
try {
  const page = browser.contexts()[0].pages().find(p=>/^https:\/\/creator\.line\.me\/my\/[^/]+\/sticker\//.test(p.url()));
  if (!page) throw Error('Open the authorized LINE sticker tab first');
  page.setDefaultTimeout(15000);
  const status = async () => (await page.locator('[data-test=product-status]').innerText()).trim();
  const ok = async () => page.getByRole('button',{name:'OK',exact:true}).filter({visible:true}).click();
  const saveJSON = async (file,data) => fs.writeFile(file,JSON.stringify(data,null,2)+'\n',{mode:0o600});
  await page.goto(source.url);
  await page.locator('[data-test=product-status]').waitFor();
  const initial = await status();
  if (initial !== 'Editing' && !accepted.has(initial)) throw Error(`Inspect unexpected state: ${initial}`);
  await page.getByText(metadata.en,{exact:true}).waitFor();
  await page.getByRole('button',{name:'Price Tier',exact:true}).click();
  await page.getByText(/Current price setting/).waitFor();
  const price = (await page.getByText(/Current price setting/).innerText()).replace('Current price setting','').trim();
  if (price !== 'US$1.99+') throw Error(`Review price explicitly before submission: ${price}`);
  if (initial === 'Editing') {
    try { await fs.access(intent); throw Error('Unresolved review intent: reconcile before any retry'); }
    catch (error) { if(error.code!=='ENOENT') throw error; }
    const options = await page.locator('select').filter({visible:true}).locator('option').allTextContents();
    if (options[0].trim() !== price) throw Error('Current price is not the lowest available tier');
    await page.getByRole('button',{name:'Sticker Images',exact:true}).click();
    await page.waitForFunction(n=>document.querySelectorAll('canvas.cm-apng-player-canvas').length===n,source.count+1);
    await page.getByRole('button',{name:'Display Information',exact:true}).click();
    await page.getByRole('link',{name:'Edit',exact:true}).click();
    await page.locator('input[name=is_auto_release][value=true]').check();
    await page.getByText('Save',{exact:true}).click();
    await page.getByText('Save this form?',{exact:true}).waitFor();
    await ok();
    await page.waitForURL(source.url);
    await page.getByText('Start sales automatically',{exact:true}).waitFor();
    await page.getByText('Request',{exact:true}).click();
    await page.getByText('Request Review',{exact:true}).waitFor();
    await page.getByLabel('I Agree',{exact:true}).check();
    await saveJSON(intent,{pack:source.pack,url:source.url,price,autoRelease:true,time:new Date().toISOString()});
    await ok();
    await page.waitForFunction(()=>document.querySelector('[data-test=product-status]')?.innerText.trim()==='Waiting for Review',null,{timeout:60000});
  }
  await page.goto(source.url);
  await page.locator('[data-test=product-status]').waitFor();
  const actual = await status();
  if(!accepted.has(actual)) throw Error(`Review not confirmed: ${actual}`);
  await page.getByText('Start sales automatically',{exact:true}).waitFor();
  const receipt={pack:source.pack,url:source.url,count:source.count,status:actual,price,autoRelease:true,verifiedAt:new Date().toISOString()};
  await saveJSON(result,receipt);
  try {
    await page.bringToFront();
    await page.screenshot({path:result+'.png',fullPage:false,timeout:10000});
  } catch(error) {
    receipt.evidenceWarning=`Review status verified after reload; screenshot unavailable: ${error.name}`;
    await saveJSON(result,receipt);
  }
  console.log(JSON.stringify(receipt));
} finally { await browser.close(); }
