#!/usr/bin/env node
// Offline exporter: the SAME drawFrame() as the browser preview, rendered by a
// headless Canvas2D (@napi-rs/canvas) and streamed as raw rgb24 into ONE ffmpeg.
//
//   node export.mjs --from 0 --to 12 --fps 30 --out /tmp/zeus.mp4
//   node export.mjs --from 0 --to 1 --fps 12 --scale 2 --samples 4 --out /tmp/clip.mp4
//   FFMPEG=/path/to/ffmpeg node export.mjs ...        # override binary
//
// No audio in the prototype; add -i <music> -c:a aac when wiring a real song.

import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderPixels, toRGB24, makeCanvas } from './src/render.mjs';
import { makeTimeline } from './src/timeline.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv[i + 1] : d; };
const flag = (k) => argv.includes(`--${k}`);

function findFFmpeg() {
  const explicit = opt('ffmpeg') || process.env.FFMPEG;
  if (explicit) {
    if (!existsSync(explicit)) throw new Error(`--ffmpeg không tồn tại: ${explicit}`);
    return explicit;
  }
  const which = spawnSync('sh', ['-c', 'command -v ffmpeg'], { encoding: 'utf8' });
  if (which.status === 0 && which.stdout.trim()) return which.stdout.trim();
  // Fallback for sandboxes without system ffmpeg (imageio-ffmpeg wheel).
  for (const py of ['python3', 'python']) {
    const r = spawnSync(py, ['-c', 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())'], { encoding: 'utf8' });
    if (r.status === 0 && r.stdout.trim().startsWith('/')) return r.stdout.trim();
  }
  throw new Error('Không tìm thấy ffmpeg. Cài hệ thống hoặc: python3 -m pip install imageio-ffmpeg');
}

async function main() {
  const projectPath = path.resolve(opt('project', path.join(HERE, 'project.json')));
  const project = JSON.parse(readFileSync(projectPath, 'utf8'));
  const fps = +opt('fps', String(project.fps));
  const from = +opt('from', '0');
  const to = Math.min(+opt('to', String(project.duration)), project.duration);
  const scale = Math.max(1, Math.round(+opt('scale', '1')));
  const samples = Math.max(1, Math.round(+opt('samples', '1')));
  const shutter = +opt('shutter', '0.2');
  const out = path.resolve(opt('out', path.join(HERE, 'out', 'zeus.mp4')));
  const ffmpeg = findFFmpeg();

  const f0 = Math.round(from * fps), f1 = Math.round(to * fps);
  const total = Math.max(1, f1 - f0);
  const pw = project.width * scale, ph = project.height * scale;
  const timeline = makeTimeline(project);
  mkdirSync(path.dirname(out), { recursive: true });

  const args = [
    '-y', '-loglevel', 'error',
    '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', `${pw}x${ph}`, '-r', String(fps), '-i', 'pipe:0',
    '-an', '-c:v', 'libx264', '-preset', opt('preset', 'veryfast'),
    '-crf', opt('crf', '18'), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out,
  ];
  const ff = spawn(ffmpeg, args, { stdio: ['pipe', 'ignore', 'pipe'] });
  let ffErr = '';
  ff.stderr.on('data', (b) => { ffErr = (ffErr + b.toString()).slice(-4000); });

  const canvas = makeCanvas(project, scale);
  const started = Date.now(); // wall clock is fine in the CLI; the renderer itself never sees it
  let firstHash = '', lastHash = '';

  for (let i = 0; i < total; i++) {
    const t = (f0 + i) / fps;
    const frame = renderPixels(project, t, { scale, samples, shutter, canvas });
    if (!firstHash) firstHash = frame.hash;
    lastHash = frame.hash;
    const raw = toRGB24(frame.data);
    if (!ff.stdin.write(raw)) await once(ff.stdin, 'drain');
    if (flag('verbose') && (i % Math.max(1, Math.floor(fps)) === 0)) {
      console.log(`  f=${i}/${total}  t=${t.toFixed(2)}  hash=${frame.hash}`);
    }
  }
  ff.stdin.end();
  const [code] = await once(ff, 'exit');
  if (code !== 0) throw new Error(`ffmpeg exit ${code}:\n${ffErr}`);

  const secs = ((Date.now() - started) / 1000).toFixed(1);
  console.log(`OK: ${out}`);
  console.log(`   ${total} frames  ${pw}x${ph}  ${fps}fps  scale=${scale}  samples=${samples}  ${secs}s`);
  console.log(`   first=${firstHash}  last=${lastHash}  (hash này in được cả trong preview để đối chiếu)`);
  console.log(`   timeline: ${timeline.map((s) => `${s.id}[${s.start.toFixed(2)}-${s.end.toFixed(2)}]`).join(' ')}`);
}

main().catch((e) => { console.error('LỖI export:', e.message); process.exit(1); });
