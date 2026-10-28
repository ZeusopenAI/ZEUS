// THE SHARED ENGINE. This exact file runs in Chrome (preview) and in Node
// (export via @napi-rs/canvas). It only uses ctx.fillRect + ctx.fillStyle, so
// the pixels are identical in both. No DOM, no Node APIs, no wall-clock time.
//
// Contract: drawFrame(ctx, project, t) is a pure function of (project, t).
// Everything random is seeded from project.seed + frameIdx(t).

import {
  surface, colour, rand, frameIdx, clamp, lerp, ease, smoothstep, textWidth,
} from './util.mjs';
import { makeTimeline, sceneAt, beatAt, wordProgress } from './timeline.mjs';

export function frameInfo(project, t) {
  const timeline = makeTimeline(project);
  const scene = sceneAt(timeline, t);
  const beat = beatAt(project, t);
  return {
    timeline,
    scene,
    beat,
    beatPhase: beat - Math.floor(beat),
    barPhase: beat / 4 - Math.floor(beat / 4),
    local: clamp((t - scene.start) / Math.max(0.001, scene.end - scene.start)),
  };
}

function spark(s, project, t, fi, intensity = 1) {
  const { width: W, height: H, seed, palette: P } = project;
  const at = (tt) => [
    W * 0.5 + W * 0.34 * Math.sin(tt * 1.7 + 0.3),
    H * 0.64 + H * 0.22 * Math.cos(tt * 2.3),
  ];
  // Trail: samples of the *same* parametric path at earlier times (still f(t)).
  for (let k = 16; k >= 1; k--) {
    const [x, y] = at(t - k * 0.014);
    const c = colour(P.signal, P.ink, (1 - k / 17) * 0.55 * intensity);
    s.rect(x, y, 3 - (k > 10 ? 1 : 0), 3 - (k > 10 ? 1 : 0), c);
  }
  const [x, y] = at(t);
  s.rect(x - 2, y - 2, 5, 5, colour(P.ember, P.ink, intensity));
  // Sputtering sparks: seeded by frameIdx so they don't shimmer between sub-frames.
  for (let i = 0; i < 9; i++) {
    const a = rand(seed, fi, i, 11) * Math.PI * 2;
    const d = 4 + rand(seed, fi, i, 12) * 16 * intensity;
    s.rect(x + Math.cos(a) * d, y + Math.sin(a) * d, 1, 1,
      colour(P.ember, P.ink, 0.35 * rand(seed, fi, i, 13) * intensity));
  }
}

function motif(s, project, info, t, fi) {
  const { width: W, height: H, seed, palette: P } = project;
  const { scene, beatPhase, barPhase, local } = info;
  const C = (hex, k) => colour(hex, P.ink, k);

  if (scene.kind === 'grid') {
    for (let i = 0; i < 3; i++) {
      const r = 18 + ((beatPhase + i / 3) % 1) * (W * 0.36);
      s.ring(W / 2, H / 2, r, 1, C(P.signal, 0.16 + 0.12 * (1 - i / 3)));
    }
    const step = 24;
    for (let i = 0; i < 12; i++) {
      const x = W * 0.16 + i * step;
      const h = 6 + 22 * Math.abs(Math.sin(t * 1.4 + i * 0.55));
      s.rect(x, H * 0.82 - h, 8, h, C(P.graphite, 0.5));
    }
  } else if (scene.kind === 'karaoke') {
    const baseY = H * 0.78;
    s.rect(W * 0.12, baseY, W * 0.76, 1, C(P.graphite, 0.6));
    project.words.forEach((w, i) => {
      const x = W * 0.12 + (i / project.words.length) * W * 0.76;
      const p = wordProgress(w, t);
      s.rect(x, baseY - 6, 6, 12, p > 0 ? C(P.signal, 0.3 + 0.7 * p) : C(P.graphite, 0.4));
    });
    s.line(W * 0.12, baseY - 10, W * 0.88, baseY - 10, 1, C(P.bone, 0.08));
  } else if (scene.kind === 'bars') {
    const n = 28, bw = W * 0.7 / n;
    for (let i = 0; i < n; i++) {
      const wobble = 0.4 + 0.6 * Math.abs(Math.sin(t * 3 + i * 0.42));
      const h = 8 + 64 * wobble * (0.55 + 0.45 * rand(seed, fi, i, 21));
      const x = W * 0.15 + i * bw;
      s.rect(x, H * 0.82 - h, bw - 2, h, C(i % 7 === 0 ? P.ember : P.signal, 0.28 + 0.5 * smoothstep(0, 70, h)));
    }
    s.rect(W * 0.15, H * 0.82, W * 0.7, 1, C(P.bone, 0.35));
  } else if (scene.kind === 'spark') {
    const k = ease.outExpo(clamp(local));
    for (let i = 0; i < 5; i++) {
      s.ring(W / 2, H * 0.58, 12 + i * 18 + k * 26, 1, C(P.signal, 0.10 + 0.10 * i));
    }
    const txt = 'SHIP';
    const sz = 7;
    s.text(txt, (W - textWidth(txt, sz)) / 2, H * 0.53, sz, C(P.bone, 0.9));
  }

  // Beat marker: a hard snap on every downbeat, not a floaty animation.
  const snap = 1 - smoothstep(0, 0.14, barPhase);
  if (snap > 0.01) s.rect(0, 0, W, 2, C(P.signal, 0.25 + 0.5 * snap));
}

