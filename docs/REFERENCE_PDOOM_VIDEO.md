# Học từ `mexicat/pdoom-video` — bài học cho ZEUS / FlowKit

> Ngày học: 2026-10-28 · Nguồn: https://github.com/mexicat/pdoom-video (MIT, ~3.5k stars,
> TypeScript ~1.15 MB + Python ~65 KB). Đây là **ghi chú học tập**, không phải fork: mình đọc
> source + docs qua `git clone --depth 1`, không copy code, nhạc, lời bài hát hay font vào ZEUS.
> Sandbox Arena không có `bun` / Chrome GPU / ffmpeg đủ mạnh để render thử, nên các kết luận
> dưới đây dựa trên **đọc mã nguồn và tài liệu**, không phải chạy render thật.

---

## 1. Repo đó là gì (1 đoạn)

Một **music video 156.651 s được vẽ hoàn toàn bằng code**: mọi khung hình là một **hàm thuần của
thời gian** `frame = f(t)`. Cùng một engine TypeScript + three.js chạy **preview trong trình duyệt**
và **export 1080p60 / 4K60** offline, nên khung hình preview và file xuất ra giống hệt nhau.
Nhạc/lyrics được phân tích offline bằng Python (Demucs + CTC + Whisper + beat tracking) rồi
**commit kết quả ra JSON**; 17+ "plate" (scene) là các module TS độc lập; hai tài liệu
`docs/TREATMENT.md` (style bible) và `docs/ENGINE.md` (luật viết scene) đóng vai trò **hợp đồng cho
nhiều agent cùng làm việc** — repo được tạo với Claude Code.

## 2. Sơ đồ kiến trúc

```text
audio/pdoom.mp3 + lyrics/lyrics.src.js
        │  (offline, nặng, Python/uv: Demucs, wav2vec2/MMS CTC, mlx-whisper,
        │   librosa onset/beat/section; có anchor tay + confidence + QA plot)
        ▼
data/lyrics.json   (word/syllable timing + conf)
data/audio.json    (132.007 BPM, beats, downbeats, sections, 100 fps envelopes, onsets)
        │  (HỢP ĐỒNG DỮ LIỆU — commit vào repo, render không cần model)
        ▼
app/src/timeline.ts  ← cắt cảnh theo NỘI DUNG lyric ("cut('There was a sudden drop')")
        │              rồi snap vào lưới beat, KHÔNG hard-code giây
        ▼
app/src/engine/*     ← Engine.render(t): load scene lazy, composite transition,
        │              HUD, post (bloom/halation/grain), adaptive motion blur
        ▼
app/src/scenes/*.ts  ← mỗi plate 1 file, class extends Scene, render(f, out) thuần f.t
        │
        ├── preview: Vite + `?t=23`, phím space/←/→/[/]/l/h
        └── export : scripts/render.ts → 2 headless Chrome (?export=1)
                     → raw rgb24 over WebSocket (có ACK/backpressure)
                     → 1 ffmpeg (BT.709, x264 CRF16, AAC) → out/*.mp4
```

## 3. Điểm đáng học nhất: 6 cơ chế lõi

### 3.1 Deterministic frame = f(t) — nền tảng của mọi thứ khác

`docs/ENGINE.md` quy định rõ: **output phải là hàm thuần của `f.t`**, cấm `Math.random()`,
`Date.now()`, `performance.now()`; randomness dùng `mulberry32(seed)`/`hash()`; jitter theo
`frameIdx(t)` chứ không `Math.floor(t*60)`. Nhờ vậy:

- render mọi sub-frame **theo bất kỳ thứ tự nào** vẫn ra cùng ảnh;
- tua/preview/export/still đều nhất quán;
- adaptive motion blur lấy trung bình 4→12→36→108→324 sub-frame **theo từng ô 32×32 px**, dừng
  khi sai số ước lượng < `--tol` (mặc định 3/255); ô đã hội tụ được **depth-mask** để GPU bỏ qua
  (early-Z), nên cảnh đứng yên gần như không tốn thêm.
