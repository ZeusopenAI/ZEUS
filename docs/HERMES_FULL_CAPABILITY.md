# Cấp "toàn quyền" cho Hermes — một lệnh

Tài liệu này trả lời đúng câu hỏi: *"gửi code để dán vào Hermes để nó toàn quyền sửa
video/ảnh, đọc bài viết, và thay đổi trên Git"*.

---

## 0. Đọc 30 giây trước khi dán

Ba điều dễ hiểu nhầm, nói ngắn gọn:

1. **Token đặt trong Actions secrets KHÔNG cấp quyền cho Hermes trên VPS.**
   Secret chỉ tồn tại trong lúc workflow chạy. Hermes (gateway 24/7) đọc token từ
   `~/.hermes/.env`. Cần cả hai nếu bạn muốn cả hai.
2. **Token GitHub chỉ mở khoá GitHub.** Nó không giúp cắt video hay sửa ảnh —
   việc đó cần `ffmpeg` + `Pillow` cài trên máy.
3. **Không dán token vào chat.** Script sẽ hỏi token trên máy bạn, ký tự bị ẩn,
   không lưu vào shell history.

---

## 1. Dán đúng 1 lệnh này trên VPS

```bash
cd /opt/zeus && sudo -u hermes bash scripts/hermes-power-setup.sh --with-token
```

Nó làm 6 việc và in bảng tổng kết:

| Bước | Việc |
|---|---|
| 1 | Cài `ffmpeg` (apt, hoặc bản pip nếu không có quyền root) |
| 2 | Cài `Pillow` |
| 3 | Kiểm `git` + `gh`, thử `git ls-remote` |
| 4 | **Hỏi GitHub token** (ẩn ký tự), kiểm quyền thật, ghi `~/.hermes/.env` mode 600 |
| 5 | Kiểm parser đọc bài viết + kiểm mạng ra Internet |
| 6 | Đồng bộ skill + ngữ cảnh sang Hermes |

Kết quả mong đợi:

```
╔══════════════════════════════════════════════════╗
║  TỔNG KẾT NĂNG LỰC CỦA HERMES                    ║
╚══════════════════════════════════════════════════╝
  ✓ ffmpeg: ffmpeg version 7.0.2-static
  ✓ Pillow 13.0.0
  ✓ git 2.39.5
  ✓ gh đã đăng nhập
  ✓ git ls-remote origin OK
  ✓ GitHub token hợp lệ và đủ quyền
  ✓ parser HTML hoạt động
  ✓ ra được Internet (đọc bài trực tiếp từ URL)
  ✓ media-batch.py chạy được (ảnh)
  ✓ media-batch.py có ffmpeg để xử lý video

  10 đạt · 0 chưa đạt
```

Kiểm lại bất cứ lúc nào (chỉ đọc, không cài gì):

```bash
bash scripts/hermes-power-setup.sh --check
```

---

## 2. Lệnh Hermes sẽ dùng sau khi cài

### Ảnh

```bash
# Nén + thu nhỏ cả thư mục
python3 scripts/media-batch.py image -i raw/ -o out/ --max-width 1920 --quality 82

# Cắt vuông + đóng thương hiệu của chính bạn
python3 scripts/media-batch.py image -i raw/ -o out/ \
    --crop square --watermark-text "quangquy.ai" --position bottom-right
```

### Video

```bash
# Chuẩn TikTok/Reels: 1080x1920, 30fps + thumbnail
python3 scripts/media-batch.py video -i clips/ -o out/ --preset vertical --thumbnail

# Cắt 3 giây đầu
python3 scripts/media-batch.py video -i a.mp4 -o out/ --trim 0:3

# Trích 5 ảnh bìa
python3 scripts/media-batch.py video -i a.mp4 -o out/ --frames 5
```

### Đọc bài viết

```bash
python3 scripts/read-article.py https://vidu.com/bai-viet --out bai.md
```

### Git (commit → push → PR)

```bash
cd /opt/zeus
git fetch origin --prune
git switch -c hermes/sua-loi-x origin/main
# ... sửa file ...
git add -A && git commit -m "mô tả ngắn"
git push -u origin HEAD
gh pr create --base main --head "$(git branch --show-current)" --title "..." --body "..."
```

