# RCA — Vì sao "gọi Hermes làm chủ phiên chat" bị lỗi (28/10/2026)

> Tài liệu phân tích sự cố (Root Cause Analysis). Kết luận ngắn: **lỗi không nằm ở Hermes,
> mà nằm ở bộ luật biến một kênh gợi ý bên ngoài thành điều kiện tiên quyết của mọi phiên chat.**
> Toàn bộ luật đã được sửa sang chế độ **TÙY CHỌN**. Luật gốc mới: [`../AGENTS.md`](../AGENTS.md) ĐIỀU 0.

---

## 1. Tóm tắt cho người đọc vội

| | |
|---|---|
| **Triệu chứng** | Mở phiên chat/agent, gọi Hermes làm chủ → nhận lỗi; AI dừng, không chịu làm việc theo yêu cầu. |
| **Tác động** | Mọi phiên Arena / Codespaces / Cursor đọc `AGENTS.md` đều bị chặn từ 23/10/2026. |
| **Nguyên nhân trực tiếp** | `bash scripts/hermes-session-boot.sh` luôn trả mã **3** ("chưa có mệnh lệnh") và in `DỪNG PHIÊN NGAY`, vì `.ai/handoff/INBOX.md` chưa từng có nội dung hợp lệ. |
| **Nguyên nhân gốc** | (1) Luật ĐIỀU 0 cũ biến kết quả đó thành lệnh **DỪNG**; (2) workflow `hermes-owner-loop.yml` lỗi tách marker nên không bao giờ ban hành lệnh; (3) lịch tự động bị tắt; (4) sandbox chat không có key/binary để gọi Hermes trực tiếp. |
| **Cách sửa** | Hermes trở thành **kênh cố vấn tùy chọn**: `boot` mặc định luôn thoát 0; lỗi/không có gợi ý không chặn phiên; chế độ strict chỉ khi Operator bật rõ. Sửa đồng bộ ~18 file luật + engine + workflow + test chống hồi quy. |

---

## 2. "Lịch sử cuộc chat" — nguồn dữ liệu đã dùng

Bản thân transcript chat của Arena **không đọc được từ repo** (đã ghi rõ trong
[`ARENA_VS_HERMES.md`](ARENA_VS_HERMES.md) mục 6: mỗi phiên Arena là trang giấy trắng với agent).
Vì vậy lịch sử được dựng lại từ **vết để lại trong repo và GitHub** — đây là bộ nhớ bền thật sự:

| Nguồn | Nội dung lấy được |
|---|---|
| PR **#12** (merge 23/10/2026) — "🧭 Hermes làm chủ mọi phiên agent" | Chính yêu cầu gốc: *"mỗi lần mở chế độ agent trên Arena thì Hermes tự động được gọi vào làm chủ"*. PR ghi rõ chính sách: *"không có mệnh lệnh hợp lệ thì phiên phải dừng, không tự quyết, không fallback im lặng"*. |
| `AGENTS.md` (bản cũ), `docs/HERMES_OWNER_PROTOCOL.md` (bản cũ) | ĐIỀU 0 + bảng mã 3/4/5/6 ⇒ **DỪNG**; "Ngoại lệ duy nhất: Operator nói bỏ qua Hermes phiên này". |
| `scripts/hermes_owner.py` (bản cũ) | `report_blocked()` in `⛔ … DỪNG PHIÊN NGAY` và trả 3/4/5/6; test `test_missing_directive_exits_3` **khẳng định** hành vi dừng. |
| GitHub Actions runs `40062072101`, `40062270254` (24/10/2026) | Cùng kết cục: job `summon failure`, các bước đầu xanh, bước **"Tách khối mệnh lệnh" đỏ**. Không có bước ghi `INBOX.md` nào chạy. |
| `gh run list --workflow=hermes-owner-loop.yml` | 2 lượt bấm tay lỗi; **15+ lượt schedule liên tiếp `skipped`** (25–27/10) vì biến `HERMES_OWNER_AUTO` không bật → không có lượt thử lại. |
| PR **#15** (mở 26/10/2026) — "fix: 4 lỗi chặn CI/vận hành" | Ghi nhận trực tiếp: *"Hermes owner loop fail 2 lượt → chưa từng có `INBOX.md` → mọi phiên agent bị chặn ở ĐIỀU 0"*. Sửa parser marker, cảnh báo Telegram... nhưng **vẫn giữ luật bắt buộc** và PR chưa merge vào `main`. |
| `Status.md` / `memory/MEMORY.md` (bản 23/10) | Nhiều lần khẳng định "Hermes là chủ repo; mọi phiên agent chạy boot; hết hạn/không có lệnh thì dừng" — bộ nhớ dài hạn cũng dạy AI cũ cách chặn phiên. |
| `.ai/handoff/INBOX.md`, `STATE.json` (bản hiện trường) | `INBOX.md` chỉ là stub "chưa có mệnh lệnh"; `STATE.json.active_directive = null`, `history = []` ⇒ **chưa từng có lệnh nào được ban hành**. Trên remote cũng không tồn tại nhánh `hermes-owner/state`. |
| `docs/ARENA_VS_HERMES.md` | Sandbox Arena không có API key provider, không giữ process, mạng allowlist ⇒ không thể gọi Hermes *trực tiếp* trong phiên chat. |

