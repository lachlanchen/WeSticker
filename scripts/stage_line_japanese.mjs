// Saves uploads only. Review submission remains a separate observed UI action.
import { chromium } from 'playwright-core';
import fs from 'node:fs/promises';
import path from 'node:path';
import { parseArgs } from 'node:util';
const { values: args } = parseArgs({ options: {
  cdp: {type:'string'}, pack: {type:'string'}, assets: {type:'string'}, receipt: {type:'string'},
}});
for (const key of ['cdp','pack','assets','receipt']) if (!args[key]) throw Error(`Missing --${key}`);
const metadata = JSON.parse(await fs.readFile(new URL('./line_japanese_metadata.json', import.meta.url)))[args.pack];
const manifest = JSON.parse(await fs.readFile(path.join(args.assets, 'manifest.json')));
if (!metadata || manifest.pack !== args.pack || manifest.language !== 'ja') throw Error('Wrong pack');
const count = manifest.stickers.length;
if (![8,16,24].includes(count)) throw Error('Invalid LINE count');
await fs.mkdir(path.dirname(args.receipt), {recursive:true});
async function read(file) { try{return JSON.parse(await fs.readFile(file));} catch(e){if(e.code==='ENOENT')return null;throw e;} }
async function write(file,value) {await fs.writeFile(file, JSON.stringify(value,null,2)+'\n',{mode:0o600});}
const saved = await read(args.receipt);
const intent = args.receipt+'.create-intent';
const browser = await chromium.connectOverCDP(args.cdp);
try {
  const page = browser.contexts()[0].pages().find(p=>/^https:\/\/creator\.line\.me\/my\/[^/]+\/sticker\//.test(p.url()));
  if (!page) throw Error('Open the authorized LINE sticker tab first');
  page.setDefaultTimeout(12000);
  async function type(name,value) {
    const field = page.locator(`[name="${name}"]`);
    await field.fill(''); await field.pressSequentially(value,{delay:2}); await field.press('Tab');
  }
  async function ok() {await page.getByRole('button',{name:'OK',exact:true}).filter({visible:true}).click();}
  let url = saved?.url;
  if (url) {
    if (saved.pack!==args.pack || !/^https:\/\/creator\.line\.me\/my\/[^/]+\/sticker\/\d+$/.test(url)) throw Error('Invalid existing receipt');
    await page.goto(url);
  } else {
    if (await read(intent)) throw Error('Unresolved create intent; reconcile existing items before retry');
    await page.locator('a[href$="/create"]').click();
    await page.locator('a[href$="/sticker/create"]').click();
    await page.locator('input[name=sticker_type][value=animation]').check();
    await type('meta[en][title]',metadata.en);
    await type('meta[en][description]',metadata.description_en);
    await page.locator('select').filter({has:page.locator('option',{hasText:/^Japanese$/})}).first().selectOption({label:'Japanese'});
    await page.getByRole('button',{name:'Add',exact:true}).first().click();
    await type('meta[ja][title]',metadata.ja);
    await type('meta[ja][description]',metadata.description_ja);
    if (!(await page.locator('body').innerText()).includes('LazyingArt')) throw Error('Verified creator name not selected');
    await type('copyright','LazyingArt LLC');
    await page.locator('input[name=is_ai_generated][value=true]').check();
    await page.locator('select').filter({has:page.locator('option',{hasText:/^Cute$/})}).selectOption({label:'Cute'});
    await page.locator('select').filter({has:page.locator('option',{hasText:/^Pandas$/})}).selectOption({label:args.pack==='vol-04'?'Other':'Pandas'});
    await page.locator('input[name=area_group][value=all]').check();
    await page.locator('input[name=is_auto_release][value=false]').check();
    await type('design_url',`https://aya.lazying.art/pack/${args.pack}`);
    await type('request_comment','Original LazyingArt characters: Aya (red panda), Lala (panda), Sasa, and Zhuangzi the robot. AI-assisted animation edited and reviewed by the creator. Japanese lettering; no private-person photographs.');
    await page.getByText('Save',{exact:true}).click();
    await page.getByText('Save this form?',{exact:true}).waitFor();
    await write(intent,{pack:args.pack,time:new Date().toISOString(),action:'save draft'});
    await ok();
    await page.waitForURL(u=>/\/sticker\/\d+$/.test(u.pathname));
    url=page.url();
    await write(args.receipt,{pack:args.pack,url,status:'draft-created',count});
  }
  await page.getByRole('button',{name:'Sticker Images',exact:true}).click();
  await page.locator('a[href$="/image"]').click();
  await page.locator('select').first().waitFor();
  if (await page.locator('select').first().inputValue()!==String(count)) {
    await page.locator('select').first().selectOption({label:String(count)});await ok();
  }
  await page.locator(`#upload-file-input-${String(count).padStart(2,'0')}`).waitFor({state:'attached'});
  const existing=await page.locator('canvas.cm-apng-player-canvas').count();
  if (existing===0) {
    await write(args.receipt,{pack:args.pack,url,status:'upload-intent',count});
    await page.locator('input[type=file][name=file]').setInputFiles(path.join(args.assets,'line-upload.zip'));
  } else if(existing!==count+1) throw Error(`Partial upload ${existing}; inspect rather than overwrite`);
  await page.waitForFunction(n=>document.querySelectorAll('canvas.cm-apng-player-canvas').length===n,count+1,{timeout:120000});
  await page.reload();
  await page.waitForFunction(n=>document.querySelectorAll('canvas.cm-apng-player-canvas').length===n,count+1,{timeout:30000});
  const errors=(await page.locator('.cm-product-image-error').allTextContents()).filter(s=>s.trim());
  if(errors.length) throw Error('Remote image validation: '+errors.join('; '));
  await page.screenshot({path:args.receipt+'.png',fullPage:true,timeout:60000});
  await write(args.receipt,{pack:args.pack,url,status:'uploaded-draft',count,remoteAnimatedImages:count+1,verifiedAt:new Date().toISOString()});
  console.log(JSON.stringify({pack:args.pack,url,status:'uploaded-draft',count}));
} finally {await browser.close();}
