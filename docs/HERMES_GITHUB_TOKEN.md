# Gắn GitHub token cho Hermes (quyền đọc/ghi thật)

Mục tiêu: Hermes chạy 24/7 trên VPS **tự commit, push, mở PR, sửa workflow** — không
cần bạn dán token mỗi lần.

> ⚠️ **Không bao giờ dán token vào chat, issue, PR, commit, hay ảnh chụp màn hình.**
> Bạn tự nhập token vào máy/VPS của mình. Không ai (kể cả trợ lý AI) cần thấy giá trị token.

---

## 1. Hiểu đúng: ba thứ "token" khác nhau

Người dùng thường nhầm 3 thứ này. Chúng **không** thay thế nhau:

| Token | Dùng cho | Hermes trên VPS đọc được? |
|---|---|---|
| **Fine-grained PAT** / classic PAT | Bạn cấp cho Hermes để push code | ✅ nếu đặt trong `~/.hermes/.env` |
| **`secrets.GITHUB_TOKEN`** trong Actions | Chỉ tồn tại trong lúc workflow chạy | ❌ (không tồn tại ngoài workflow) |
| **Actions secrets** (vd `OPENROUTER_API_KEY`) | Truyền vào workflow | ❌ (Hermes trên VPS không đọc được) |

Nói cách khác: **đặt token vào Actions secret KHÔNG làm Hermes trên VPS có quyền.**
Muốn Hermes (gateway 24/7) push được code thì token phải nằm trong `$HERMES_HOME/.env`.

Ngoài ra còn một thứ rất hay bị nhầm là "token chỉ có quyền đọc":

- **`GITHUB_TOKEN` của Actions** bị giới hạn bởi *Settings → Actions → General →
  Workflow permissions*. Nếu để **Read repository contents** thì `git push` trong
  workflow sẽ 403 dù file workflow có ghi `contents: write`.
- Đây là lý do phổ biến nhất khiến `arena-auto-pr.yml` / `hermes-openrouter.yml`
  không mở được PR.

---

## 2. Tạo token đúng (khuyên dùng: fine-grained)

GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens
→ Generate new token**

- **Token name**: `hermes-vps-zeus`
- **Expiration**: 90 ngày (đừng chọn "No expiration")
- **Resource owner**: `ZeusOpenAI`
- **Repository access**: *Only select repositories* → `ZeusOpenAI/ZEUS`

### Quyền cần cấp

| Mục | Quyền | Vì sao |
|---|---|---|
| **Contents** | Read and write | commit, push, tạo/xoá nhánh |
| **Pull requests** | Read and write | mở/cập nhật PR |
| **Workflows** | Read and write | sửa file `.github/workflows/*` (nếu thiếu, push sẽ bị từ chối) |
| **Actions** | Read | xem trạng thái run, log |
| **Metadata** | Read | bắt buộc, GitHub tự thêm |
| **Administration** | Read | đọc thiết lập Actions (tuỳ chọn nhưng hữu ích) |
| **Issues** | Read and write | nếu muốn Hermes xử lý issue |

**Không cấp**: `Delete repositories`, `Administration: write`, `Secrets: write`,
`Organization: any`, `Webhooks: write`. Những quyền đó phá huỷ được repo hoặc lộ secret.

### Nếu bạn dùng classic token

Chỉ cần 2 scope: **`repo`** và **`workflow`**. Đừng tick `admin:org`, `delete_repo`,
`admin:public_key`, `admin:repo_hook` — không cần thiết cho Hermes.

---

## 3. Cài token vào máy chạy Hermes (VPS hoặc Codespace)

```bash
cd /opt/zeus          # hoặc thư mục repo trên máy bạn
sudo -u hermes bash scripts/hermes-github-setup.sh --repo ZeusOpenAI/ZEUS --test-write
```

Script sẽ hỏi token (ký tự bị ẩn, **không lưu vào shell history**), rồi:

1. Kiểm định dạng (`ghp_…`, `github_pat_…`)
2. Gọi `/user` để xác nhận token sống → in login
3. Đọc quyền thật trên repo (`admin / maintain / push / pull`)
4. Ghi `GITHUB_TOKEN` + `GH_TOKEN` vào `$HERMES_HOME/.env` (mode 600, có backup)
5. Cấu hình `gh` làm git credential helper (`gh auth setup-git`) để `git push` chạy
6. Với `--test-write`: tạo rồi xoá 1 nhánh test → **chứng minh** có quyền ghi

