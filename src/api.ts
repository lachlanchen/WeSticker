export const API = import.meta.env.VITE_API_ORIGIN || "";
let csrf = "";
export function setCSRF(value: string) {
  csrf = value || "";
}
export async function api<T = any>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const headers: Record<string, string> = {};
  const multipart = body instanceof FormData;
  if (body !== undefined && !multipart)
    headers["Content-Type"] = "application/json";
  if (csrf) headers["X-CSRF-Token"] = csrf;
  const result = await fetch(API + path, {
    method: method || (body === undefined ? "GET" : "POST"),
    credentials: "include",
    headers,
    body:
      body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  });
  const value = await result.json();
  if (!result.ok)
    throw Error(value.error || "Something went wrong. Please try again.");
  return value;
}
export type Sticker = {
  id: string;
  label: string;
  gif: string;
  poster: string;
  motion?: string;
};
export type Pack = {
  id: string;
  name: string;
  english: string;
  description: string;
  count: number;
  tag: string;
  banner: string;
  cover: string;
  stickers: Record<string, Sticker[]>;
};
export type Item = {
  id: string;
  label: string;
  asset: string | null;
  approved: boolean;
  action?: string;
};
export type Draft = {
  id: string;
  title: string;
  theme: string;
  language: string;
  status: string;
  items: Item[];
  revision: number;
};
export type Character = {
  id: string;
  name: string;
  style: string;
  refs: string[];
  locked: boolean;
};
export type Job = {
  id: string;
  pack_id: string;
  state: string;
  progress: number;
  error?: string;
  kind?: string;
};
export type Boot = {
  user: null | {
    id: string;
    name: string;
    plan: string;
    credits: number;
    expires: number;
    payout_ready: number;
    consented: number;
  };
  csrf: string;
  local_accounts: boolean;
  providers: string[];
  plans: {
    id: string;
    name: string;
    cents: number;
    credits: number;
    features: string[];
  }[];
  themes: Record<string, Record<string, string[]>>;
  capabilities: Record<string, boolean>;
};
