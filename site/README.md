# Landing page — Nguyễn Quang Quý

Site tĩnh (HTML + CSS + JS thuần, **không cần build step**) cho thương hiệu cá nhân
**Nguyễn Quang Quý — AI Creator · Digital Marketing**.

Bản này là bản **code lại và mở rộng** nội dung từ trang Google Sites cũ.

---

## 1. Cấu trúc

```text
site/
├── index.html              # Toàn bộ trang (1 trang, nhiều section)
├── assets/
│   ├── css/styles.css      # Design system: token → component → section → responsive
│   ├── js/
│   │   ├── chat-demo.js    # Demo chatbot AI (mô phỏng phía trình duyệt, không gọi API)
│   │   └── app.js          # Nav, carousel, countdown, hoa đào, form, terminal animation…
│   └── img/
│       ├── favicon.svg     # Logo chữ QQ nền vàng gold
│       └── og-image.png    # Ảnh chia sẻ 1200×630 (tạo bởi scripts/build-og-image.sh)
├── content.md              # ⭐ Toàn bộ nội dung dạng văn bản để sửa copy
├── robots.txt
└── sitemap.xml
```

## 2. Xem thử tại máy

Không cần cài gì:

```bash
cd site
python3 -m http.server 8080
# mở http://localhost:8080
```

Hoặc bằng Node:

```bash
npx serve site
```

## 3. Những chỗ cần sửa trước khi lên sóng

| Muốn đổi | Sửa ở đâu |
| --- | --- |
| **Tên miền** (`https://quangquy.ai/` đang là placeholder) | `index.html`: `canonical`, `og:url`, `og:image`, `twitter:image`; `robots.txt`; `sitemap.xml` |
| **Số điện thoại / Zalo** | `index.html` (nhiều chỗ, tìm `0763123992`) + `assets/js/app.js` → `CONFIG.phone`, `CONFIG.zalo` |
| **Email** (`hello@quangquy.ai`) | `index.html` → footer |
| **Giá 3 gói** | `index.html` → section `#bang-gia`; giá hiện tại là *mức tham khảo* |
| **Nhận lead tự động** | `assets/js/app.js` → `CONFIG.formEndpoint` (Google Apps Script / n8n / Formspree). Để trống = lưu trong trình duyệt + gửi qua Zalo |
| **Nội dung câu trả lời của chatbot demo** | `assets/js/chat-demo.js` → `PRODUCTS`, `COLORS`, hàm `reply()`, mảng `SCRIPT` |
| **Ảnh chia sẻ (OG)** | sửa biến trong `scripts/build-og-image.sh` rồi chạy lại |

> Ghi chú: Google Fonts (`Be Vietnam Pro`, `JetBrains Mono`) tải qua CDN. Nếu chạy offline,
> trang vẫn dùng được với font hệ thống nhờ fallback trong `styles.css`.

## 3b. Kiểm thử tự động

```bash
npm i --no-save jsdom          # cài 1 lần
node scripts/site-smoke-test.mjs
```

Script mô phỏng trình duyệt (jsdom) và kiểm tra: menu, carousel, validate form, gõ tin nhắn vào
chatbot trong lúc demo đang chạy, bấm gợi ý liên tiếp, countdown, và kịch bản chatbot tự chạy hết.
Chạy tự động trên CI qua `.github/workflows/site-check.yml` (không deploy).

## 4. Deploy lên GitHub Pages

Workflow có sẵn: `.github/workflows/deploy-quangquy-site.yml` — **chạy thủ công**, không tự deploy.

1. Repo → **Settings → Pages → Source: GitHub Actions**.
2. Tab **Actions** → *Deploy landing page quangquy* → **Run workflow**.
3. Sau khi job xong, URL nằm ở bước `deploy`.
4. Muốn dùng tên miền riêng: **Settings → Pages → Custom domain** (thêm bản ghi CNAME
   ở nhà cung cấp tên miền), sau đó cập nhật lại canonical/sitemap như bảng trên.

## 5. Tính năng tương tác

- Hoa đào rơi (canvas, tự tắt khi bật *giảm chuyển động* trong hệ điều hành).
- Countdown FOMO tự tính tới 23:59 ngày cuối tháng.
- Bộ đếm “đang đọc / lượt đọc” (lưu bằng `localStorage`).
- Carousel 6 sản phẩm (vuốt được trên điện thoại, phím ← → trên bàn phím).
- **Chatbot demo tương tác**: bấm câu hỏi gợi ý hoặc tự gõ — bot khớp từ khoá,
  trả lời theo dữ liệu sản phẩm mẫu, có tình huống *handoff* sang người thật.
- Terminal gõ chữ khi cuộn tới, thanh render Kling chạy tới 92%.
- Form tư vấn có kiểm tra dữ liệu, lưu cục bộ, soạn sẵn nội dung để gửi qua Zalo.
- Tối ưu tiếng Việt: font Be Vietnam Pro, `lang="vi"`, JSON-LD `Person` + `Service` + `FAQPage`.

Không có dữ liệu nào rời khỏi trình duyệt của người xem (trừ khi bạn cấu hình `formEndpoint`).