Kết quả:

```
== Quyền trên repo ZeusOpenAI/ZEUS ==
   · admin=True maintain=True push=True pull=True
   → CÓ quyền ghi (push/commit/PR)
== Thử quyền ghi ==
   ✓ TẠO được nhánh → token CÓ quyền ghi
   đã xoá nhánh test
```

Nếu token chỉ đọc, script **dừng với mã 3** và nói rõ cần cấp lại quyền nào — không
để bạn phát hiện muộn lúc push bị 403.

Cuối cùng, nạp lại để gateway dùng token mới:

```bash
hermes gateway restart
```

---

## 4. Kiểm tra bất cứ lúc nào (chỉ đọc)

```bash
bash scripts/hermes-github-check.sh
```

```
== Xác thực ==
  ✓ đăng nhập: qquy28888
  ✓ classic PAT · scopes: repo,workflow
== Repo ZeusOpenAI/ZEUS ==
  · admin=False maintain=False push=False pull=True
  ✗ chỉ ĐỌC trên repo (cần Contents: Read and write)
== GitHub Actions (quyền của GITHUB_TOKEN) ==
  ✗ default_workflow_permissions = read → workflow KHÔNG push được
```

Script không in giá trị token, không ghi gì. Mã thoát: `0` OK, `1` có vấn đề, `2` chưa có token.

---

## 5. Sửa quyền `GITHUB_TOKEN` cho workflow (nếu PR tự động không chạy)

GitHub → repo → **Settings → Actions → General → Workflow permissions** →
chọn **Read and write permissions** → **Save**.

Sau đó `arena-auto-pr.yml` và `hermes-openrouter.yml` mới push/PR được.

---

## 6. Điều token KHÔNG làm được

Token GitHub **chỉ** mở khoá GitHub. Nó không giúp Hermes:

| Việc bạn muốn | Cần gì thật |
|---|---|
| Sửa/chỉnh video, ảnh | `ffmpeg` + `Pillow` trên máy (`apt install ffmpeg`, `pip install pillow`) |
| Tạo ảnh bằng AI | Model ảnh + key (`OPENROUTER_API_KEY`), tốn credit |
| "Đọc bài viết" trên web | Quyền truy cập mạng của máy — không liên quan token |
| Chạy 24/7 | VPS/Docker, không phải Vercel serverless |
| Đăng bài lên TikTok/Facebook | API riêng của nền tảng (OAuth), không phải GitHub token |

---

## 7. Bảo mật & xoay vòng

- Token nằm trong `$HERMES_HOME/.env` mode **600**, thuộc user chạy Hermes.
- Không commit `.env` (`.gitignore` đã chặn). Nếu GitHub chặn push vì "secret detected",
  **đừng** dùng `--no-verify` — hãy xoá token khỏi lịch sử và thu hồi.
- Token lộ = **thu hồi ngay**: GitHub → Settings → Developer settings → Tokens → Delete.
- Xoay vòng mỗi 90 ngày: tạo token mới → chạy lại `hermes-github-setup.sh` → thu hồi token cũ.
- Máy nhiều người dùng: chỉ `root`/`hermes` đọc được `~/.hermes`; kiểm bằng
  `ls -ld ~/.hermes` (nên `700`).
- Cảnh báo: phương án dự phòng `~/.git-credentials` lưu token **dạng plaintext**. Chỉ dùng
  khi không cài được `gh`, và chỉ trên máy tin cậy.

---

## 8. File liên quan

| File | Vai trò |
|---|---|
| `scripts/hermes-github-setup.sh` | Nhận token (không qua argv), kiểm quyền, ghi `.env`, cấu hình `gh`/git |
| `scripts/hermes-github-check.sh` | Chẩn đoán chỉ-đọc: token, scopes, quyền repo, git, Actions |
| `skills/hermes-github-access/SKILL.md` | Quy trình + ranh giới an toàn cho Hermes khi sửa repo |
| `src/…` | — |
| `docs/HERMES_AUTO_SYNC.md` | Đồng bộ skill/ngữ cảnh sau khi có token |