- `stateful = true` là ngoại lệ có kiểm soát: phải `reset()` + tích phân `f.dt`, engine fast-forward
  sau khi seek, và **bị từ chối** khi export adaptive.

### 3.2 Tách "phân tích" và "render" bằng hợp đồng JSON

`analysis/` (uv, Python 3.12, torch/demucs/librosa/mlx-whisper) sinh ra 2 file nhỏ được commit:
`data/lyrics.json` (31 KB: từng line → word → `start/end/conf/syl`) và `data/audio.json` (755 KB:
BPM, beats, downbeats, sections, 100 fps envelopes, kick/snare/hat/vocal onsets). Toàn bộ stem,
model weight ~4 GB, intermediate được `.gitignore`. Renderer **không cần Python, không cần GPU
model**, chỉ đọc 2 JSON. Sửa lời/bài hát thì chạy lại pipeline, không sửa code render.

Hay nhất: `align.py` không tin model mù quáng — nó **cross-check 2 CTC model + Whisper**, chấm
`conf`, cho phép `FIX = {(line, token): {start, conf}}` với **ghi chú lý do âm học** ngay trong code
(ví dụ "lead buried under sustained backing ah pad", "pitch drop to schwa at 21.35"). Dữ liệu có
vết kiểm toán.

### 3.3 Timeline neo vào ngữ nghĩa, không neo vào giây

```ts
const cut = (q: string, nth = 0, tol = 0.02) =>
  au.timeOfBeat(Math.floor(au.beatAt(ly.get(q, nth).words[0].start + tol)));
```

`makeTimeline()` tìm line bằng **nội dung** (`ly.get("I'm upping", 3)`), lấy mốc beat gần nhất,
rồi khai báo 22 entry `E('hook3','hook', b.hook3, b.clips, { params: {n:3} })`. Đổi bản nhạc/đổi
timing → sửa lại data, timeline tự bám theo; không có con số giây rải rác trong scene.

### 3.4 Một engine → preview và export (không có "render riêng")

`?export=1` chỉ bật `window.__pdoom` với `still(t)`, `png()`, `stream(from,to,fps)`. `render.ts`
dùng `playwright-core` mở 2 headless Chrome, chia khung thành chunk 8 frame, gửi **rgb24** qua
WebSocket từ một Web Worker (buffer pool + ACK, tối đa vài frame in-flight), rồi một `ffmpeg`
duy nhất nhận frame theo đúng thứ tự. Bộ nhớ có hạn: reorder buffer `--mem-gb 1`, quá thì **spool ra
đĩa** `--spool-gb 20`. Kèm các chế độ QA: `stills`, `sheet` (contact sheet, `--cuts` lấy mọi điểm
cắt), `perf`, `plates` (tạo lại ảnh thumbnail cho outro), `video --only a,b` để cô lập scene lỗi.

Chi tiết nhỏ nhưng đáng học: export gắn **BT.709** (`scale=out_color_matrix=bt709,setparams=...`)
vì ffmpeg mặc định BT.601 trong khi player/YouTube giải mã HD không tag bằng BT.709 → màu lệch.
Và `PDOOM_NO_HMR=1` tắt live-reload trong lúc render để không reload trang giữa chừng.

### 3.5 Style bible chống "AI slop"

`docs/TREATMENT.md` là tài liệu ~24 KB gồm: palette 8 màu (ink `#0A0A0B`, signal `#FF4D12`, một
accent acid duy nhất dùng đúng ~2 s), 4 họ font với vai trò riêng, quy tắc karaoke (word highlight
không được chạy trước giọng hát), 5 motif đặc trưng, bảng 17 plate kèm lyric và "owner", và một
danh sách **cấm**: không neon tím/cyan, không não phát sáng, không mưa code Matrix, không lens-flare,
không ảnh look-AI-generated, không emoji/mascot. Đây là thứ biến output của AI thành sản phẩm có
gu — ZEUS đang thiếu một tài liệu tương đương cho FlowKit.

