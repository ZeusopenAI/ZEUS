# Deploy lên Vercel — kiến trúc tách đôi

Mục tiêu: **Vercel quản lý phần người dùng nhìn thấy** (site, dashboard, API nhẹ),
**VPS quản lý bộ não** (Hermes gateway, FlowKit API, SQLite).

```
┌──────────────────────── VERCEL (CDN toàn cầu) ────────────────────────┐
│  Project 1: zeus-site         Root = site/          (static, no build) │
│  Project 2: zeus-flowkit-dash Root = flowkit/dashboard (Vite + proxy)  │
│         │                                                             │
│         └── /api/*  →  serverless proxy (api/[...path].ts)            │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼───────────────────────────────────────┐
│  VPS / Docker (24/7, có ổ đĩa)                                        │
│    • Hermes gateway  → ~/.hermes/state.db, skills/, cron              │
│    • FlowKit FastAPI → SQLite, /ws/dashboard (WebSocket)              │
│    • Cloudflare Worker: Telegram webhook → Hermes                     │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Vì sao Hermes KHÔNG nằm trên Vercel

| Hermes cần | Vercel cung cấp |
|---|---|
| Process chạy 24/7 (gateway, systemd) | Serverless: function ngủ sau mỗi request; tối đa 60s (Hobby) / 300s (Pro) |
| `~/.hermes/state.db` (SQLite WAL, ghi liên tục) | Filesystem tạm, mất sau mỗi lần chạy |
| Telegram long-polling (`start_polling()`) | Không có process nền |
| Ghi `~/.hermes/skills/` lúc chạy | Chỉ đọc, đóng gói lúc build |
| Terminal/shell, browser CDP, cron | Bị chặn / không tồn tại |
| `pip install ./agents/hermes` (nhiều deps) | Giới hạn dung lượng, không systemd |

Nếu muốn thay VPS bằng một nền tảng PaaS: **Railway / Fly.io / Render** — đều chạy
Docker 24/7 và có volume bền cho `state.db`.

---

## 1. Project 1 — Landing page (`site/`)

Đã có `site/vercel.json`: static, không build, có security headers và cache cho `assets/`.

**Trên vercel.com:**

1. *Add New… → Project* → Import `ZeusopenAI/ZEUS`
2. **Root Directory** = `site`  ← quan trọng
3. **Framework Preset** = `Other`
4. Build Command / Output Directory / Install Command: **để trống**
5. *Deploy*

Kết quả: `https://<project>.vercel.app` chạy đúng `index.html` + `assets/`.

**Gắn domain:** *Settings → Domains* → thêm `quangquy.ai` (và `www`).
Nếu tên miền đang trỏ GitHub Pages, phải đổi DNS sang Vercel — **đừng chạy song song
2 nơi phát hành cùng một domain**.

> ⚠️ Sau khi `site/index.html` đổi domain, nhớ sửa các thẻ `canonical`, `og:url`,
> và `site/sitemap.xml` cho khớp domain mới (hiện đang là `https://quangquy.ai/`).

---

## 2. Project 2 — FlowKit dashboard (`flowkit/dashboard`)

Đã có `flowkit/dashboard/vercel.json` (Vite, output `dist`, SPA rewrite) và
`flowkit/dashboard/api/[...path].ts` — serverless proxy chuyển `/api/*` về backend trên VPS.

**Trên vercel.com:**

1. *Add New… → Project* → Import `ZeusOpenAI/ZEUS` (lần nữa, project thứ hai)
2. **Root Directory** = `flowkit/dashboard`
3. **Framework Preset** = `Vite` (tự nhận từ `vercel.json`)
4. **Environment Variables**:

| Biến | Bắt buộc | Ví dụ | Ghi chú |
|---|---|---|---|
| `FLOWKIT_API_BASE` | ✅ | `https://flowkit.quangquy.ai` | Không có `/` ở cuối |
| `FLOWKIT_API_TOKEN` | nếu backend yêu cầu | chuỗi ngẫu nhiên | Proxy gửi qua header `X-Proxy-Token` |
| `VITE_WS_BASE` | để có realtime | `wss://flowkit.quangquy.ai` | **Build-time**: phải set trước khi build, đổi phải redeploy |

5. *Deploy*

### Giới hạn đã biết

- **WebSocket không đi qua serverless function.** Vì vậy `VITE_WS_BASE` phải trỏ
  thẳng tới backend (đã hỗ trợ trong `src/api/useWebSocket.ts`).
- Function timeout (Hobby 60s). Tác vụ dài (render video) phải gọi thẳng backend
  hoặc chạy job nền rồi polling.
- Proxy chỉ là chuyển tiếp: dữ liệu vẫn nằm trong SQLite trên VPS.

---

## 3. Deploy tự động (tuỳ chọn)

