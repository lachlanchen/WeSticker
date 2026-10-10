import { readdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
async function walk(dir) {
  let result = [];
  for (const f of await readdir(dir, { withFileTypes: true })) {
    const name = path.join(dir, f.name);
    if (f.isDirectory()) result.push(...(await walk(name)));
    else if (!["sw.js", "asset-manifest.json"].includes(f.name))
      result.push("/" + path.relative("dist", name));
  }
  return result;
}
const files = (await walk("dist")).sort();
const base = process.env.WESTICKER_BASE || "/";
if (!/^\/[a-zA-Z0-9/-]*$/.test(base) || !base.endsWith("/"))
  throw Error("Invalid base path");
const catalog = JSON.parse(await readFile("dist/catalog.json", "utf8"));
try {
  const { previews } = JSON.parse(
    await readFile("dist/motion/manifest.json", "utf8"),
  );
  for (const pack of catalog.packs)
    for (const stickers of Object.values(pack.stickers)) {
      for (const sticker of stickers) {
        const entry = previews[sticker.gif];
        if (entry) sticker.motion = entry.preview;
      }
    }
  await writeFile("dist/catalog.json", JSON.stringify(catalog));
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}
const firstPosters = new Set(
  catalog.packs.flatMap((p) =>
    Object.values(p.stickers).map((s) => s[0]?.poster),
  ),
);
for (const sticker of catalog.packs[0].stickers.zh)
  firstPosters.add(sticker.poster);
const precache = files.filter(
  (f) =>
    !f.startsWith("/motion/") &&
    (!f.startsWith("/previews/") || firstPosters.has(f)),
);
const hash = createHash("sha256");
hash.update(base);
hash.update(await readFile("public/sw.js"));
hash.update(JSON.stringify(precache));
for (const file of files) hash.update(await readFile("dist" + file));
const version = hash.digest("hex").slice(0, 16);
await writeFile(
  "dist/asset-manifest.json",
  JSON.stringify({ version, files: precache.map((f) => base + f.slice(1)) }),
);
const manifest = JSON.parse(
  await readFile("dist/manifest.webmanifest", "utf8"),
);
manifest.id = manifest.scope = manifest.start_url = base;
manifest.icons = manifest.icons.map((i) => ({
  ...i,
  src: base + i.src.slice(1),
}));
await writeFile("dist/manifest.webmanifest", JSON.stringify(manifest));
await writeFile(
  "dist/sw.js",
  (await readFile("public/sw.js", "utf8")).replace("__BUILD_HASH__", version),
);
console.log(
  `Offline shell: ${precache.length}/${files.length} files precached, ${version}, scope ${base}`,
);
