# Quang Quý AI — Hermes Profile

Profile này dùng Hermes như người điều phối cho repository `quangquy-ai`; không biến điện thoại thành máy chủ 24/7 và không tự có quyền với Facebook, Notion, Drive hay payout.

## Những gì profile làm được ngay

- Kiểm tra repository, tạo branch/commit, chạy test và ghi changelog.
- Chạy `tools/facebook_monetization_os.py validate` và tạo brief một Reel gốc/ngày.
- Báo chính xác các integration còn thiếu thay vì giả vờ đã đăng bài hoặc lấy được KPI.

## Những gì profile không được làm

- Đăng bài, gửi tin nhắn, đổi payout, gửi/lặp kháng nghị Meta, hoặc thay đổi quyền/tài khoản.
- Đọc/ghi mật khẩu, token, cookie, OTP, API key, giấy tờ thuế.
- Deploy production, merge vào `main`, hoặc tạo chi phí mà không có lệnh riêng từ chủ sở hữu.

## Cách dùng sau khi Hermes hoạt động

1. Clone repo này trong workspace Hermes/VPS lab.
2. Trỏ Hermes đến thư mục `hermes-profile/` như profile distribution của dự án.
3. Chạy skill `facebook-growth-ops` để tạo brief và xác thực trạng thái.
4. Chỉ thêm connector chính thức (Notion, Drive, Meta) qua OAuth do chủ tài khoản tự đăng nhập; tuyệt đối không đặt secrets vào GitHub.

Ví dụ quy trình nội bộ trong checkout của repo:

```bash
python tools/facebook_monetization_os.py validate
python tools/facebook_monetization_os.py daily-brief --date 2026-07-26 --output runs/daily-brief-2026-07-26.md
```

Profile này được thiết kế để chạy trên VPS lab cho các tác vụ dài. Điện thoại chỉ nên dùng để chat/duyệt trạng thái; Android có thể dừng tác vụ nền.

