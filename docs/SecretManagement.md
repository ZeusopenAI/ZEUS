# Secret Management — Quang Quý AI

Cập nhật: 2026-08-06

## Mục tiêu

Không credential nào nằm trong Git, Notion page, prompt, log hoặc tài liệu. Mỗi dịch vụ có credential riêng, scope tối thiểu, owner, ngày tạo, ngày hết hạn/rotation và quy trình revoke.

## Phân loại và nơi lưu

| Loại | Development Termux | GitHub Actions | Production |
|---|---|---|---|
| Model API keys | `~/.hermes/.env`, mode 600 | GitHub Secrets nếu CI cần | Secret manager hoặc service env |
| OAuth tokens | `~/.hermes/auth.json`, mode 600 | Tránh dùng user OAuth trong CI | Secret manager/encrypted state |
| Telegram token | `~/.hermes/.env` | Chỉ nếu deploy workflow cần | Secret manager/service env |
| Notion token | `~/.hermes/.env` | GitHub Secret nếu CI cần | Secret manager |
| Google credentials | OAuth store ngoài repo | Workload identity/secret | Secret manager, scope tối thiểu |
| Make credentials | Make Connections/Secrets | Không copy vào GitHub nếu không cần | Make vault + webhook secret |
| Hugging Face token | `~/.hermes/.env` | GitHub Secret theo environment | Secret manager; ưu tiên read-only |

`.env.example` chỉ chứa tên biến và placeholder. `config.yaml` chỉ chứa hành vi, model name, timeout và feature flags; không chứa secret.

## Trạng thái audit

- `~/.hermes`: mode 700.
- `~/.hermes/config.yaml`: mode 600.
- `~/.hermes/auth.json`: mode 600.
- `~/.hermes/.env`: chưa tồn tại.
- `~/.config/gh/hosts.yml`: chưa tồn tại; GitHub CLI chưa đăng nhập.
- Tracked sensitive filenames: chỉ `agents/hermes/.env.example`.
- High-confidence credential scan production paths hiện tại: 0 finding.
- Không có gitleaks/trufflehog/detect-secrets local; CI hiện dùng pattern scan. Nên bổ sung scanner chuyên dụng trong CI bằng phiên bản/SHA pin.

## Quy trình tạo secret

1. Xác định service, owner và use case.
2. Tạo credential riêng cho Quang Quý AI, không tái sử dụng personal master token.
3. Chọn scope nhỏ nhất; read-only là mặc định.
4. Lưu vào đúng vault; đặt permission filesystem 600 nếu là local file.
5. Chỉ cấu hình biến môi trường theo tên, không ghi giá trị vào command history hoặc tài liệu.
6. Kiểm thử và ghi lại ngày tạo/rotation trong inventory không chứa giá trị.

## Rotation/revoke

- Rotate ngay nếu token từng xuất hiện trong Git, chat, log hoặc màn hình chia sẻ.
- Revoke credential cũ trước hoặc ngay sau khi credential mới được xác minh.
- Kiểm tra dependency: gateway, cron, CI, Make scenario và VPS service.
- Ghi audit event gồm tên secret, owner, thời điểm và kết quả; không ghi value.

## Incident response

1. Cô lập workflow/process nghi ngờ.
2. Revoke/rotate credential.
3. Kiểm tra provider audit log và phạm vi truy cập.
4. Xóa secret khỏi source hiện tại và rewrite history nếu cần, nhưng hiểu rằng rewrite không thay thế revoke.
5. Thông báo owner, thêm prevention test và rà soát credential cùng scope.

## Chính sách từng integration

- GitHub: fine-grained PAT hoặc GitHub App; repo scope cụ thể; branch protection; không dùng classic PAT rộng nếu tránh được.
- Notion: share từng page/database, không share toàn workspace.
- Google Drive: OAuth scope tối thiểu; ưu tiên app folder hoặc folder riêng.
- Telegram: token chỉ dùng cho một bot; giới hạn user/chat allowlist.
- Make: secret per webhook/scenario, kiểm tra chữ ký và chống replay.
- Hugging Face: read token mặc định; write token riêng cho publish job.
- Model providers: budget/rate limit và key riêng cho dev/prod.

## CI gate

CI phải chặn sensitive filenames, high-confidence key patterns và secret-shaped value trong examples. GitHub Actions phải pin commit SHA; không dùng mutable tags. Production deploy dùng environment approval và secrets theo environment.
