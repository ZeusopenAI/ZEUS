#!/usr/bin/env node
// QA contact sheet — "nhìn bằng mắt" như `render.ts sheet` của pdoom-video.
//   node sheet.mjs --from 0 --to 12 --n 8 --cols 4 --out /tmp/sheet.png
//   node sheet.mjs --times 0,2.5,5.5,8.5 --out /tmp/sheet.png
//   node sheet.mjs --cuts --out /tmp/cuts.png     # one frame at every scene boundary

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createCanvas } from '@napi-rs/canvas';
import { drawFrame } from './src/drawFrame.mjs';
import { makeTimeline } from './src/timeline.mjs';
import { drawText, colour } from './src/util.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv[i + 1] : d; };
const flag = (k) => argv.includes(`--${k}`);

const project = JSON.parse(readFileSync(path.resolve(opt('project', path.join(HERE, 'project.json'))), 'utf8'));
let times;
if (flag('cuts')) {
  times = makeTimeline(project).map((s) => s.start).filter((t) => t < project.duration);
} else if (opt('times')) {
  times = opt('times').split(',').map(Number);
} else {
  const from = +opt('from', '0'), to = +opt('to', String(project.duration)), n = +opt('n', '8');
  times = Array.from({ length: n }, (_, i) => n === 1 ? from : from + (to - from) * i / (n - 1));
}

const cols = Math.max(1, +opt('cols', '4'));
const cw = +opt('cell-w', '240'), ch = Math.round(cw * project.height / project.width);
const pad = 6, label = 16;
const rows = Math.ceil(times.length / cols);
const W = cols * (cw + pad) + pad, H = rows * (ch + label + pad) + pad;
const sheet = createCanvas(W, H);
const ctx = sheet.getContext('2d');
const ink = project.palette.ink, bone = project.palette.bone, signal = project.palette.signal;
ctx.fillStyle = ink;
ctx.fillRect(0, 0, W, H);

times.forEach((t, i) => {
  const x = pad + (i % cols) * (cw + pad);
  const y = pad + Math.floor(i / cols) * (ch + label + pad);
  const frame = createCanvas(project.width, project.height);
  drawFrame(frame.getContext('2d'), project, t, { scale: 1 });
  ctx.drawImage(frame, x, y + label, cw, ch);
  drawText(ctx, `T=${t.toFixed(2)}S`, x + 2, y + 2, 1, colour(bone, ink, 0.85), 1);
  ctx.fillStyle = colour(signal, ink, 0.9);
  ctx.fillRect(x, y + label, 2, ch);
});

const out = path.resolve(opt('out', path.join(HERE, 'out', 'sheet.png')));
mkdirSync(path.dirname(out), { recursive: true });
writeFileSync(out, sheet.toBuffer('image/png'));
console.log(`OK: ${out} (${times.length} khung, ${W}x${H})`);
