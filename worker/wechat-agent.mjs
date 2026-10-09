import { readFile, writeFile, access } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

export function validateManifest(manifest) {
  if (
    manifest.mode !== "draft_only" ||
    manifest.approved !== true ||
    !["static", "animated"].includes(manifest.format)
  )
    throw Error("An approved draft-only manifest is required.");
  if (
    !Array.isArray(manifest.stickers) ||
    manifest.stickers.length < 8 ||
    manifest.stickers.length > 24
  )
    throw Error("Expected 8–24 reviewed stickers.");
  for (const item of manifest.stickers) {
    if (
      !/^stickers\/\d{2}\.(png|gif)$/.test(item.file) ||
      typeof item.meaning !== "string" ||
      !item.meaning.trim()
    )
      throw Error("Invalid sticker or meaning word.");
  }
  for (const key of ["title", "description", "copyright"])
    if (typeof manifest[key] !== "string" || !manifest[key].trim())
      throw Error("Missing " + key);
}

export async function stage(page, manifest, folder) {
  validateManifest(manifest);
  const url = new URL(page.url());
  if (
    url.hostname !== "sticker.weixin.qq.com" ||
    !url.pathname.endsWith("/stickerPage/detail") ||
    url.searchParams.has("stikerid")
  )
    throw Error(
      "Open your own empty new-album form. Existing works are never overwritten.",
    );
  if (await page.getByPlaceholder("输入含义词", { exact: true }).count())
    throw Error(
      "The form already has stickers. Inspect it manually instead of duplicating uploads.",
    );
  const type = manifest.format === "animated" ? "动态表情" : "静态表情";
  const radio = page.getByText(type, { exact: true });
  if ((await radio.count()) !== 1)
    throw Error(
      "Current platform format controls changed; inspect before uploading.",
    );
  await radio.click();
  const inputs = page.locator("input[type=file]");
  const accept = await inputs.first().getAttribute("accept");
  if (!accept?.includes(manifest.format === "animated" ? "gif" : "png"))
    throw Error("The selected upload control does not accept this format.");
  for (const item of manifest.stickers)
    await access(path.join(folder, item.file));
  await inputs
    .first()
    .setInputFiles(
      manifest.stickers.map((item) => path.join(folder, item.file)),
    );
  await page.waitForFunction(
    (n) =>
      document.querySelectorAll('input[placeholder="输入含义词"]').length === n,
    manifest.stickers.length,
    { timeout: 180000 },
  );
  for (let i = 0; i < manifest.stickers.length; i++)
    await page
      .getByPlaceholder("输入含义词", { exact: true })
      .nth(i)
      .fill(manifest.stickers[i].meaning);
  await page
    .getByPlaceholder("填写表情专辑名称", { exact: true })
    .fill(manifest.title);
  await page.locator("textarea").first().fill(manifest.description);
  await page
    .getByPlaceholder("填写版权信息", { exact: true })
    .fill(manifest.copyright);
  for (const [i, name] of [
    [1, "banner.jpg"],
    [2, "cover.png"],
    [3, "icon.png"],
  ]) {
    if ((await inputs.count()) <= i)
      throw Error(
        "Packaging controls changed. Uploaded artwork is preserved on the page.",
      );
    await inputs.nth(i).setInputFiles(path.join(folder, name));
  }
  const values = await page
    .getByPlaceholder("输入含义词", { exact: true })
    .evaluateAll((nodes) => nodes.map((x) => x.value));
  if (
    JSON.stringify(values) !==
    JSON.stringify(manifest.stickers.map((x) => x.meaning))
  )
    throw Error("Meaning words do not match.");
  await page.screenshot({
    path: path.join(folder, "staged.png"),
    fullPage: true,
  });
  // This is the only final action. No review/submit locator exists in this agent.
  const save = page.getByRole("button", { name: "保存", exact: true });
  if ((await save.count()) !== 1)
    throw Error(
      "Save control changed. Materials are staged; review them manually.",
    );
  await writeFile(
    path.join(folder, "receipt.json"),
    JSON.stringify({
      status: "save_intent",
      message:
        "Inspect the same browser after an interrupted save; do not upload twice.",
    }),
  );
  await save.click();
  await page
    .getByText("保存成功", { exact: false })
    .first()
    .waitFor({ timeout: 120000 });
  const saved = new URL(page.url()).searchParams.get("stikerid");
  if (!saved)
    throw Error(
      "Save has no draft ID. Inspect the same work before continuing.",
    );
  await page.reload();
  await page.getByPlaceholder("填写表情专辑名称", { exact: true }).waitFor();
  if (
    (await page
      .getByPlaceholder("填写表情专辑名称", { exact: true })
      .inputValue()) !== manifest.title
  )
    throw Error("Saved title was not verified.");
  const after = await page
    .getByPlaceholder("输入含义词", { exact: true })
    .evaluateAll((nodes) => nodes.map((x) => x.value));
  if (JSON.stringify(after) !== JSON.stringify(values))
    throw Error("Saved meaning words were not verified.");
  return {
    status: "saved_draft_not_submitted",
    draft: saved,
    message:
      "Draft saved. Only you can confirm rights and submit it for review.",
  };
}

async function main() {
  const folder = process.env.WORK_DIR || "/work";
  const manifest = JSON.parse(
    await readFile(path.join(folder, "manifest.json"), "utf8"),
  );
  validateManifest(manifest);
  try {
    await access(path.join(folder, "receipt.json"));
    throw Error(
      "A receipt already exists. Reconcile the same draft, do not upload again.",
    );
  } catch (e) {
    if (e.code !== "ENOENT") throw e;
  }
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const page = browser
    .contexts()[0]
    .pages()
    .find((p) => p.url().startsWith("https://sticker.weixin.qq.com/"));
  if (!page)
    throw Error(
      "Open the WeChat Sticker Platform and sign in in your isolated browser.",
    );
  try {
    const result = await stage(page, manifest, folder);
    await writeFile(
      path.join(folder, "receipt.json"),
      JSON.stringify(result, null, 2),
    );
    console.log(result.status);
  } catch (e) {
    await writeFile(
      path.join(folder, "attention.json"),
      JSON.stringify(
        { message: e.message, status: "needs_user_attention" },
        null,
        2,
      ),
    );
    throw e;
  } finally {
    await browser.close();
  }
}
if (
  process.argv[1] &&
  fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
)
  main().catch((e) => {
    console.error(e.message);
    process.exitCode = 1;
  });