### 3.6 Hợp đồng làm việc đa agent

`docs/ENGINE.md` viết thẳng cho "scene authors": mỗi scene **một file**, không sửa engine, không sửa
`timeline.ts`, lazy `import.meta.glob` để **scene hỏng không làm sập build**, `--only` để cô lập,
`SCENE ERRORS` + console log được in ra, typecheck từng file, quy tắc `render()` phải ghi đè toàn bộ
`out` (linear HDR), ngân sách < 25 ms/frame. Đây chính là dạng "luật" mà ZEUS `AGENTS.md` đang làm
cho AI — nhưng áp xuống cấp mã nguồn rất cụ thể.

---

## 4. Đối chiếu với ZEUS (cái có / cái thiếu)

| Chủ đề | pdoom-video | ZEUS hiện tại | Đáng làm |
|---|---|---|---|
| Render lặp lại được | `f(t)` thuần, seeded PRNG | `flowkit/agent/services/flow_batch.py` dùng `random.randint(1,1e9)` khi thiếu seed; pipeline tạo clip rồi concat | Thêm layer "timing project" thuần định cho phần overlay/caption/cut; seed bắt buộc khi review lại |
| Dữ liệu timing | 2 JSON commit, phân tích tách rời | `flowkit/skills/fk-gen-music.md`, `fk-concat-fit-narrator.md` fit narration bằng ffmpeg, chưa có beat/word grid | Sinh `timing.json` (beats/sections/word) bằng Python offline; commit; dashboard đọc |
| Cắt cảnh | `cut('lyric text')` + snap beat | Cảnh trong SQLite, duration do model trả về | Cho phép "cut on beat" khi concat; sửa lời/nhạc không phải sửa code |
| Preview = export | Cùng engine, `?export=1` | Dashboard Vite preview trạng thái pipeline; render thật ở Flow/ffmpeg | Một renderer Canvas/Three cho text overlay + transition, chạy được cả trên Vercel preview lẫn headless Chrome |
| QA hình ảnh | `stills/sheet/perf/plates/--only` | `scripts/media-batch.py` có thumbnail + preset, **chưa có contact sheet** | Thêm lệnh `sheet` (grid ảnh có nhãn thời gian) — rẻ, dùng ngay được |
| Style bible | `TREATMENT.md` | `memory/flowkit-ai-filmmaking.md` + `skills/flowkit-ai-filmmaker/SKILL.md` (quy tắc prompt/entity) | Viết `flowkit/docs/STYLE_BIBLE.md`: palette, font, motion rules, danh sách "cấm AI slop"; prompt generator đọc file này |
| Kiểm chứng dữ liệu | `conf`, `FIX` có lý do, QA plot | FlowKit review clip bằng AI (`fk-review-video`) | Khi review, lưu confidence + lý do vào DB thay vì chỉ điểm số |
| Đa agent | 1 file/scene, lazy import, `--only` | `flowkit/AGENTS.md`, `flowkit/skills/fk-*.md` | Áp lazy-load cho scene renderer tương lai; có chế độ chạy riêng 1 cảnh |
| 4K | logical 1920×1080 ↔ physical `SCALE`, `pxLine()` | `media-batch.py` preset cố định pixel | Tách "logical canvas" khỏi output size khi làm overlay |
| Bản quyền | Code MIT; nhạc/lyrics **loại khỏi license**; font OFL; credits rõ | FlowKit snapshot đã giữ MIT + provenance | Giữ nguyên thói quen này khi mượn asset/video/mẫu nhạc |
| CI | **Không có** `.github/` (chạy local, QA bằng stills) | ZEUS có 17 workflow + CI chặt | Đừng bỏ CI để theo repo này; chỉ học quy trình QA local của nó |

---

## 5. Lộ trình áp dụng (đề xuất, từ rẻ đến đắt)

**Phase A — 1 phiên, không đụng runtime (khuyến nghị làm trước)**

1. `flowkit/docs/STYLE_BIBLE.md`: palette + type scale + motion/ease + 10 điều cấm (anti-slop),
   dùng làm nguồn cho mọi prompt sinh ảnh/video.
