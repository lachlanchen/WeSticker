import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateManifest,stage} from '../worker/wechat-agent.mjs';
const valid={mode:'draft_only',approved:true,format:'static',title:'Daily',description:'Daily hellos',copyright:'Creator',stickers:Array.from({length:8},(_,i)=>({file:`stickers/0${i+1}.png`,meaning:'你好'}))};
test('draft manifest requires approval, bounded paths and count',()=>{
 assert.doesNotThrow(()=>validateManifest(valid));
 for(const patch of [{mode:'submit'},{approved:false},{stickers:[]},{stickers:[...valid.stickers.slice(1),{file:'../private.png',meaning:'Hello'}]}])assert.throws(()=>validateManifest({...valid,...patch}));
});
test('existing or unrelated works are never edited',async()=>{
 for(const url of ['https://example.com/stickerPage/detail','https://sticker.weixin.qq.com/stickerPage/detail?stikerid=other-owner','https://sticker.weixin.qq.com/login']){
  await assert.rejects(stage({url:()=>url},valid,'/unused'));
 }
});