## 3. Dòng thời gian

| Thời điểm (UTC) | Sự kiện |
|---|---|
| 23/10 19:16 | Merge PR #12: Hermes Owner Protocol + ĐIỀU 0 (chính sách dừng cứng). |
| 24/10 04:22 & 04:25 | 2 lần bấm **Hermes owner loop** → lỗi ở bước tách marker. `hermes -z` chạy xong, `scripts/hermes_owner.py extract` không tìm được khối `<<<ZEUS_DIRECTIVE>>>` → exit 3. Không ghi `INBOX.md`, không mở PR. |
| 24–27/10 | Mọi lượt `schedule` (mỗi 6h) bị `skipped` do `HERMES_OWNER_AUTO != "on"`. Không có lệnh mới, không có cảnh báo rõ ràng tới Operator. |
| 24–27/10 | Mọi phiên agent mới chạy boot → mã 3 → in "DỪNG PHIÊN NGAY" → AI dừng ⇒ người dùng thấy **lỗi khi gọi Hermes làm chủ phiên chat**. |
| 26/10 | PR #15 mở, xác định lỗi và vá parser extraction (+6 test), nhưng không đổi chính sách dừng. PR còn mở, `main` chưa nhận vá. Comment trên PR vẫn hướng dẫn *"chạy lại workflow để `boot` trả 0 thay vì 3"* — tức là sửa triệu chứng (workflow), chưa sửa luật gây chặn phiên. |
| **28/10** | **Sửa tận gốc:** đổi toàn bộ luật sang TÙY CHỌN; port luôn vá parser; workflow lỗi thì cảnh báo thay vì chặn; thêm RCA này + test chống hồi quy. |

## 4. Chuỗi lỗi (failure chain)

```
Operator muốn "Hermes làm chủ phiên chat"
        │
        ▼
PR #12: AGENTS.md ĐIỀU 0 = "PHẢI boot; mã 3/4/5/6 ⇒ DỪNG"
        │
        ▼
Workflow owner loop: model in marker lệch (<<< ZEUS_DIRECTIVE >>>, **…**, code fence…)
        │
        ▼
extract regex cũ (chuỗi chính xác) không khớp  ⇒  job đỏ, không ghi INBOX.md
        │
        ▼
Lịch tự động bị tắt (HERMES_OWNER_AUTO != on)  ⇒  không có lượt sửa lỗi tự nhiên
        │
        ▼
INBOX.md là stub · STATE.active_directive = null · không có nhánh hermes-owner/state
        │
        ▼
boot: exit 3 + "⛔ DỪNG PHIÊN NGAY"  ──►  AI đọc luật ĐIỀU 0 ⇒ TỪ CHỐI LÀM VIỆC
        │
        ▼
Người dùng thấy: "gọi Hermes làm chủ phiên chat bị lỗi"
```

## 5. Nguyên nhân gốc (xếp theo mức độ quyết định)

1. **Thiết kế luật sai (P0).** Một kênh phụ thuộc vào LLM bên ngoài + GitHub Actions + secret +
   mạng + TTL bị dựng thành **cổng chặn cứng** cho mọi yêu cầu của người dùng. Chỉ cần một mắt
   xích lỗi, toàn bộ hệ thống chat bị khóa. Đây là single point of failure do **chính luật** tạo ra.
