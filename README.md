# QuangQuy AI

Dự án website và hệ thống AI Automation cho thương hiệu cá nhân Nguyễn Quang Quý.

## Mục tiêu

- Xây dựng website giới thiệu dịch vụ AI Automation và Marketing.
- Quản lý mã nguồn bằng GitHub.
- Triển khai website miễn phí hoặc chi phí thấp.
- Duy trì quy trình thay đổi an toàn, có lịch sử và có thể khôi phục.

## Quy tắc làm việc

1. Không đưa mật khẩu, cookie, access token, API key hoặc file `.env` lên GitHub.
2. Không chỉnh sửa trực tiếp bản đang chạy nếu chưa có bản sao lưu.
3. Mỗi thay đổi lớn nên thực hiện trên nhánh riêng hoặc pull request.
4. Trước khi triển khai phải kiểm tra lỗi build và liên kết.
5. Ghi rõ các file đã thay đổi trong mỗi commit.

## Trạng thái

Hermes Agent đã được tích hợp tại `agents/hermes/` và đang đóng vai trò AI Manager/orchestration runtime. Môi trường Termux đã chạy được bằng virtualenv + tmux supervisor; production VPS và các integration bên ngoài vẫn đang được triển khai.

## Tài liệu vận hành

- [Status](Status.md)
- [TODO](TODO.md)
- [Roadmap](Roadmap.md)
- [Architecture](Architecture.md)
- [Deployment](Deployment.md)
- [Repository audit](docs/AUDIT_2026-08-06.md)
- [Secret management](docs/SecretManagement.md)
