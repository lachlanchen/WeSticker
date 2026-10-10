import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

function fixture() {
  const images = [],
    timers = new Map();
  let id = 0;
  class Image {
    constructor() {
      images.push(this);
    }
    set src(value) {
      this.value = value;
    }
    get src() {
      return this.value;
    }
  }
  const context = vm.createContext({
    exports: {},
    Image,
    setTimeout: (fn) => {
      timers.set(++id, fn);
      return id;
    },
    clearTimeout: (key) => timers.delete(key),
  });
  const source = ts.transpileModule(
    readFileSync("src/previewQueue.ts", "utf8"),
    {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
    },
  ).outputText;
  vm.runInContext(source, context);
  return { transfer: context.exports.previewTransfer, images, timers };
}

test("at most three transfers, successful completion admits the next job", () => {
  const f = fixture(),
    ready = [];
  for (let i = 0; i < 5; i++) f.transfer(`gif-${i}`, () => ready.push(i));
  assert.equal(f.images.filter((i) => i.src).length, 3);
  f.images[0].onload();
  assert.deepEqual(ready, [0]);
  assert.equal(f.images[3].src, "gif-3");
  assert.equal(f.timers.size, 3);
});

test("cancelled queued work never starts and active cancellation frees one slot", () => {
  const f = fixture();
  const cancels = Array.from({ length: 5 }, (_, i) =>
    f.transfer(`gif-${i}`, () => assert.fail()),
  );
  cancels[3]();
  cancels[0]();
  cancels[0]();
  assert.equal(f.images[0].src, "");
  assert.equal(f.images[3].src, undefined);
  assert.equal(f.images[4].src, "gif-4");
  assert.equal(f.timers.size, 3);
});

test("errors and timeout free slots without reporting a loaded image", () => {
  const f = fixture();
  for (let i = 0; i < 6; i++) f.transfer(`gif-${i}`, () => assert.fail());
  f.images[0].onerror();
  assert.equal(f.images[3].src, "gif-3");
  f.timers.values().next().value();
  assert.equal(f.images[4].src, "gif-4");
  assert.equal(f.timers.size, 3);
});

test("visible top row takes priority over queued lower rows", () => {
  const f = fixture();
  for (let i = 0; i < 3; i++) f.transfer(`active-${i}`, () => {});
  f.transfer("lower-row", () => {}, 1000);
  f.transfer("top-row", () => {}, 50);
  f.images[0].onload();
  assert.equal(f.images[3].src, undefined);
  assert.equal(f.images[4].src, "top-row");
});