Chi tiết + ranh giới an toàn: `skills/hermes-github-access/SKILL.md`.

---

## 3. Nói gì với Hermes để nó dùng đúng

Hermes tự đọc kỹ năng qua `skills_list` / `skill_view`. Bạn chỉ cần nói việc:

- *"Nén toàn bộ ảnh trong `raw/`, thu về 1920px, đóng logo của tôi góc phải."*
- *"Clip này đưa về 1080x1920 cho TikTok, xuất kèm thumbnail."*
- *"Đọc bài này rồi tóm tắt 10 gạch đầu dòng: https://…"*
- *"Sửa lỗi X trong `scripts/…`, mở PR về main."*

Hermes sẽ chọn `media-batch.py`, `read-article.py` hoặc skill `hermes-github-access`.

---

## 4. GitHub token: quyền tối thiểu đủ dùng

Fine-grained PAT, chỉ repo `ZeusOpenAI/ZEUS`:

| Mục | Quyền |
|---|---|
| Contents | **Read and write** |
| Pull requests | **Read and write** |
| Workflows | **Read and write** |
| Actions | Read |
| Administration | Read |
| Issues | Read and write |

**Không cấp**: `Delete repositories`, `Administration: write`, `Secrets: write`,
`Organization`. Không cần cho việc bạn muốn, và làm tăng thiệt hại nếu token lộ.

Nếu dùng classic token: chỉ cần scope `repo` + `workflow`.

Chi tiết + xoay vòng + thu hồi: `docs/HERMES_GITHUB_TOKEN.md`.

---

## 5. Nếu PR tự động vẫn không chạy

Không phải lỗi token. Kiểm hai thứ:

1. **Settings → Billing** — GitHub Actions còn hạn mức không? Khi hết hạn mức,
   job fail ngay ở bước `Set up job` (2–3 giây) và **không chạy code của bạn**.
2. **Settings → Actions → General → Workflow permissions** → **Read and write**.

---

## 6. Giới hạn cần biết (nói thật)

| Việc | Hermes làm được? |
|---|---|
| Nén/cắt/resize ảnh, cắt/nén video, thumbnail, frame | ✅ offline, không tốn credit |
| Đóng watermark **của chính bạn** | ✅ |
| Xoá watermark TikTok/Facebook trên nội dung người khác | ❌ từ chối |
| Đọc bài viết công khai → văn bản/markdown | ✅ (nếu VPS ra được Internet) |
| Commit/push/PR/sửa workflow | ✅ khi có token đúng quyền |
| Tạo ảnh bằng AI | ⚠️ cần model ảnh + key, **tốn credit** |
| Chạy 24/7 | ✅ trên VPS — **không** trên Vercel serverless |

---

## 7. Bảo mật

- Token trong `~/.hermes/.env` mode **600**, thuộc user chạy Hermes (`ls -ld ~/.hermes` → `700`).
- Không commit `.env`; nếu GitHub chặn push vì "secret detected" → **đừng** dùng
  `--no-verify`, hãy xoá khỏi lịch sử và thu hồi token.
- Token lộ → thu hồi ngay: GitHub → Settings → Developer settings → Tokens → Delete.
- Không đưa token cho bất kỳ ai (kể cả trợ lý AI). Script tự hỏi trên máy bạn.

---

## 8. File liên quan

| File | Vai trò |
|---|---|
| `scripts/hermes-power-setup.sh` | Cài + kiểm tra toàn bộ năng lực (một lệnh) |
| `scripts/media-batch.py` | Xử lý ảnh/video hàng loạt (Pillow + ffmpeg) |
| `scripts/read-article.py` | Đọc bài viết web → văn bản sạch / Markdown |
| `scripts/hermes-github-setup.sh` | Gắn token, kiểm quyền, cấu hình `gh`/git |
| `scripts/hermes-github-check.sh` | Chẩn đoán quyền token (chỉ đọc) |
| `skills/hermes-media-tools/SKILL.md` | Hướng dẫn cho Hermes về media |
| `skills/hermes-github-access/SKILL.md` | Hướng dẫn cho Hermes về Git/PR |
| `docs/HERMES_GITHUB_TOKEN.md` | Bảng quyền token, xoay vòng, thu hồi |