function karaoke(s, project, t) {
  const { width: W, height: H, palette: P } = project;
  const C = (hex, k) => colour(hex, P.ink, k);
  let active = null;
  for (const w of project.words) if (t >= w.start && t <= w.end) active = w;
  if (!active) {
    const next = project.words.find((w) => w.start > t);
    if (next) {
      const txt = next.w;
      const sz = 5;
      s.text(txt, (W - textWidth(txt, sz)) / 2, H * 0.38, sz, C(P.graphite, 0.35));
    }
    return;
  }
  const txt = active.w;
  const sz = 6;
  const p = wordProgress(active, t);
  const lit = Math.round(txt.length * p);
  const x0 = (W - textWidth(txt, sz)) / 2;
  const y = H * 0.35;
  s.text(txt, x0, y, sz, C(P.graphite, 0.42));           // unsung
  s.text(txt.slice(0, lit), x0, y, sz, C(P.signal, 1));  // sung portion
  const hx = x0 + lit * (3 + 1) * sz;
  s.rect(hx, y - 3, 2, 5 * sz + 6, C(P.ember, 0.9));    // playhead
}

function hud(s, project, info, t, fi) {
  const { width: W, height: H, palette: P } = project;
  const C = (hex, k) => colour(hex, P.ink, k);
  s.rect(0, 0, W, 1, C(P.graphite, 0.5));
  s.rect(0, H - 20, W, 1, C(P.graphite, 0.5));
  s.text('ZEUS / DETERMINISTIC RENDER', 8, 7, 1, C(P.bone, 0.72));
  const seedTxt = `SEED ${project.seed}`;
  s.text(seedTxt, W - 8 - textWidth(seedTxt, 1), 7, 1, C(P.graphite, 0.8));

  const pShip = (0.02 + 0.97 * ease.outCubic(clamp(t / project.duration))).toFixed(2);
  const line = `T=${t.toFixed(2)}  BEAT=${info.beat.toFixed(1)}  SCENE=${info.scene.id.toUpperCase()}  P(SHIP)=${pShip}`;
  s.text(line, 8, H - 15, 1, C(P.ash ?? P.graphite, 0.85));
  const fps = `F=${fi}  ${project.fps}FPS`;
  s.text(fps, W - 8 - textWidth(fps, 1), H - 15, 1, C(P.graphite, 0.8));

  // progress / scrub bar
  const k = clamp(t / project.duration);
  s.rect(0, H - 2, W * k, 2, C(P.signal, 0.85));
}

/** Draw one frame. `opts.scale` is an INTEGER physical scale (1 = 480x270, 2 = 960x540). */
export function drawFrame(ctx, project, t, opts = {}) {
  const scale = opts.scale ?? 1;
  const s = surface(ctx, project.width, project.height, scale);
  const P = project.palette;
  const info = frameInfo(project, t);
  const fi = frameIdx(t, project.fps);

  s.clear(P.ink);

  // Structural grid — same in every plate, part of the shared visual language.
  for (let x = 0; x <= project.width; x += 40) s.rect(x, 0, 1, project.height, colour(P.graphite, P.ink, 0.16));
  for (let y = 0; y <= project.height; y += 40) s.rect(0, y, project.width, 1, colour(P.graphite, P.ink, 0.16));

  // Deterministic grain, keyed to frameIdx (not continuous t) so sub-frame
  // averaging does not turn it into mush and the adaptive sampler stays calm.
  for (let i = 0; i < 24; i++) {
    const x = Math.floor(rand(project.seed, fi, i, 1) * project.width);
    const y = Math.floor(rand(project.seed, fi, i, 2) * project.height);
    s.rect(x, y, 1, 1, colour(P.bone, P.ink, 0.03 + 0.05 * rand(project.seed, fi, i, 3)));
  }

  motif(s, project, info, t, fi);
  spark(s, project, t, fi, info.scene.kind === 'spark' ? 1 : 0.7);
  karaoke(s, project, t);
  hud(s, project, info, t, fi);
  return info;
}