Nếu không muốn bấm trên web, dùng `.github/workflows/deploy-vercel.yml`
(chạy **thủ công** — đúng quy tắc AGENTS.md: deploy production phải do chủ tài khoản xác nhận).

Cần thêm secrets vào GitHub (*Settings → Secrets and variables → Actions*):

| Secret | Lấy ở đâu |
|---|---|
| `VERCEL_TOKEN` | vercel.com → Account Settings → Tokens |
| `VERCEL_ORG_ID` | chạy `vercel link` ở máy, xem `.vercel/project.json` |
| `VERCEL_PROJECT_ID_SITE` | id project `site` |
| `VERCEL_PROJECT_ID_DASHBOARD` | id project dashboard |

Chạy: tab **Actions** → *Deploy Vercel* → **Run workflow** → chọn `site` / `dashboard` / `both`
và `preview` / `production`.

> Không có token vẫn ổn: Vercel tự build mỗi lần push `main` sau khi đã import project
> (Git integration). Workflow này chỉ để chủ động deploy/rollback.

---

## 4. Vai trò của GitHub Pages

`.github/workflows/deploy-quangquy-site.yml` (thủ công) vẫn giữ được làm **bản dự phòng**.
Chỉ nên dùng **một** trong hai làm nơi phát hành chính cho domain thật.

---

## 5. Kiểm tra sau khi deploy

```bash
# Site sống?
curl -sI https://<project>.vercel.app | head -3

# Dashboard trả HTML?
curl -s https://<dash>.vercel.app | grep -o '<title>[^<]*</title>'

# Proxy có tới backend không? (200 = OK, 502 = chưa đặt FLOWKIT_API_BASE / backend chết)
curl -s -o /dev/null -w '%{http_code}\n' https://<dash>.vercel.app/api/health

# Realtime tới đúng backend?
#   Mở DevTools → Network → WS → phải thấy kết nối tới wss://<backend>/ws/dashboard
```

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Trang trắng, 404 toàn bộ | Root Directory sai | Đặt lại `site` hoặc `flowkit/dashboard` |
| `/api/*` trả 502 `FLOWKIT_API_BASE chưa được đặt` | Thiếu env | Thêm env → **Redeploy** (env chỉ áp dụng cho lần build sau) |
| Dashboard build fail `tsc` | Type lỗi trong `src/` | Chạy `npm run build` ở máy để xem lỗi |
| Realtime không chạy | Thiếu `VITE_WS_BASE` | Set env rồi redeploy (biến này nhúng vào bundle lúc build) |
| Sửa `site/` mà Vercel không đổi | Project đang trỏ nhầm root | Kiểm *Settings → General → Root Directory* |

---

## 5b. Project cấu hình sai ở gốc repo (`vercel.json` gốc)

Repo có **hai** `vercel.json`: `site/vercel.json` và `flowkit/dashboard/vercel.json`.
Nếu một project trên Vercel để **Root Directory = gốc repo** (mặc định khi import
mà không sửa), nó không thấy file cấu hình nào và build/deploy hỏng ngay (check
`Vercel – <project>` đỏ trong 0s, không có log build).

Để gốc repo cũng deploy được (phục vụ landing page trong `site/`), repo có thêm
`vercel.json` ở gốc:

```json
{ "framework": null, "outputDirectory": "site", "cleanUrls": true, "trailingSlash": false }
```

`framework: null` = preset **Other** (Vercel không cố đoán framework), còn
`outputDirectory: site` trỏ output về thư mục site tĩnh. Project nào đã đặt
Root = `site` hoặc `flowkit/dashboard` thì file này **không ảnh hưởng** (Vercel
chỉ đọc `vercel.json` nằm trong Root Directory của project).

Nếu vẫn đỏ sau khi merge, nguyên nhân nằm phía Vercel (project bị pause, bị
chặn deploy, hoặc chưa cấp quyền) — kiểm tra *Settings → General* của project
đó, hoặc xoá project thừa: **mỗi repo chỉ nên có 2 project** (`site`,
`flowkit/dashboard`).

---

## 6. Checklist

- [ ] Import project `site` (Root = `site`)
- [ ] Gắn domain + sửa `canonical` / `sitemap.xml` nếu đổi domain
- [ ] Import project dashboard (Root = `flowkit/dashboard`)
- [ ] Đặt `FLOWKIT_API_BASE`, `FLOWKIT_API_TOKEN`, `VITE_WS_BASE` → Redeploy
- [ ] Kiểm `/api/health` và WebSocket
- [ ] (Tuỳ chọn) thêm `VERCEL_TOKEN` để dùng workflow deploy thủ công
- [ ] Xác nhận Hermes vẫn chạy trên VPS: `bash scripts/hermes-doctor.sh`
