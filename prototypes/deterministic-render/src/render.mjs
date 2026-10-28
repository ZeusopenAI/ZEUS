// Node-side pixel renderer. Uses @napi-rs/canvas (Skia) as a headless Canvas2D,
// but the DRAWING CODE is the very same src/drawFrame.mjs the browser preview uses.
// In production you could swap this file for "headless Chrome + WebSocket rgb24"
// (see docs/REFERENCE_PDOOM_VIDEO.md §3.4) without touching drawFrame.

import { createCanvas } from '@napi-rs/canvas';
import { drawFrame } from './drawFrame.mjs';
import { hashPixels, clamp } from './util.mjs';

export function makeCanvas(project, scale = 1) {
  return createCanvas(project.width * scale, project.height * scale);
}

/**
 * Render frame at time t. `samples > 1` averages sub-frames spread over
 * `shutter / fps` — a deliberately small nod to pdoom-video's motion blur.
 * Sub-frames are still pure f(t), so order does not matter.
 */
export function renderPixels(project, t, opts = {}) {
  const scale = opts.scale ?? 1;
  const samples = Math.max(1, Math.floor(opts.samples ?? 1));
  const shutter = opts.shutter ?? 0.2;
  const canvas = opts.canvas ?? makeCanvas(project, scale);
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  let acc = null;

  for (let i = 0; i < samples; i++) {
    const off = samples === 1 ? 0 : ((i + 0.5) / samples - 0.5) * (shutter / project.fps);
    drawFrame(ctx, project, clamp(t + off, 0, project.duration), { scale });
    const rgba = ctx.getImageData(0, 0, width, height).data;
    if (!acc) acc = new Float32Array(rgba.length);
    for (let j = 0; j < rgba.length; j++) acc[j] += rgba[j];
  }
  const out = new Uint8ClampedArray(acc.length);
  for (let j = 0; j < acc.length; j++) out[j] = Math.round(acc[j] / samples);
  return { data: out, width, height, hash: hashPixels(out), samples, scale };
}

/** RGBA -> raw rgb24 (what ffmpeg wants on stdin). */
export function toRGB24(rgba) {
  const out = Buffer.allocUnsafe((rgba.length / 4) * 3);
  for (let i = 0, j = 0; i < rgba.length; i += 4, j += 3) {
    out[j] = rgba[i];
    out[j + 1] = rgba[i + 1];
    out[j + 2] = rgba[i + 2];
  }
  return out;
}
