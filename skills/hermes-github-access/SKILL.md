---
name: hermes-github-access
description: Dùng GitHub token đã cấu hình để đọc/ghi repo ZEUS (commit, push, mở PR, sửa workflow, đọc issue), đồng thời xử lý media (ảnh/video) bằng ffmpeg + Pillow trên máy. Activate when the user asks Hermes to edit or push code, open a PR, change CI files, read repo content, or process images/videos.
license: MIT-compatible synthesized workflow; internal operations guide.
---

# Hermes GitHub Access

## Mục tiêu

Cho Hermes quyền làm việc thật với repo `ZeusOpenAI/ZEUS`: đọc mã, commit, push nhánh,
mở PR, sửa file CI — và xử lý ảnh/video trên máy. Mọi thứ chạy bằng token đã lưu
trong `$HERMES_HOME/.env`, không cần người dùng dán lại.

## Khi nào dùng

- Người dùng yêu cầu "sửa code trong repo", "push lên nhánh", "mở PR", "đổi workflow".
- Cần đọc trạng thái repo (commit gần nhất, file thay đổi, issue mở) để trả lời chính xác.
- Cần xử lý ảnh/video hàng loạt (resize, cắt, nén, đóng watermark của chính người dùng).

## Điều kiện tiên quyết

1. `$HERMES_HOME/.env` có `GITHUB_TOKEN` và `GH_TOKEN` (mode 600).
2. Repo đã clone trên máy (mặc định `/opt/zeus`).
3. Kiểm tra trước khi làm:

```bash
bash scripts/hermes-github-check.sh          # đọc-only, in ra quyền thật
```

Nếu báo "chỉ ĐỌC": **dừng lại**, báo người dùng cấp lại token có `Contents: Read and write`
(xem `docs/HERMES_GITHUB_TOKEN.md`). Không cố push rồi đoán mò.

## Quy trình chuẩn khi sửa code

```bash
cd /opt/zeus
git fetch origin --prune
git switch -c hermes/<mô-tả-ngắn> origin/main     # KHÔNG làm việc trên main
# ... sửa file ...
git add -A
git commit -m "mô tả ngắn, nêu rõ đã kiểm gì"
git push -u origin HEAD
gh pr create --base main --head "$(git branch --show-current)" \
  --title "..." --body "Đã kiểm: ..."
```

## Ranh giới an toàn (bắt buộc)

- **Không bao giờ** `git push --force` lên `main`, không xoá nhánh của người khác.
- **Không commit** `.env`, token, key, `state.db`, file > 5 MB không cần thiết.
- **Không tự merge** PR của chính mình; để người dùng bấm Merge.
- Việc tốn tiền (gọi model trả phí hàng loạt) hoặc phá huỷ (xoá dữ liệu, reset cứng)
  phải **hỏi trước** — theo `AGENTS.md` mục "Tác vụ phải hỏi trước".
- Không dán token vào chat/log/PR. Nếu token lộ: báo người dùng thu hồi ngay.

## Đọc repo nhanh mà không cần clone lại

```bash
gh api repos/ZeusOpenAI/ZEUS/commits?per_page=5 -q '.[] | .sha[0:7] + " " + .commit.message' | head
gh pr list --state open
gh issue list --state open
```

## Xử lý ảnh/video (KHÔNG liên quan tới token)

Token GitHub chỉ mở khoá GitHub. Để chỉnh sửa media trên máy cần công cụ riêng:

```bash
# một lần trên VPS/Codespace
sudo apt-get update && sudo apt-get install -y ffmpeg
python3 -m pip install --user pillow

# ví dụ
ffmpeg -i in.mp4 -vf scale=1080:-2 -c:a copy out.mp4
ffmpeg -i in.mp4 -ss 00:00:03 -frames:v 1 thumb.jpg
```

- Xoá watermark/logo của **nền tảng khác** (TikTok, Facebook) trên nội dung không thuộc
  sở hữu của người dùng: **từ chối**. Chỉ xử lý nội dung do người dùng sở hữu.
- Muốn chỉnh ảnh bằng AI (không phải lệnh ffmpeg): cần model ảnh + key
  (`OPENROUTER_API_KEY`), tốn credit — hỏi trước khi chạy hàng loạt.

## Định nghĩa "xong"

- Có commit + nhánh + PR (nếu người dùng muốn thay đổi được review).
- Đã chạy kiểm tra liên quan (`scripts/validate-skills.py`, `npm run build`, `pytest`…)
  và báo cáo kết quả thật, không suy đoán.
- Báo lại: nhánh nào, commit nào, link PR, đã kiểm gì, còn rủi ro gì.
