# Roadmap — Quang Quý AI

Cập nhật: 2026-08-06

## Định hướng

Hermes là AI Manager trung tâm: nhận yêu cầu, chọn model/công cụ, điều phối workflow, giữ trạng thái và trả kết quả qua Telegram/CLI. GitHub là nguồn mã chuẩn; Notion/Google Drive quản lý tri thức và tài liệu; Make xử lý automation SaaS; VPS là production runtime 24/7.

## Giai đoạn 0 — nền tảng Termux (hiện tại)

Mục tiêu: có runtime phát triển ổn định trên Android.

- Entrypoint, editable install và tmux supervisor: hoàn tất.
- Cold-start từ boot script: hoàn tất.
- Còn thiếu: cài Termux:Boot và reboot thật.
- Gate thoát giai đoạn: sau reboot có boot log mới, tmux session tồn tại, process Hermes đúng venv và Telegram round-trip thành công.

## Giai đoạn 1 — bảo mật và CI

Mục tiêu: repository có thể phát triển an toàn.

- Sửa npm advisories theo từng dependency, không dùng `npm audit fix --force` trên `main`.
- Chạy Python/Node tests trong GitHub Actions Linux.
- Pin GitHub Actions bằng commit SHA.
- Bật branch protection, review và required status checks.
- Chuẩn hóa secret inventory, owner, scope, expiry và rotation.
- Đồng bộ technical fork `hermes-agent` với upstream chính thức trước khi nhận thêm thay đổi sản phẩm.

Gate: CI xanh, không có critical/high vulnerability chưa có quyết định xử lý, không có secret trong Git history hiện hành.

## Giai đoạn 2 — kênh và nhà cung cấp AI

Mục tiêu: Hermes điều phối được đa model và đa kênh.

Thứ tự triển khai:

1. Telegram Gateway.
2. OpenAI Codex hiện tại + Claude fallback.
3. Gemini fallback/vision.
4. GitHub workflow qua `gh`.
5. Notion và Google Drive.
6. Make webhook.
7. Hugging Face model/dataset operations.

Mỗi integration phải có least privilege, timeout, retry có giới hạn, idempotency và audit log.

## Giai đoạn 3 — VPS production

Mục tiêu: không phụ thuộc Android để chạy liên tục.

- VPS Ubuntu tối thiểu, firewall mặc định deny.
- Hermes Gateway chạy dưới service manager và user không phải root.
- Reverse proxy/TLS chỉ khi cần HTTP ingress.
- Backup encrypted ngoài máy, kiểm thử restore.
- Monitoring uptime, disk, memory, API errors và budget.

Gate: staging soak test, rollback đã diễn tập, Telegram và workflow quan trọng có health check.

## Giai đoạn 4 — AI Manager nâng cao

- Routing theo chi phí/độ khó/độ nhạy dữ liệu.
- Human approval cho deploy, gửi dữ liệu, phát sinh chi phí và thao tác phá hủy.
- Kanban nhiều agent cho workflow dài.
- Báo cáo định kỳ về tiến độ, chi phí và sự cố.
- Knowledge retrieval có phân quyền giữa cá nhân, dự án và khách hàng.

## Chiến lược repository

Giữ hai repository với vai trò tách biệt:

- `qquy28888-ops/quangquy-ai`: product/control plane canonical — cấu hình, automation, deployment và business logic.
- `qquy28888-ops/hermes-agent`: technical fork — chỉ chứa patch Hermes thực sự cần cho Quang Quý.
- `NousResearch/hermes-agent`: canonical upstream.

Thay snapshot `rsync` hiện tại bằng Git submodule pin SHA/tag dưới `vendor/hermes-agent/` (ưu tiên), pinned release/container nếu runtime ổn định, hoặc `git subtree` không `--squash` nếu bắt buộc một checkout. Không tiếp tục copy snapshot vì cách đó mất ancestry, contributor attribution và khiến CI upstream nằm lồng nên không chạy. Việc chuyển đổi phải diễn ra trên migration branch có backup tag, tree-equivalence check và rollback; không rewrite `main` trực tiếp.
