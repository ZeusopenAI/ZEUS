# BRAIN MEMORY — FLOWKIT AI FILMMAKING PIPELINE

- **Cập nhật:** 2026-10-03
- **Chủ đề:** Tự động hóa sản xuất phim AI & video marketing
- **Mã nguồn chuẩn:** `flowkit/` trong `ZeusopenAI/ZEUS`

---

## 1. Bản chất công nghệ & khái niệm cốt lõi

FlowKit là ứng dụng độc lập gồm:

- **FastAPI + SQLite:** Quản lý dự án, request queue và trạng thái pipeline.
- **Chrome Extension MV3 + Google Flow:** Browser bridge dùng tab Google Flow đã đăng nhập; cấu hình dự án qua `FLOW_PROJECT_ID`.
- **Dashboard React/Vite:** Theo dõi dự án, trạng thái render và media.
- **FFmpeg:** Ghép clip và xử lý hậu kỳ.
- **Skills trong `flowkit/skills/`:** Các recipe cho agent và người vận hành.

FlowKit chạy riêng, không cần Hermes runtime. Setup, requirements, dữ liệu runtime và tests nằm trong `flowkit/`. Xem `docs/FLOWKIT_INTEGRATION.md` để cài đặt và chạy.

---

## 2. Tính nhất quán hình ảnh và giới hạn

- **Reference Image System:** Gán media ID và ảnh tham chiếu cho nhân vật, địa điểm, đạo cụ; mô tả entity chỉ nên chứa ngoại hình ổn định.
- **Scene Prompting:** Prompt cảnh tập trung vào hành động, bố cục và camera, gọi entity theo tên thay vì lặp mô tả ngoại hình.
- **Giới hạn:** Ảnh tham chiếu hỗ trợ tính nhất quán nhưng không đảm bảo kết quả giống hệt qua mọi cảnh.
- **Scene chaining:** Khả năng phụ thuộc model và Flow API hiện hành. Veo start+end-frame chaining chưa được hỗ trợ trên batch API hiện tại; dùng mode Omni được hỗ trợ hoặc chỉ bật fallback sau khi người vận hành đồng ý.

---

## 3. Ứng dụng

- **Thương mại / dịch vụ:** Video quảng cáo cho dịch vụ, du lịch, bất động sản.
- **Nội dung sáng tạo:** Chuyển thể câu chuyện, thông điệp thương hiệu và nội dung ngắn.
- **Định dạng:** Tối ưu cho 9:16 (Shorts/Reels/TikTok) và 16:9 (YouTube/TVC), tùy workflow.

---

## 4. Kỹ năng điều khiển

- Hướng dẫn ZEUS: `skills/flowkit-ai-filmmaker/SKILL.md`.
- Recipe và commands chuẩn: `flowkit/skills/`.
- Bắt đầu chạy: `docs/FLOWKIT_INTEGRATION.md`.
