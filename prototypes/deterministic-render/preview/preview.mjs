// Browser player. NOTE: wall-clock time is used ONLY to schedule animation
// frames; the time passed to drawFrame() advances by exactly 1/fps per frame,
// so the sequence of images equals the exporter's frame-by-frame loop.

import { drawFrame, frameInfo } from '../src/drawFrame.mjs';
import { hashPixels, clamp, frameIdx } from '../src/util.mjs';
import { makeTimeline } from '../src/timeline.mjs';

const qs = new URLSearchParams(location.search);
const scale = Math.max(1, Math.round(+qs.get('scale') || 1));
const project = await fetch('/project.json').then((r) => r.json());
const timeline = makeTimeline(project);

const canvas = document.getElementById('c');
canvas.width = project.width * scale;
canvas.height = project.height * scale;
const ctx = canvas.getContext('2d', { willReadFrequently: true });
const scrub = document.getElementById('scrub');
scrub.max = String(project.duration);
scrub.step = String(1 / project.fps);

let t = clamp(+qs.get('t') || 0, 0, project.duration);
let playing = false;
let loopScene = false;

const el = (id) => document.getElementById(id);
function render() {
  const info = drawFrame(ctx, project, t, { scale });
  const px = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  el('t').textContent = t.toFixed(2);
  el('f').textContent = String(frameIdx(t, project.fps));
  el('beat').textContent = info.beat.toFixed(1);
  el('scene').textContent = info.scene.id.toUpperCase();
  el('hash').textContent = hashPixels(px);
  el('state').textContent = playing ? '▶ playing' : '⏸ paused';
  scrub.value = String(t);
}

function seek(v) { t = clamp(v, 0, project.duration); render(); }
function stepFrames(n) { seek(t + n / project.fps); }
function jumpScene(dir) {
  const idx = timeline.findIndex((s) => t >= s.start && t < s.end);
  const next = clamp((idx < 0 ? 0 : idx) + dir, 0, timeline.length - 1);
  seek(timeline[next].start);
}

scrub.addEventListener('input', () => seek(+scrub.value));
document.addEventListener('keydown', (e) => {
  const k = e.key;
  if (k === ' ') { e.preventDefault(); playing = !playing; render(); }
  else if (k === 'ArrowRight') seek(t + (e.shiftKey ? 5 : 1));
  else if (k === 'ArrowLeft') seek(t - (e.shiftKey ? 5 : 1));
  else if (k === ',' || k === '.') stepFrames(k === ',' ? -1 : 1);
  else if (k === '[' || k === ']') jumpScene(k === '[' ? -1 : 1);
  else if (k === 'l') loopScene = !loopScene;
  else if (k === 'h') document.body.classList.toggle('hide');
});

function tick() {
  if (playing) {
    const cur = timeline.find((s) => t >= s.start && t < s.end) ?? timeline[timeline.length - 1];
    let next = t + 1 / project.fps;
    if (loopScene && next >= cur.end) next = cur.start;
    if (next > project.duration) { next = 0; }
    t = next;
  }
  render();
  requestAnimationFrame(tick);
}
render();
requestAnimationFrame(tick);
