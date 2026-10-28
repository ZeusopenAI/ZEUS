# Tham khảo: quy trình nâng chất lượng video AI (ghi chép từ chia sẻ của Operator)

> Nguồn: đoạn chia sẻ ngày 2026-10-28 về một workflow "swap character/background/trang phục"
> dùng model nguồn mở (bài viết gọi là **Minimax H3**). Đây là **ghi chú kỹ thuật nội bộ để học
> cách tổ chức pipeline**, không phải xác nhận năng lực model, không phải benchmark, và không
> mang nội dung/bất kỳ asset nào từ bài viết vào repo. Các tên model/kênh tham khảo trong bài
> chưa được đối chiếu với nguồn chính thức — cần verify trước khi đưa vào dependency.

---

## 1. Vấn đề được nêu

Model sinh video nguồn mở dạng "thô" thường có 4 bệnh khi nhân vật ở xa hoặc video gốc nhiều
đoạn cắt: nhiễu / bể pixel, nát mặt (< 120 px), da nhựa bóng dầu, và ám đỏ. Bài viết giải quyết
bằng cách **không render thẳng độ phân giải cao**, mà dựng một pipeline nhiều stage, mỗi stage
một trách nhiệm riêng.

## 2. Bốn trụ cột (đọc như pattern, không đọc như công thức copy)

### 2.1 Guide Latent + nhánh LoRA nhận dạng riêng

- Thay vì ném ảnh + video vào Reference thông thường (dễ trôi nét, sai form người, lỗi chuyển
  động khi video gốc có nhiều cut), ép luồng video đi qua **Guide Latent** kèm LoRA swap dạng
  latent, và **tự động tách nền ảnh mẫu**.
- Rank động nén nhẹ, nhưng **khóa cứng** các đặc trưng: khuôn mặt, kiểu tóc, vóc dáng — đồng
  thời bám chuyển động nhỏ và đổi trang phục của video gốc.

**Pattern đáng học:** tách luồng "danh tính" khỏi luồng "chuyển động". Đừng để một model phải
vừa nhớ mặt vừa đoán motion. FlowKit đã có reference-image system; đây là bước tiếp theo của nó.

### 2.2 2-Pass Latent Upscale + phân nhánh LoRA (không nhồi chung)

- Pass 1 dựng khung nhanh ở độ phân giải thấp; Pass 2 đẩy qua **3D Latent Upscaler** lên ~1.0 MP.
  Ép model render cao ngay từ đầu vừa nặng vừa bệt.
- **Mấu chốt:** nếu nhồi chung LoRA Swap và LoRA làm nét vào một luồng, chúng "đánh nhau" →
  đơ chuyển động hoặc méo mặt. Phải tách riêng nhánh LoRA cho từng stage, cộng LoRA
  Detail/Realism với tỷ lệ riêng.

**Pattern đáng học:** mỗi stage có **config + weight riêng**, log lại tỉ lệ LoRA. Đây cũng là lý
do `post_process.py` của FlowKit nên được tách thành các bước có tên, thay vì một chuỗi ffmpeg
dài khó debug.

### 2.3 Face Refine động + Audio Lock

- Tự động dò mặt trên từng frame, cắt riêng, vẽ lại ở độ phân giải cao với **lực denoise biến
  thiên theo khoảng cách**: mặt xa (< 120 px) vẽ lại mạnh, mặt gần chỉ gọt nhẹ.
- **Khóa cứng audio**: khi ghép mặt trở lại, khẩu hình vẫn khớp nhịp thở/âm thanh gốc — tức là
  refine chỉ được phép sửa pixel, không được sửa timeline âm thanh.

**Pattern đáng học:** refine theo **tín hiệu đo được** (kích thước mặt, confidence), không refine
toàn frame mù quáng. Và luôn giữ một "trục bất biến" (ở đây là audio) để các stage sau không làm
lệch đồng bộ — giống như `f(t)` trong
[`REFERENCE_PDOOM_VIDEO.md`](REFERENCE_PDOOM_VIDEO.md) giữ nguyên trục thời gian.

### 2.4 Cân bằng màu + super-resolution phần cứng

