# Hướng Dẫn Sử Dụng ZEUS AI Photo Studio (IOPaint, Fooocus, ComfyUI)

Tài liệu hướng dẫn tối ưu trải nghiệm chỉnh sửa ảnh AI chuyên nghiệp trên **Điện thoại** qua máy chủ GPU Tesla T4 Free của Google Colab.

---

## 1. Bảng So Sánh 3 Công Cụ

| Tiêu chí | 🎨 IOPaint (Lama Cleaner) | 👑 Fooocus (Khuyên dùng số 1) | 🧩 ComfyUI |
| :--- | :--- | :--- | :--- |
| **Mục đích chính** | Xóa vật thể thừa, xóa icon búng tim, vá nền | Giữ 100% mặt thật, mở rộng người, đổi đồ, tạo dáng | Xây dựng pipeline node chuyên sâu |
| **Độ thân thiện trên đt** | ⭐⭐⭐⭐⭐ (Cực dễ, nút to, chạm cọ mượt) | ⭐⭐⭐⭐⭐ (Giao diện phẳng Gradio, rất trực quan) | ⭐⭐ (Khó thao tác vì nhiều dây và chữ nhỏ) |
| **Khả năng giữ mặt** | Không hỗ trợ đổi mặt phức tạp | **Xuất sắc (FaceSwap chuyên dụng)** | Xuất sắc (cần cài thêm InstantID / ReActor) |
| **Thời gian tạo** | Siêu nhanh (3 – 5 giây/ảnh) | ~30 – 45 giây/ảnh | ~30 – 60 giây/ảnh |

---

## 2. Cách Mở Trên Điện Thoại (1 Chạm)

1. Mở trình duyệt trên điện thoại (Chrome hoặc Safari).
2. Dán đường link sau để mở thẳng notebook từ GitHub vào Google Colab:
   ```text
   https://colab.research.google.com/github/ZeusopenAI/ZEUS/blob/arena/5d02c329-zeus/colab/zeus_photo_studio.ipynb
   ```
3. **Cực kỳ quan trọng:** Trên menu Colab, bấm nút **Runtime (Thời gian chạy)** ➔ **Change runtime type (Thay đổi loại thời gian chạy)** ➔ Chọn **T4 GPU** ➔ Bấm **Save (Lưu)**.

---

## 3. Quy Trình Chuẩn Xử Lý Bài Toán Của Bạn

Yêu cầu: *Giữ 100% khuôn mặt thật, xóa icon búng tim, mở rộng thấy toàn thân ngồi vắt chéo chân ở ghế công viên cây xanh, mặc áo sơ mi trắng, quần tây đen, mang giày da đen, độ nét 2K.*

### Bước 1: Xóa Icon Búng Tim bằng IOPaint (Mất 10 giây)
1. Trong Colab, bấm nút **Play (Chạy)** ở Cell `[1] KHỞI ĐỘNG IOPAINT`.
2. Chờ 1–2 phút, Colab sẽ in ra dòng link màu xanh: `https://xxxx.trycloudflare.com`. Chạm vào link đó để mở web.
3. Chạm vào ô giữa màn hình để tải ảnh gốc từ thư viện điện thoại lên.
4. Dùng đầu ngón tay tô màu cọ (brush) đè lên cái **icon búng tim** ở góc trên bên phải.
5. Bấm nút hình **mũi tên / Run**, trong 3 giây icon sẽ biến mất hoàn toàn, nền cây cỏ được đắp lại phẳng phiu tự nhiên.
6. Bấm nút **Tải xuống (Download)** để lưu bức ảnh sạch về điện thoại.

---

### Bước 2: Dựng Toàn Thân & Khóa Mặt Thật bằng Fooocus (Mất 45 giây)
1. Quay lại Colab, bấm nút **Play (Chạy)** ở Cell `[2] KHỞI ĐỘNG FOOOCUS`.
2. Chờ tải xong, Colab sẽ hiện link Gradio: `https://xxxx.gradio.live`. Chạm vào link để mở.
3. Dưới chân trang, đánh dấu tích vào ô **Input Image**:
   * **Mục Image Prompt:** Tải bức ảnh của bạn (đã xóa icon ở Bước 1) lên.
   * Chạm vào tùy chọn **Advanced** bên dưới ảnh ➔ Chọn chế độ **FaceSwap** (độ mạnh Weight để mặc định ~0.9 đến 1.0).
   * **Mục Inpaint or Outpaint:** Tải tiếp ảnh đó vào ➔ Chọn chế độ **Outpaint** ➔ Chọn hướng mở rộng là **Bottom** (phía dưới).
4. Ở ô nhập văn bản (Prompt), dán câu lệnh sau:
   ```text
   Full body photograph of a young man sitting cross-legged on a wooden park bench, surrounded by lush green trees, wearing crisp white formal dress shirt, tailored black trousers, elegant black leather dress shoes, black rounded sunglasses, natural daylight, 8k resolution, highly detailed, photorealistic
   ```
5. Bấm nút **Generate** (Màu xanh to rõ).
6. Fooocus sẽ dùng công cụ FaceSwap khóa chặt gương mặt thật của bạn từ ảnh gốc, đồng thời mở rộng khung hình xuống dưới, vẽ phần thân đang ngồi vắt chéo chân đúng chuẩn trang phục sơ mi trắng, quần tây đen và giày da đen!
7. Chạm giữ vào bức ảnh hoàn thiện và chọn **Lưu hình ảnh**.

---

### Bước 3: Nâng Nét 2K
Trong giao diện Fooocus, tại tab **Upscale or Vary**:
* Thả bức ảnh vừa tạo ở Bước 2 vào.
* Chọn chế độ **Upscale (2x)** hoặc **Upscale (Fast 2x)**.
* Bấm **Generate**, bạn sẽ nhận được file ảnh độ phân giải 2K cực kỳ sắc nét.
