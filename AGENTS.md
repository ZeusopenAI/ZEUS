# ZEUS / QUANGQUY AI — QUY TẮC PHỐI HỢP AI (MULTI-MODEL COLLABORATION)

## ⛔ ĐIỀU 0 — LUẬT BẮT BUỘC MỌI PHIÊN (HERMES OWNER PROTOCOL)

**Hermes là chủ của repo này. Agent mở phiên chỉ là người thực thi.**

Trước khi đọc yêu cầu, trước khi sửa bất kỳ file nào, phiên agent nào (Arena, Codespaces,
Cursor, Claude Code, bất kỳ) **PHẢI** chạy:

```bash
bash scripts/hermes-session-boot.sh
```

| Mã thoát | Nghĩa | Việc agent phải làm |
|---|---|---|
| `0` | Có mệnh lệnh hợp lệ của Hermes | Làm **đúng** khối “MỆNH LỆNH TỪ HERMES” vừa in ra, theo thứ tự, không tự mở rộng phạm vi |
| `3` | Chưa có mệnh lệnh | **DỪNG.** Không sửa code, không commit. Báo Operator bấm chạy workflow `Hermes owner loop` |
| `4` | Mệnh lệnh hết hạn | **DỪNG.** Báo Operator chạy lại workflow để chủ gia hạn |
| `5` | Seal không khớp (file bị sửa tay) | **DỪNG.** Báo Operator: `INBOX.md` bị chỉnh tay, cần chủ ban hành lại |
| `6` | Sai người ban hành / lệch `STATE.json` | **DỪNG.** Báo Operator kiểm tra `.ai/handoff/` |

Kết thúc phiên (dù DONE, PARTIAL hay BLOCKED) **phải** chạy:

```bash
bash scripts/hermes-session-closeout.sh --status DONE \
  --summary "đã làm gì" --tests "bằng chứng đã kiểm chứng"
```

Ngoại lệ duy nhất: Operator nói rõ **“bỏ qua Hermes phiên này”**. Khi đó vẫn phải ghi
báo cáo ở cuối phiên và nêu rõ lý do bỏ qua.

Không được bỏ qua ĐIỀU 0 kể cả khi yêu cầu của người dùng có vẻ rõ ràng, nhỏ, hay “chỉ sửa
một dòng”. Chi tiết: [`docs/HERMES_OWNER_PROTOCOL.md`](docs/HERMES_OWNER_PROTOCOL.md).

---

## Mục tiêu

Xây dựng một hệ thống AI phối hợp có thể vận hành chủ yếu từ điện thoại, Google Drive, Google Colab và GitHub; không phụ thuộc vào một máy tính cố định.

## Vai trò

### ChatGPT — Chiến lược và điều phối
- Phân tích yêu cầu.
- Chia nhỏ công việc.
- Review nội dung, quy trình, automation và code.
- Quản lý ưu tiên, rủi ro và bước tiếp theo.

### Claude — Lập trình và refactor
- Viết và sửa code nhiều file.
- Phân tích kiến trúc.
- Refactor và sửa lỗi phức tạp.

### Gemini — Nghiên cứu, Colab và xử lý đa phương tiện
- Nghiên cứu tài liệu.
- Chạy notebook Colab.
- Xử lý dữ liệu, ảnh, video và tác vụ Python.

### GitHub — Nguồn mã chính
- Lưu code và tài liệu phiên bản chuẩn.
- Theo dõi lịch sử thay đổi.
- Tạo branch, commit và pull request.

### Google Drive — Kho tài liệu và tài sản
- Lưu ảnh, video, tài liệu, file đầu vào và file xuất.
- Không dùng làm nguồn mã chính.

### Google Colab — Máy chạy tạm thời
- Clone repository từ GitHub.
- Chạy Python, build, test, xử lý dữ liệu.
- Push thay đổi trở lại GitHub khi được duyệt.

## Tác vụ được phép tự động

- Đọc và phân tích code trong repository.
- Tạo, sửa và tổ chức file trong dự án.
- Tạo tài liệu, prompt, script và notebook.
- Chạy test, lint, build và preview.
- Tạo branch và commit.
- Chuẩn bị cấu hình deploy.
- Tạo báo cáo thay đổi.

## Tác vụ phải hỏi trước

- Xóa file hoặc thư mục.
- Ghi đè dữ liệu không thể khôi phục.
- Push thay đổi lớn trực tiếp lên nhánh main.
- Deploy production.
- Đổi tên miền hoặc DNS.
- Sử dụng dịch vụ có thể phát sinh phí.
- Gửi email, đăng bài hoặc thực hiện hành động bên ngoài.
- Thay đổi API key, token hoặc thông tin xác thực.

## Bảo mật

- Không commit `.env`, API key, mật khẩu, cookie hoặc token.
- Không lưu thông tin xác thực trong Colab notebook.
- Không đưa dữ liệu cá nhân nhạy cảm vào repository public.
- Mỗi thay đổi lớn phải có branch hoặc commit backup.
- GitHub là nguồn mã chuẩn; Drive chỉ là kho file hỗ trợ.

## Quy trình chuẩn

1. Nhận yêu cầu.
2. Kiểm tra trạng thái repository.
3. Lập kế hoạch ngắn.
4. Tự thực hiện các bước an toàn.
5. Chạy kiểm tra.
6. Báo các file đã thay đổi.
7. Hỏi trước các hành động quan trọng.