2. `scripts/media-batch.py sheet`: contact sheet có nhãn timestamp (Pillow, không cần ffmpeg),
   kèm test nhỏ. Đây là "QA bằng mắt" như `render.ts sheet`.
3. Quy tắc determinism ngắn trong `AGENTS.md` / `flowkit/AGENTS.md`: code render không dùng
   random/time thật; mọi seed phải ghi lại.

**Phase B — hợp đồng dữ liệu timing**

4. `flowkit/agent/services/timing.py` (stdlib + librosa tuỳ chọn) → `project/timing.json`
   `{duration, bpm, beats[], downbeats[], sections[], words[{w,start,end,conf}]}`. Chạy offline
   một lần, commit output, không bắt dashboard tải model.
5. `flowkit/agent/services/timeline.py`: `cut(query)` + `snapToBeat()` tương tự `timeline.ts`;
   unit test với một `timing.json` giả cố định.
6. Dashboard: scrubbing theo beat + hiển thị word highlight (karaoke) cho caption.

**Phase C — renderer preview/export thống nhất**

7. Một module `flowkit/dashboard/src/render/` (Canvas2D/three.js) với `renderFrame(project, t)`
   thuần; preview trong Vite, export bằng headless Chrome + ffmpeg (Colab hoặc Actions).
8. Backpressure: buffer có hạn + spool ra đĩa khi render 4K (đọc `render.ts video()`), tránh OOM.
9. Nếu cần motion blur: adaptive sampling từng tile là **tham vọng cao** (GPU ~23 GB ở 4K),
   chỉ nên học ý tưởng "dừng sớm khi hội tụ", chưa nên implement.

## 6. Không nên mang sang ZEUS

- **Nhạc, lyrics, ảnh plate, font**: bài hát/lyrics không thuộc MIT license; font giữ OFL riêng.
  Chỉ học cấu trúc dữ liệu, không copy nội dung. Repo nguồn ghi credits rất rõ — ZEUS nên làm vậy.
- **Yêu cầu phần cứng**: 4K với 108–324 sub-frame tốn ~23 GB RAM, GPU M-series; `mlx-whisper` là
  macOS-only. ZEUS cloud-first (Colab/VPS/điện thoại) cần bản nhẹ hơn: 1080p, `--samples 4` draft,
  rồi tăng dần.
- **Thiếu CI**: repo đó không có workflow nào; QA hoàn toàn bằng lệnh local. ZEUS đã có CI xanh —
  đừng đánh đổi.
- **Hard-code thủ công**: `SECTION_BARS`, `ANCHORS`, `FIX` trong `analysis/` là dữ liệu riêng của
  bài hát đó. Học **cơ chế** (anchor có lý do + confidence), đừng copy số.

## 7. Chạy thử repo nguồn trên máy có bun/Chrome (tham khảo)

```bash
git clone --depth 1 https://github.com/mexicat/pdoom-video
cd pdoom-video/app && bun install && bunx vite     # http://localhost:5173/?t=23
bun scripts/render.ts stills --t 7.5,14.3,100.2 --only open,loss --out ../out/wip
bun scripts/render.ts sheet --from 20 --to 35 --n 12 --cols 4 --out ../out/sheet.png
bun scripts/render.ts video --samples auto --shutter 0.2 --out ../out/pdoom.mp4
# phân tích lại (cần model ~4GB): cd analysis && uv run python align.py && uv run python analyze.py
```

## 8. Liên quan trong ZEUS

- `docs/FLOWKIT_INTEGRATION.md` · `flowkit/README.md` · `flowkit/ARCHITECTURE.md`
- `memory/flowkit-ai-filmmaking.md` · `skills/flowkit-ai-filmmaker/SKILL.md`
- `scripts/media-batch.py` · `docs/HERMES_FULL_CAPABILITY.md` (media tools)
- `docs/HERMES_AUTO_SYNC.md` (cách đưa tài liệu/skill vào runtime Hermes)
