import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderPixels, makeCanvas } from '../src/render.mjs';
import { makeTimeline, cut, wordProgress, beatAt } from '../src/timeline.mjs';
import { mulberry32, colour, hashPixels } from '../src/util.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const project = JSON.parse(readFileSync(path.join(ROOT, 'project.json'), 'utf8'));
const px = (t, opts) => renderPixels(project, t, opts);

test('cùng (project, t) -> cùng hash, dù render lại nhiều lần', () => {
  const a = px(2.5), b = px(2.5), c = px(2.5);
  assert.equal(a.hash, b.hash);
  assert.equal(b.hash, c.hash);
  assert.equal(Buffer.compare(Buffer.from(a.data), Buffer.from(b.data)), 0);
});

test('hai thời điểm khác nhau cho hai khung hình khác nhau', () => {
  const hashes = [0, 2.5, 5.5, 9, 11.5].map((t) => px(t).hash);
  assert.equal(new Set(hashes).size, hashes.length);
});

test('golden hash: phát hiện mọi thay đổi vô tình của renderer', () => {
  // Nếu bạn đổi drawFrame có chủ đích, cập nhật số này kèm lý do trong commit.
  assert.equal(px(2.5).hash, '28adf0c8');
  assert.equal(px(9).hash, '17482dca');
});

test('code pixel không dùng random/time thật', () => {
  const files = ['src/drawFrame.mjs', 'src/util.mjs', 'src/timeline.mjs'];
  const banned = [/Math\.random/, /Date\.now/, /performance\.now/, /\bdocument\b/, /\bwindow\b/];
  for (const f of files) {
    const src = readFileSync(path.join(ROOT, f), 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/\/\/.*$/gm, '');
    for (const re of banned) assert.equal(re.test(src), false, `${f} chứa ${re}`);
  }
});

test('PRNG seeded cho cùng chuỗi số', () => {
  const a = mulberry32(20261028), b = mulberry32(20261028), c = mulberry32(20261029);
  const sa = [a(), a(), a(), a()], sb = [b(), b(), b(), b()], sc = [c(), c(), c(), c()];
  assert.deepEqual(sa, sb);
  assert.notDeepEqual(sa, sc);
});

test('timeline cắt theo nội dung lyric rồi snap vào beat grid', () => {
  const tl = makeTimeline(project);
  assert.deepEqual(tl.map((s) => s.id), ['open', 'type', 'bars', 'outro']);
  assert.equal(cut(project, 'ONE'), 4);       // word 4.0 -> beat 8 -> 4.0
  assert.equal(cut(project, 'PREVIEW'), 5.5); // word 5.8 -> beat 11 -> 5.5
  assert.equal(cut(project, 'SAME'), 8.5);    // word 8.8 -> beat 17 -> 8.5
  assert.equal(tl[0].end, tl[1].start);
  assert.equal(tl[tl.length - 1].end, project.duration);
  for (const s of tl) assert.ok(s.end > s.start, `scene ${s.id} có cửa sổ âm`);
  assert.throws(() => cut(project, 'KHONG-CO-TU-NAY'), /no word matching/);
});

test('đổi BPM thì mọi điểm cắt dời theo, không sửa code', () => {
  const faster = { ...project, bpm: 240 };
  assert.equal(cut(faster, 'PREVIEW'), 5.75); // beat 23 * 0.25
});

test('wordProgress nằm trong [0,1] và không chạy trước giọng hát', () => {
  const w = project.words[6]; // PREVIEW 5.8 -> 7.0
  assert.equal(wordProgress(w, 5.7), 0);
  assert.ok(wordProgress(w, 6.4) > 0.49 && wordProgress(w, 6.4) < 0.51);
  assert.equal(wordProgress(w, 7.1), 1);
  assert.equal(beatAt(project, 5.5), 11);
});

test('scale=2 cho đúng ảnh scale=1 (logical vs physical tách biệt)', () => {
  for (const t of [0, 2.5, 5.5, 9]) {
    const a = px(t, { scale: 1 }).data;
    const b = px(t, { scale: 2 }).data;
    let bad = 0;
    for (let y = 0; y < project.height; y++) {
      for (let x = 0; x < project.width; x++) {
        const i = (y * project.width + x) * 4;
        const j = ((2 * y) * (project.width * 2) + (2 * x)) * 4;
        if (a[i] !== b[j] || a[i + 1] !== b[j + 1] || a[i + 2] !== b[j + 2]) bad++;
      }
    }
    assert.equal(bad, 0, `t=${t}: ${bad} pixel lệch`);
  }
});

test('motion blur nhiều sub-frame vẫn deterministic', () => {
  assert.equal(px(2.5, { samples: 4 }).hash, '7604fedf');
  assert.equal(px(2.5, { samples: 4 }).hash, px(2.5, { samples: 4 }).hash);
});

test('màu được trộn sẵn (không dùng alpha) nên giống nhau giữa các backend', () => {
  assert.equal(colour('#FF4D12', '#0A0A0B', 1), '#ff4d12');
  assert.equal(colour('#FF4D12', '#0A0A0B', 0), '#0a0a0b');
  const canvas = makeCanvas(project, 1);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = colour('#FF4D12', '#0A0A0B', 1);
  ctx.fillRect(0, 0, 2, 2);
  assert.equal(hashPixels(ctx.getImageData(0, 0, 2, 2).data).length, 8);
});
