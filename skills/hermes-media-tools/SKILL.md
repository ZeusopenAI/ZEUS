---
name: hermes-media-tools
description: Xử lý ảnh và video hàng loạt bằng công cụ có sẵn trên máy (Pillow + ffmpeg) và đọc bài viết trên web thành văn bản sạch — hoàn toàn offline, không tốn credit. Activate when the user asks to resize, crop, compress, convert, watermark their own images, trim/compress video, export thumbnails, or read/summarize an article from a URL.
license: MIT-compatible synthesized workflow; internal operations guide.
---

# Hermes Media Tools

## Mục tiêu

Cho Hermes khả năng **làm việc thật với file media** và **đọc nội dung web**, không cần
API trả phí. Mọi thứ chạy cục bộ trên VPS/Codespace.

## Kiểm tra trước khi làm

```bash
bash scripts/hermes-power-setup.sh --check
```

Nếu thiếu công cụ:

```bash
bash scripts/hermes-power-setup.sh        # tự cài ffmpeg + Pillow
```

## Ảnh — `scripts/media-batch.py image`

```bash
# Nén + thu nhỏ cả thư mục
python3 scripts/media-batch.py image -i raw/ -o out/ --max-width 1920 --quality 82

# Cắt vuông cho feed + đóng tên thương hiệu của CHÍNH người dùng
python3 scripts/media-batch.py image -i raw/ -o out/ \
    --crop square --watermark-text "quangquy.ai" --position bottom-right

# Đóng logo PNG của người dùng
python3 scripts/media-batch.py image -i raw/ -o out/ \
    --watermark-image logo.png --opacity 180

# Đổi định dạng sang webp cho web
python3 scripts/media-batch.py image -i raw/ -o out/ --format webp --quality 80

# Xem trước, không ghi gì
python3 scripts/media-batch.py image -i raw/ -o out/ --max-width 800 --dry-run
```

Tùy chọn: `--crop square|16:9|9:16`, `--max-width`, `--max-height`, `--quality`,
`--format jpg|png|webp`, `--position`, `--opacity`.

## Video — `scripts/media-batch.py video`

```bash
# Chuẩn bị cho TikTok / Reels / Shorts (1080x1920, 30fps, h264)
python3 scripts/media-batch.py video -i clips/ -o out/ --preset vertical --thumbnail

# Bản nhẹ để gửi duyệt
python3 scripts/media-batch.py video -i clips/ -o out/ --preset preview

# Cắt 3 giây đầu, chất lượng cao hơn (crf thấp = đẹp hơn)
python3 scripts/media-batch.py video -i a.mp4 -o out/ --trim 0:3 --crf 20

# Trích 5 ảnh rải đều để làm ảnh bìa
python3 scripts/media-batch.py video -i a.mp4 -o out/ --frames 5
```

Preset: `vertical` (1080×1920) · `square` (1080×1080) · `landscape` (1920×1080) · `preview` (720×1280).

Preset dùng scale + pad nên **không làm méo hình** khi tỉ lệ nguồn khác khung đích.

## Xem thông tin file — `scripts/media-batch.py info`

```bash
python3 scripts/media-batch.py info anh.jpg video.mp4
```
Trả JSON: kích thước, độ phân giải, thời lượng, định dạng, dung lượng.

## Đọc bài viết — `scripts/read-article.py`

```bash
python3 scripts/read-article.py https://vidu.com/bai-viet
python3 scripts/read-article.py https://vidu.com/bai-viet --out bai.md --max-chars 8000
python3 scripts/read-article.py trang-da-tai.html --json
```

Bỏ menu/quảng cáo/footer/script, giữ tiêu đề + đoạn + danh sách + link dạng Markdown.

Nếu máy bị chặn domain (VPS một số nơi chặn), tải file trước rồi đọc bằng đường dẫn.

## Quy tắc bắt buộc

- **Không xoá watermark/logo của nền tảng khác** (TikTok, Facebook, Shutterstock…) trên
  nội dung không thuộc sở hữu của người dùng. Chỉ đóng watermark **của chính họ**.
- Không ghi đè file gốc: luôn xuất ra thư mục `--output` (script tự tránh trùng tên).
- Việc hàng loạt lớn (>100 file hoặc video dài) → chạy `--dry-run` trước, báo thời gian ước tính.
- Đọc web: chỉ nội dung công khai; trích dẫn nguồn khi dùng lại.
- Kết quả luôn báo: bao nhiêu file, tiết kiệm bao nhiêu dung lượng, file nào lỗi và vì sao.

## Định nghĩa "xong"

- File kết quả tồn tại, mở được, kích thước/độ phân giải đúng như yêu cầu.
- Đã in tổng kết (số file thành công/lỗi) — không tuyên bố thành công khi chưa kiểm.
- Với video: kiểm lại bằng `media-batch.py info` để chắc thời lượng/độ phân giải đúng.
