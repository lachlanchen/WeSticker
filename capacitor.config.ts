import type { CapacitorConfig } from "@capacitor/cli";
const config: CapacitorConfig = {
  appId: "art.lazying.westicker",
  appName: "WeSticker",
  webDir: "dist",
  ios: { contentInset: "automatic" },
  android: { allowMixedContent: false },
  server: { androidScheme: "https" },
};
export default config;
