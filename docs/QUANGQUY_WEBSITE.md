# Website thương hiệu cá nhân — Nguyễn Quang Quý

Trạng thái: **đã code xong bản đầy đủ, đang chờ Quý chốt nội dung cuối trước khi lên sóng.**
Cập nhật: 2026-10-12

---

## 1. Bối cảnh

Quý gửi nội dung trang giới thiệu dịch vụ đang nằm trên **Google Sites** (link dạng
`sites.google.com/d/.../edit`) và yêu cầu: **mở rộng nội dung và code lại web**.

Google Sites có các hạn chế đã gặp:

- Không kiểm soát được code/SEO chi tiết (canonical, JSON-LD, OG image, tốc độ tải).
- Không nhúng được demo tương tác (chatbot, terminal, carousel tuỳ biến).
- Link chia sẻ dạng `sites.google.com/d/<id>/...` — không phải link sạch, khó dùng cho quảng cáo.

Ngoài ra Google Sites **không tự cập nhật bản public** khi bạn mới bấm *Edit*: phải bấm **Publish**
thì thay đổi mới hiện trên link xem (bỏ `/edit`). Nếu gần đây bạn sửa mà “không thấy đổi”, phần lớn
trường hợp là do chưa Publish.

## 2. Đã làm gì

Chuyển toàn bộ nội dung sang **site tĩnh trong repo** (`site/`), đồng thời **mở rộng** thêm:

| Mục | Nội dung mới |
| --- | --- |
| Section Vấn đề | 4 pain point cụ thể + câu chốt theo ngưỡng “2 trong 4” |
| Section Dịch vụ | 6 dịch vụ, mỗi dịch vụ có phạm vi + **“Đo được”** (KPI) |
| Kênh & sai lầm | Giữ 3 sai lầm gốc, thêm terminal A/B test hiển thị sống |
| Sản phẩm | 6 sản phẩm, mỗi cái có mock-up minh hoạ (browser/phone/flow/dashboard) |
| Quy trình | Timeline 14 ngày 5 mốc + khối “Bàn giao gồm những gì” |
| Trước & sau | Bảng so sánh 6 hạng mục vận hành + 4 nguyên tắc làm việc |
| Bảng giá | 3 gói + gói Care (giá hiện là mức tham khảo, cần Quý chốt) |
| FAQ | 8 câu hỏi thường gặp thực tế của SME |
| Liên hệ | Form 4 trường + kiểm tra dữ liệu + soạn sẵn nội dung gửi Zalo |
| Kỹ thuật | SEO đầy đủ, JSON-LD, hoa đào rơi canvas, countdown, live counter, carousel, demo chatbot tương tác |

## 3. Cấu trúc file

```text
site/
  index.html                     # 1 trang, ~15 section (id: #van-de #dich-vu #kenh #san-pham
                                 #   #cong-cu #chatbot #quy-trinh #ket-qua #bang-gia #faq #lien-he)
  assets/css/styles.css          # design system, responsive 1080/960/720/420, print, reduced-motion
  assets/js/app.js               # nav, carousel, countdown, hoa đào, terminal, form, counters
  assets/js/chat-demo.js         # demo chatbot (dữ liệu mẫu nội thất Minh Phát)
  assets/img/favicon.svg         # logo QQ vàng gold
  assets/img/og-image.png        # ảnh chia sẻ 1200×630 (ImageMagick, font DejaVu)
  content.md                     # ⭐ nội dung gốc để sửa copy
  robots.txt · sitemap.xml
  README.md                      # hướng dẫn xem thử + deploy + bảng “sửa ở đâu”
scripts/build-og-image.sh        # tạo lại og-image.png khi đổi chữ
.github/workflows/deploy-quangquy-site.yml   # deploy GitHub Pages (chạy THỦ CÔNG)
```

## 3b. Kiểm thử tự động

```bash
npm i --no-save jsdom
node scripts/site-smoke-test.mjs        # exit 0 = pass
```

Script dùng **jsdom** mô phỏng trình duyệt và kiểm tra: mở/đóng menu, nút chọn gói điền sẵn form,
carousel (nút · dot · phím ← →), form chặn dữ liệu sai và nhận dữ liệu đúng, gõ tin nhắn vào chatbot
**trong lúc kịch bản demo đang chạy**, bấm gợi ý liên tiếp, đóng thanh thông báo, cuộn trang,
countdown chạy đúng, và kịch bản chatbot tự chạy hết 5 tin bot / 4 tin khách / 8 product card
không để lại con trỏ “đang soạn”.

Hai lỗi thật do test phát hiện và đã sửa trong `chat-demo.js`:

1. **Người dùng gõ tin nhắn giữa lúc kịch bản demo đang chạy → tin bị bỏ qua im lặng.**
   Đã sửa: người dùng luôn “giành quyền” điều khiển, kịch bản dừng ngay.
2. **Bấm gợi ý trong lúc bot đang trả lời → không có phản hồi nào.**
   Đã sửa: tin nhắn xếp hàng đợi và được trả lời lần lượt (tối đa 3 tin chờ).

Workflow `.github/workflows/site-check.yml` chạy đúng các bước trên trên mọi PR/push có đổi
`site/**` (kèm kiểm tra cú pháp JS, id trùng, hash link hỏng, file thiếu). Workflow này **không deploy**.

## 4. Cách chạy & deploy

```bash
# Xem thử tại máy
cd site && python3 -m http.server 8080     # → http://localhost:8080

# Tạo lại ảnh OG khi đổi nội dung
bash scripts/build-og-image.sh
```

Deploy: repo → **Settings → Pages → Source: GitHub Actions**, sau đó vào tab **Actions** →
*Deploy landing page quangquy* → **Run workflow**. Workflow chỉ chạy khi bấm tay
(không tự deploy khi push) đúng theo quy tắc trong `AGENTS.md`: *deploy production phải hỏi trước*.

## 5. Bảo mật & quyền riêng tư

- Không có API key/token nào trong site; không gọi API bên thứ ba.
- Chatbot demo chạy **hoàn toàn phía trình duyệt** — không gửi dữ liệu người xem đi đâu.
- Form lưu yêu cầu bằng `localStorage` của chính người xem; muốn nhận lead tự động thì điền
  `CONFIG.formEndpoint` trong `site/assets/js/app.js` (Google Apps Script / n8n / Formspree).
- Font Google tải qua CDN; nếu chạy offline vẫn có fallback font hệ thống.

## 6. Việc cần Quý chốt

Xem mục 16 trong `site/content.md`. Tóm tắt:

1. Tên miền thật (site đang dùng placeholder `https://quangquy.ai/`).
2. Email liên hệ thật (đang là `hello@quangquy.ai`).
3. Giá 3 gói + gói Care.
4. Có muốn nhận lead tự động qua webhook không.
5. Có bổ sung số liệu thật của khách hàng (đã xin phép) để thay các con số minh hoạ không.
6. Giữ Google Sites song song hay thay thế hoàn toàn.

## 7. Lịch sử

- **2026-10-12** — Tạo `site/` từ đầu: HTML + CSS + JS, mở rộng nội dung theo 8 nhóm ở mục 2,
  thêm `content.md`, ảnh OG, favicon, workflow deploy thủ công. Kiểm tra: `node --check` 2 file JS,
  cân bằng thẻ HTML, không có id trùng, không có hash link hỏng.
