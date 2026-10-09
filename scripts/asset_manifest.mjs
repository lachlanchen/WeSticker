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
const hash = createHash("sha256");
for (const file of files) hash.update(await readFile("dist" + file));
const version = hash.digest("hex").slice(0, 16);
await writeFile("dist/asset-manifest.json", JSON.stringify({ version, files }));
await writeFile(
  "dist/sw.js",
  (await readFile("public/sw.js", "utf8")).replace("__BUILD_HASH__", version),
);
console.log(`Offline shell: ${files.length} files, ${version}`);
