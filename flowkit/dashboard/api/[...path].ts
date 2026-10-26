// Serverless proxy: /api/* → FlowKit backend (chạy trên VPS, không chạy trên Vercel).
//
// Vì sao cần: dashboard gọi API same-origin (`BASE = ''` trong src/api/client.ts),
// nên trên Vercel phải có lớp chuyển tiếp. Vercel chỉ làm "mặt tiền"; bộ não
// (FastAPI + SQLite) vẫn nằm trên VPS.
//
// Biến môi trường (Vercel → Project → Settings → Environment Variables):
//   FLOWKIT_API_BASE   ví dụ: https://flowkit.example.com   (KHÔNG có / ở cuối)
//   FLOWKIT_API_TOKEN  (tuỳ chọn) token dùng chung; sẽ gửi qua header X-Proxy-Token
//
// Giới hạn đã biết:
//   - WebSocket KHÔNG đi qua được serverless function. Dashboard cần đặt
//     VITE_WS_BASE trỏ thẳng tới backend để có realtime (xem src/api/useWebSocket.ts).
//   - Function có timeout (Hobby 60s). Tác vụ dài (render video) phải gọi trực tiếp
//     backend hoặc dùng job + polling.

export const config = { runtime: 'edge' };

const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'host',
]);

export default async function handler(request: Request): Promise<Response> {
  const base = (process.env.FLOWKIT_API_BASE || '').replace(/\/+$/, '');

  if (!base) {
    return Response.json(
      {
        error: 'FLOWKIT_API_BASE chưa được đặt',
        hint: 'Vercel → Project → Settings → Environment Variables → thêm FLOWKIT_API_BASE (https://backend-cua-ban)',
      },
      { status: 502 },
    );
  }

  const url = new URL(request.url);
  const target = `${base}${url.pathname}${url.search}`;

  const headers = new Headers();
  for (const [key, value] of request.headers) {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  }

  // Xác thực phía backend: chỉ chấp nhận request đến từ proxy này.
  const token = process.env.FLOWKIT_API_TOKEN;
  if (token) headers.set('X-Proxy-Token', token);
  // Backend không nên thấy origin của Vercel như thể là client thật.
  headers.set('X-Forwarded-Host', url.host);

  const hasBody = !['GET', 'HEAD'].includes(request.method);

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: 'manual',
    });

    const responseHeaders = new Headers();
    for (const [key, value] of upstream.headers) {
      const name = key.toLowerCase();
      // `content-length` của upstream không còn đúng sau khi fetch giải nén body
      // (và có thể làm client cắt cụt response) -> bỏ, để runtime tự tính lại.
      if (!HOP_BY_HOP.has(name) && name !== 'content-encoding' && name !== 'content-length') {
        responseHeaders.set(key, value);
      }
    }
    responseHeaders.set('Cache-Control', 'no-store');

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    return Response.json(
      {
        error: 'Không gọi được FlowKit backend',
        detail: error instanceof Error ? error.message : String(error),
        target_base: base,
      },
      { status: 502 },
    );
  }
}
