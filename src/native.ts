import { Capacitor } from "@capacitor/core";
import { Directory, Filesystem } from "@capacitor/filesystem";
import { Share } from "@capacitor/share";
import { API, type Sticker, type Pack } from "./api";

export async function saveSticker(
  pack: Pack,
  sticker: Sticker,
  language: string,
) {
  if (!Capacitor.isNativePlatform()) {
    location.href =
      API + `/api/default/${pack.id}/sticker/${language}/${sticker.id}`;
    return;
  }
  const url = new URL(sticker.gif);
  if (
    url.origin !== "https://aya.lazying.art" ||
    !url.pathname.startsWith("/media/")
  )
    throw Error("Untrusted download.");
  const file = `westicker-${pack.id}-${language}-${sticker.id}.gif`;
  // Pinned filesystem supports this API; qualify FileTransfer before store release.
  await Filesystem.downloadFile({
    url: sticker.gif,
    path: file,
    directory: Directory.Cache,
  });
  const result = await Filesystem.getUri({
    path: file,
    directory: Directory.Cache,
  });
  await Share.share({
    title: sticker.label,
    files: [result.uri],
    dialogTitle: "Save or share your sticker",
  });
}
