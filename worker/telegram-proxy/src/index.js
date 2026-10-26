/**
 * Zeus — Telegram webhook proxy mỏng (phương án A).
 *
 * Topology:
 *
 *   Telegram ──POST──▶ Cloudflare Worker (https://<worker>.workers.dev/telegram)
 *                             │  1) verify header X-Telegram-Bot-Api-Secret-Token (edge)
 *                             │  2) forward body + secret header nguyên vẹn
 *                             ▼
 *                Hermes gateway webhook server (0.0.0.0:8443/telegram)
 *
 * Nguyên tắc số 1: một bot token chỉ có MỘT consumer. Worker này KHÔNG gọi
 * getUpdates, KHÔNG gọi setWebhook, KHÔNG gọi bất kỳ model nào (Gemini/Veo/…).
 * Toàn bộ "bộ não" (model, memory, skills, cron) nằm ở Hermes gateway — Worker
 * chỉ là pass-through có kiểm tra secret ở edge (defense in depth).
 *
 * Biến môi trường (đặt bằng `wrangler secret put`, KHÔNG hardcode trong code):
 *   WEBHOOK_SECRET  — phải GIỐNG HỆT TELEGRAM_WEBHOOK_SECRET của Hermes.
 *   UPSTREAM_URL    — URL đầy đủ tới webhook server của Hermes, kể cả path.
 *                     Ví dụ: https://xxxx.trycloudflare.com/telegram
 *   WEBHOOK_PATH    — (non-secret var) path Worker lắng nghe; mặc định /telegram.
 */

const TELEGRAM_SECRET_HEADER = "x-telegram-bot-api-secret-token";

/**
 * Header không được chuyển tiếp khi trả response về client.
 *
 * Bug cũ: worker trả `resp.body` kèm NGUYÊN `resp.headers` của upstream. Khi
 * Cloudflare (hoặc Hermes) nén gzip, body đã được giải nén nhưng header vẫn ghi
 * `content-encoding: gzip` + `content-length` cũ -> client nhận response hỏng
 * (lỗi "ERR_CONTENT_DECODING_FAILED" / cắt cụt body).
 */
const DROP_RESPONSE_HEADERS = new Set([
  "content-encoding",
  "content-length",
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function sanitizeResponseHeaders(upstreamHeaders) {
  const headers = new Headers();
  for (const [key, value] of upstreamHeaders) {
    if (!DROP_RESPONSE_HEADERS.has(key.toLowerCase())) headers.set(key, value);
  }
  return headers;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

/**
 * So sánh hai chuỗi secret theo kiểu constant-time (đủ cho token ngắn của
 * Telegram; tránh so sánh `===` rò rỉ thông tin độ dài/sớm kết thúc).
 */
function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  const ab = new TextEncoder().encode(a);
  const bb = new TextEncoder().encode(b);
  if (ab.length !== bb.length) return false;
  let diff = 0;
  for (let i = 0; i < ab.length; i += 1) diff |= ab[i] ^ bb[i];
  return diff === 0;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const webhookPath = (env.WEBHOOK_PATH || "/telegram").trim();

    // Health check cho uptime monitor (UptimeRobot, Cloudflare warmup, v.v.).
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      return json({ ok: true, role: "zeus-telegram-webhook-proxy", webhookPath });
    }

    // Chỉ chấp nhận POST vào đúng path webhook.
    if (request.method !== "POST" || url.pathname !== webhookPath) {
      return json({ ok: false, error: "not found" }, 404);
    }

    // 1) Kiểm tra secret ở edge. Fail-closed: thiếu secret ⇒ 401.
    const provided = request.headers.get(TELEGRAM_SECRET_HEADER) || "";
    const expected = env.WEBHOOK_SECRET || "";
    if (!expected || !timingSafeEqual(provided, expected)) {
      console.warn("telegram-proxy: rejected request with bad/missing secret token");
      return json({ ok: false, error: "unauthorized" }, 401);
    }

    // 2) Forward nguyên vẹn về Hermes gateway.
    const upstream = (env.UPSTREAM_URL || "").trim();
    if (!upstream) {
      console.error("telegram-proxy: UPSTREAM_URL is not configured");
      return json({ ok: false, error: "UPSTREAM_URL is not configured" }, 503);
    }

    const headers = new Headers();
    headers.set("content-type", request.headers.get("content-type") || "application/json");
    // Chuyển tiếp đúng header secret để python-telegram-bot bên Hermes tự xác minh lại.
    headers.set(TELEGRAM_SECRET_HEADER, provided);

    try {
      const resp = await fetch(upstream, {
        method: "POST",
        headers,
        body: await request.arrayBuffer(),
        // UPSTREAM_URL phải là URL CUỐI CÙNG (https, không redirect) — không
        // để fetch âm thầm biến POST thành GET khi gặp 301/302.
        redirect: "manual",
      });

      return new Response(resp.body, {
        status: resp.status,
        statusText: resp.statusText,
        headers: sanitizeResponseHeaders(resp.headers),
      });
    } catch (err) {
      // Báo lỗi THẬT thay vì luôn trả 200 OK (lỗi cũ của worker cool-unit-a53f).
      const detail = err && err.message ? err.message : String(err);
      console.error("telegram-proxy: upstream unreachable:", detail);
      return json({ ok: false, error: "upstream unreachable", detail }, 502);
    }
  },
};
