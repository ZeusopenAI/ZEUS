# Prototype: deterministic `renderFrame(project, t)`

Một bản thu nhỏ của ý tưởng cốt lõi trong
[`docs/REFERENCE_PDOOM_VIDEO.md`](../../docs/REFERENCE_PDOOM_VIDEO.md): **mọi khung hình là hàm thuần
của thời gian**, và **cùng một hàm vẽ chạy cho preview lẫn export**.

```text
project.json ──► src/timeline.mjs  (cắt cảnh theo lyric + snap vào beat)
                      │
                      ▼
              src/drawFrame.mjs   ← DUY NHẤT 1 file vẽ, thuần f(t)
                 ╱            ╲
   preview/ (Chrome)      src/render.mjs (Node + @napi-rs/canvas)
   Canvas2D thật          headless Canvas2D (Skia)
        │                        │
        └──── cùng HASH pixel ───┴──► export.mjs → raw rgb24 → 1 ffmpeg → .mp4
                                     sheet.mjs → contact sheet PNG
```

## Chạy

```bash
cd prototypes/deterministic-render
npm install                      # chỉ 1 dependency: @napi-rs/canvas
npm test                         # 11 test, ~0.3s

npm run preview                  # http://localhost:5173  (?t=5.5, ?scale=2)
npm run export -- --from 0 --to 12 --fps 30 --out /tmp/zeus.mp4
npm run sheet  -- --from 0 --to 12 --n 8 --cols 4 --out /tmp/sheet.png
```

- Preview: `space` play/pause, `←/→` ±1s (shift ±5s), `,/./` ±1 frame, `[/]` chuyển scene,
  `l` loop scene, `h` ẩn UI. Ô **HASH** trên màn hình là FNV-1a của toàn bộ pixel khung hình.
- Export in `first=<hash>`. Nếu hash tại cùng `t`, cùng `scale`, cùng `samples` khớp với preview
  nghĩa là **hai backend vẽ ra đúng cùng một ảnh**. Đây là cách kiểm chứng parity không cần tin
  vào lời hứa "cùng code".
- Cần `ffmpeg` trên PATH. Nếu không có: `python3 -m pip install imageio-ffmpeg` rồi
  `FFMPEG=$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())') npm run export -- ...`
  (hoặc `--ffmpeg /đường/dẫn/ffmpeg`).

## Các quy tắc được cố tình giữ (từ repo tham khảo)

| Quy tắc | Ở đây |
|---|---|
| `frame = f(project, t)`; cấm `Math.random/Date.now/performance.now` | `src/drawFrame.mjs`, `src/util.mjs`; có test quét source |
| Random có seed | `mulberry32(seed)`, `hash32(seed, frameIdx, i, ...)` |
| Jitter theo `frameIdx(t)` chứ không `t` liên tục | hạt grain / tia lửa trong `drawFrame.mjs` |
| Timeline neo ngữ nghĩa + snap beat | `src/timeline.mjs`: `cut('PREVIEW') === 5.5` ở 120 BPM; đổi 240 BPM → 5.75 |
| Dữ liệu tách khỏi code | `project.json` là hợp đồng (BPM, words, scenes, palette, seed) |
| Logical ≠ physical resolution | `surface(..., scale)`: vẽ ở 480×270 logical, xuất 960×540 khi `--scale 2`; có test so sánh từng pixel |
| Một engine → preview + export | `drawFrame.mjs` được import bởi cả hai |
| QA bằng mắt | `sheet.mjs` (`--cuts` lấy đúng các điểm cắt) |
| Backpressure | `export.mjs` đợi `drain` trước khi ghi frame tiếp vào stdin ffmpeg |
| Sub-frame motion blur vẫn deterministic | `--samples N` lấy trung bình N sub-frame; có golden hash |

## Cố tình làm đơn giản (và khác gì production)

- **Chỉ dùng `fillRect` màu đặc**, không `rgba/globalAlpha`, không `fillText`, không path/gradient.
  Lý do: Skia (headless) và Chrome tô màu bán trong suốt hơi khác nhau; trộn màu trước
  (`colour(hex, ink, k)`) thì hash hai bên khớp chính xác. Font cũng tự vẽ bằng bitmap 3×5.
- **Không có three.js / WebGL / post-processing / adaptive sampling theo tile**. Đây là bản chứng
  minh hợp đồng `f(t)`, không phải engine sản xuất. Bước tiếp theo nếu làm thật: thay
  `src/render.mjs` bằng headless Chrome + `window.__zeus.still(t)` + WebSocket rgb24 như
  `pdoom-video/app/scripts/render.ts` — **không phải sửa `drawFrame.mjs`**.
- **Không có audio**. Thêm `-i music.mp3 -c:a aac -shortest` vào lệnh ffmpeg trong `export.mjs`.
- **Preview dùng `requestAnimationFrame` để lên lịch**, nhưng `t` tăng đúng `1/fps` mỗi frame
  (không đọc đồng hồ), nên dãy ảnh preview trùng dãy ảnh export.
- `out/` và `node_modules/` nằm trong `.gitignore`; không commit video/ảnh sinh ra.

## Kiểm chứng đã chạy (2026-10-28)

```
npm test                       -> 11/11 pass
node export.mjs --from 0 --to 2 --fps 30  -> 60 frames 480x270, 0.5s, first=13a143d2
node export.mjs --scale 2 --samples 4     -> 8 frames 960x540, first=c5c15959
node sheet.mjs --n 8 --cols 4             -> 990x320 PNG, 8 khung
ffmpeg -i clip.mp4                        -> h264 yuv420p 480x270 30fps, 2.00s
```

Mở `out/sheet.png` (tạo lại bằng lệnh trên) để xem 8 khung trải đều 12 giây.
