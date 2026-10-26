/**
 * Test cho Cloudflare Worker proxy Telegram → Hermes gateway.
 *
 * Không cần wrangler/miniflare: worker chỉ dùng `Request`/`Response`/`fetch`
 * toàn cục (có sẵn từ Node 18+), nên stub `fetch` là đủ.
 *
 *   npm test --prefix worker/telegram-proxy
 */

import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import worker from "../src/index.js";

const SECRET = "s3cr3t-token-abc123";
const UPSTREAM = "https://hermes.example.com/telegram";
const realFetch = globalThis.fetch;
let calls = [];

function stubFetch(handler) {
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return handler(url, init);
  };
}

function makeRequest({ method = "POST", path = "/telegram", secret = SECRET, body = '{"update_id":1}' } = {}) {
  const headers = { "content-type": "application/json" };
  if (secret !== null) headers["x-telegram-bot-api-secret-token"] = secret;
  // GET/HEAD không được có body theo spec của fetch.
  const payload = ["GET", "HEAD"].includes(method) ? undefined : body;
  return new Request(`https://zeus-worker.example.workers.dev${path}`, { method, headers, body: payload });
}

function env(overrides = {}) {
  return { WEBHOOK_SECRET: SECRET, UPSTREAM_URL: UPSTREAM, ...overrides };
}

beforeEach(() => {
  calls = [];
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

test("GET /health trả 200 và không cần secret", async () => {
  const res = await worker.fetch(makeRequest({ method: "GET", path: "/health", secret: null }), env());
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), {
    ok: true,
    role: "zeus-telegram-webhook-proxy",
    webhookPath: "/telegram",
  });
});

test("path khác webhook -> 404, không gọi upstream", async () => {
  stubFetch(() => new Response("x"));
  const res = await worker.fetch(makeRequest({ path: "/nope" }), env());
  assert.equal(res.status, 404);
  assert.equal(calls.length, 0);
});

test("thiếu secret -> 401 (fail-closed)", async () => {
  stubFetch(() => new Response("x"));
  const res = await worker.fetch(makeRequest({ secret: null }), env());
  assert.equal(res.status, 401);
  assert.equal(calls.length, 0);
});

test("secret sai độ dài khác nhau -> 401", async () => {
  stubFetch(() => new Response("x"));
  const res = await worker.fetch(makeRequest({ secret: "short" }), env());
  assert.equal(res.status, 401);
  assert.equal(calls.length, 0);
});

test("env.WEBHOOK_SECRET rỗng -> 401 (không cho pass-through)", async () => {
  stubFetch(() => new Response("x"));
  const res = await worker.fetch(makeRequest(), env({ WEBHOOK_SECRET: "" }));
  assert.equal(res.status, 401);
  assert.equal(calls.length, 0);
});

test("thiếu UPSTREAM_URL -> 503", async () => {
  stubFetch(() => new Response("x"));
  const res = await worker.fetch(makeRequest(), env({ UPSTREAM_URL: "" }));
  assert.equal(res.status, 503);
  assert.equal(calls.length, 0);
});

test("secret đúng -> forward POST + secret header, giữ status/body upstream", async () => {
  stubFetch(
    () =>
      new Response('{"ok":true}', {
        status: 202,
        headers: { "content-type": "application/json", "x-upstream-id": "abc" },
      }),
  );

  const res = await worker.fetch(makeRequest(), env());

  assert.equal(res.status, 202);
  assert.equal(await res.text(), '{"ok":true}');
  assert.equal(res.headers.get("x-upstream-id"), "abc");

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, UPSTREAM);
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.redirect, "manual");
  const sent = new Headers(calls[0].init.headers);
  assert.equal(sent.get("x-telegram-bot-api-secret-token"), SECRET);
  assert.equal(sent.get("content-type"), "application/json");
});

test("bỏ content-encoding/content-length/transfer-encoding của upstream", async () => {
  stubFetch(
    () =>
      new Response("plain body", {
        status: 200,
        headers: {
          "content-encoding": "gzip",
          "content-length": "999",
          "transfer-encoding": "chunked",
          "cache-control": "no-store",
        },
      }),
  );

  const res = await worker.fetch(makeRequest(), env());

  assert.equal(await res.text(), "plain body");
  assert.equal(res.headers.get("content-encoding"), null);
  assert.equal(res.headers.get("content-length"), null);
  assert.equal(res.headers.get("transfer-encoding"), null);
  assert.equal(res.headers.get("cache-control"), "no-store");
});

test("upstream lỗi mạng -> 502 kèm detail, không lộ secret", async () => {
  stubFetch(() => {
    throw new Error("ECONNREFUSED");
  });

  const res = await worker.fetch(makeRequest(), env());

  assert.equal(res.status, 502);
  const payload = await res.json();
  assert.equal(payload.ok, false);
  assert.match(payload.detail, /ECONNREFUSED/);
  assert.ok(!JSON.stringify(payload).includes(SECRET));
});

test("webhookPath tuỳ chỉnh từ env được tôn trọng", async () => {
  stubFetch(() => new Response("ok", { status: 200 }));
  const custom = env({ WEBHOOK_PATH: "/tg/hook" });

  const ok = await worker.fetch(makeRequest({ path: "/tg/hook" }), custom);
  assert.equal(ok.status, 200);
  assert.equal(calls.length, 1);

  calls = [];
  const notFound = await worker.fetch(makeRequest({ path: "/telegram" }), custom);
  assert.equal(notFound.status, 404);
  assert.equal(calls.length, 0);
});