2. **Parser output LLM quá cứng (P0).** `_extract_directive()` cũ chỉ khớp đúng chuỗi
   `<<<ZEUS_DIRECTIVE>>>`. Model thực tế thêm dấu cách, bọc `**`, đổi hoa/thường, bọc code fence.
   Kết quả: 2 run đầu tiên của workflow đỏ ngay bước tách khối — trước khi kịp sinh ra lệnh nào.
3. **Không có đường hồi phục tự động (P1).** `HERMES_OWNER_AUTO` không bật ⇒ `schedule` skipped;
   TTL mặc định 72h ⇒ dù có lệnh thì sau 3 ngày cũng hết hạn; không có fallback "không có lệnh
   thì tự quyết". Hệ thống rơi vào trạng thái khóa vĩnh viễn cho đến khi người dùng can thiệp tay.
4. **Môi trường không khớp kỳ vọng (P1).** Sandbox phiên chat không có `OPENROUTER_API_KEY`,
   không có binary `hermes`, mạng allowlist chặn nhiều host. "Gọi Hermes trực tiếp trong phiên"
   là không thể; `--live` chỉ chạy được trên máy/VPS/Codespaces có key. Giao thức vì thế phải đi
   vòng qua repo — càng không nên là điều kiện tiên quyết.
5. **Luật bị nhân bản ở quá nhiều nơi (P1).** Cùng một mệnh lệnh "dừng" nằm trong: `AGENTS.md`,
   `README.md`, `.ai/CONSTITUTION.md` (gián tiếp), `Status.md`, `memory/MEMORY.md`,
   `.ai/handoff/README.md`, `.ai/handoff/INBOX.md`, `docs/HERMES_OWNER_PROTOCOL.md`,
   `skills/hermes-owner/SKILL.md`, 2 wrapper script, engine (thông báo in ra), prompt gửi chính
   Hermes (`hermes_owner_brief.py`), skill `zeus-context` sinh tự động, và **cả unit test**
   (`assertIn("DỪNG PHIÊN", ...)`). Sửa 1–2 file không đủ: AI vẫn gặp luật cũ ở file khác.
6. **Từ ngữ thiên vị quyền lực (P2).** "chủ", "owner", "mệnh lệnh", "chỉ thực thi", "không tự
   quyết" khiến model có xu hướng tuân phục và dừng phiên, ngay cả khi người dùng đang yêu cầu
   việc khác. Tên gọi làm lỗi thiết kế nặng thêm.

## 6. Điều đã sửa (toàn bộ luật)

| Tầng | File | Thay đổi |
|---|---|---|
| Luật gốc | `AGENTS.md` | ĐIỀU 0 viết lại: Hermes **có thể gọi hoặc không**, không chặn phiên; bảng mã 3/4/5/6 đều "tiếp tục"; closeout tùy chọn; strict chỉ do Operator bật. |
| Hiến pháp | `.ai/CONSTITUTION.md` | Operator là quyền cao nhất; thứ tự ưu tiên khi xung đột; Hermes là kênh tùy chọn. |
| Cổng repo | `README.md`, `Status.md`, `memory/MEMORY.md` | Bỏ banner "Hermes là chủ"; ghi nhận sự cố; cập nhật bộ nhớ dài hạn. |
| Hộp thư | `.ai/handoff/{INBOX.md,README.md,STATE.json,OUTBOX.md}` | "Chưa có gợi ý = bình thường"; seal sai không dừng; `policy: "optional"`; báo cáo tùy chọn. |
| Đặc tả | `docs/HERMES_OWNER_PROTOCOL.md` | Viết lại 13 mục theo chính sách tùy chọn, giữ nguyên định dạng dữ liệu/seal. |
| Skill | `skills/hermes-owner/SKILL.md`, `skills/README.md` | Hermes là cố vấn; cấm Hermes ra lệnh dừng phiên; thêm mục skill 8. |
| Engine | `scripts/hermes_owner.py` | `POLICY="optional"`; `boot` mặc định thoát 0 + JSON `blocking:false`; `--strict`/`HERMES_OWNER_STRICT=1` mới dừng; `INBOX_STUB`, banner, LIVE_PROMPT, status, closeout đổi ngữ nghĩa; parser `extract` chịu marker lệch. |
| Wrapper | `scripts/hermes-session-boot.sh`, `hermes-session-closeout.sh` | Comment "tùy chọn, không chặn"; thiếu python3 cũng thoát 0. |
| Prompt gửi Hermes | `scripts/hermes_owner_brief.py` | Hermes là CỐ VẤN TÙY CHỌN; cấm yêu cầu agent dừng phiên; quy tắc marker rõ ràng. |
| Ngữ cảnh sinh | `scripts/gen-zeus-context.py` | Skill `zeus-context` nhắc Hermes không bắt buộc, không chặn phiên. |
| Workflow | `.github/workflows/hermes-owner-loop.yml` | Lỗi tách khối chỉ cảnh báo, không đỏ job; ghi chú "kênh tùy chọn" trong PR body; lỗi Hermes không chặn phiên. |
| CI | `.github/workflows/hermes-owner-protocol-ci.yml` | Chạy `test_hermes*.py`, gồm test chống hồi quy chính sách. |
| Test | `scripts/tests/test_hermes_owner.py`, `test_hermes_optional_rules.py` | 23 test engine/extract/end-to-end + test quét file luật và hành vi wrapper. |
| Tài liệu khác | `docs/ARENA_VS_HERMES.md`, file RCA này | Ghi chú chính sách và toàn bộ phân tích. |