- Trước khi xuất, đưa toàn bộ khung qua bộ lọc cân bằng màu để triệt tông da đỏ đặc trưng,
  rồi dùng **NVIDIA RTX VSR** đẩy lên 1080P mà không render lại.

**Pattern đáng học:** màu sửa **trước** upscale (upscale sẽ nhân luôn lỗi màu). Với ZEUS
cloud-first (Colab/VPS, không chắc có GPU NVIDIA), cần fallback không phụ thuộc phần cứng:
white-balance bằng Pillow/`zscale` + upscale `lanczos`, hoặc Real-ESRGAN chạy riêng ngoài
runtime Hermes.

## 3. Cái đem được vào ZEUS ngay (không cần model mới)

1. **Stage contract:** mỗi bước xử lý ghi ra `{stage, config, seed, input, output, duration}`.
   Khi clip hỏng, biết đúng stage nào — thay vì mò trong một lệnh ffmpeg 20 tham số.
2. **QA bằng contact sheet:** `prototypes/deterministic-render/sheet.mjs` và lệnh `sheet` đề xuất
   cho `scripts/media-batch.py` dùng được ngay cho việc so sánh trước/sau từng stage.
3. **Quality gate:** trước khi xuất file cuối, kiểm tra 3 thước đo đơn giản — mặt có bị nát
   (kích thước face box), màu có ám đỏ (trung bình kênh R so với G/B), và độ sắc nét
   (variance của Laplacian). Chỉ cần log, chưa cần chặn.
4. **Không trộn LoRA / không trộn preset:** áp cả cho prompt lẫn preset ffmpeg — một stage, một
   ý định.
5. **Trục bất biến:** audio/timeline/seed không đổi qua các stage; mọi refine chỉ đụng pixel.

## 4. Giới hạn & phạm vi (quan trọng)

- **Chỉ áp dụng cho nội dung hợp pháp và có sự đồng ý** của người xuất hiện trong ảnh/video.
  ZEUS không xây tính năng chuyên tạo nội dung 18+, không hỗ trợ deepfake người thật không có
  sự đồng ý, và không tìm cách vượt rào kiểm duyệt của nhà cung cấp dịch vụ. Việc một model là
  nguồn mở không làm thay đổi luật pháp hay chính sách nền tảng phân phối nội dung.
- **Các con số là claim, chưa kiểm chứng:** "1080P trong veo", "gần Seedance 2.5", "rank động
  cực nhẹ" đều là mô tả trong bài chia sẻ. Nếu đưa vào sản phẩm, phải đo (PSNR/SSIM/LPIPS +
  review mù) và ghi rõ điều kiện phần cứng.
- **Không kéo dependency nặng vào runtime Hermes:** model/LoRA/VSR nếu có sẽ nằm ở
  `flowkit/` hoặc một job Colab riêng, chạy khi Operator chủ động bật; không tự tải weight,
  không tự gọi dịch vụ có phí, không tự publish.
- **Không copy asset:** bài viết không kèm repo/weights; ZEUS chỉ giữ lại phần mô tả kiến trúc.

## 5. Đề xuất lộ trình nhỏ (nếu bạn muốn triển khai)

| Bước | File | Việc |
|---|---|---|
| A1 | `flowkit/docs/STYLE_BIBLE.md` | Gộp style bible + 4 quy tắc ở mục 3 thành "chuẩn chất lượng" cho prompt sinh video |
| A2 | `scripts/media-batch.py` | Thêm `sheet` (contact sheet) và `--white-balance` (Pillow), kèm test |
| A3 | `flowkit/agent/services/post_process.py` | Tách stage có tên + log config; **chưa** đụng model |

## 6. Liên quan

- `docs/REFERENCE_PDOOM_VIDEO.md` — deterministic render, hợp đồng dữ liệu, QA contact sheet
- `prototypes/deterministic-render/` — prototype `f(t)` chạy thật được
- `memory/flowkit-ai-filmmaking.md` · `skills/flowkit-ai-filmmaker/SKILL.md`
- `docs/FLOWKIT_INTEGRATION.md` · `scripts/media-batch.py`