## 7. Cách vận hành bây giờ

- **Mặc định:** người dùng yêu cầu gì, AI làm đó. Không cần gọi Hermes, không cần workflow,
  không cần secret. `INBOX.md` trống là bình thường.
- **Nếu muốn gọi Hermes:** `bash scripts/hermes-session-boot.sh` (luôn thoát 0). Có gợi ý hợp lệ
  thì đọc thêm; không có thì tiếp tục việc đang làm.
- **Nếu muốn Hermes ban hành gợi ý:** Actions → `Hermes owner loop` → Run workflow. Workflow lỗi
  ⇒ chỉ cảnh báo; **không sao**, phiên chat vẫn chạy. Muốn tự động thì đặt `HERMES_OWNER_AUTO=on`.
- **Nếu vẫn muốn chế độ cũ (dừng khi thiếu lệnh):** chỉ Operator nói rõ, rồi dùng
  `bash scripts/hermes-session-boot.sh --strict` hoặc `HERMES_OWNER_STRICT=1`. AI không tự bật.

## 8. Kiểm chứng

```bash
bash scripts/hermes-session-boot.sh --offline          # exit 0, "KHÔNG BẮT BUỘC…"
bash scripts/hermes-session-boot.sh --offline --json   # blocking: false
bash scripts/hermes-session-boot.sh --offline --strict # exit 3 (chỉ khi cố tình bật)
python3 scripts/hermes_owner.py selftest               # OK
python3 -m unittest discover -s scripts/tests -p 'test_hermes*.py' -v
python3 scripts/validate-skills.py --strict skills/hermes-owner
bash -n scripts/hermes-session-boot.sh scripts/hermes-session-closeout.sh
```

## 9. Rủi ro còn lại

- **Tên cũ vẫn gây nhầm lẫn** (`hermes-owner/state`, `MỆNH LỆNH`, `owner`). Đổi tên hàng loạt sẽ
  gãy automation/dữ liệu cũ; giải pháp chọn là giữ tên kỹ thuật + đổi ngữ nghĩa ở mọi file luật.
- **Chế độ strict vẫn tồn tại.** Nếu Operator bật rồi quên tắt, lỗi chặn phiên có thể tái diễn.
  `policy: "optional"` trong `STATE.json` và test chống hồi quy giúp phát hiện sớm.
- **Chất lượng gợi ý phụ thuộc model/brief.** Gợi ý sai giờ chỉ gây tốn thời gian đọc, không
  còn gây chết phiên — đó là mục tiêu chính của thay đổi này.
- **PR #15 vẫn mở.** Nó chứa vá parser extraction và nhiều fix khác. Khi merge, cần giữ chính
  sách tùy chọn của các file luật; CI test `test_hermes_optional_rules.py` sẽ báo nếu PR đưa lại
  câu "bắt buộc/dừng phiên".
