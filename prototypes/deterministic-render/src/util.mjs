// Pure, dependency-free helpers shared by the browser preview and the Node exporter.
// RULE (from docs/REFERENCE_PDOOM_VIDEO.md): everything that affects pixels is a
// function of (project, t). No Math.random, no Date.now, no performance.now here.

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const mix = (a, b, k) => lerp(a, b, clamp(k));

/** Deterministic 32-bit PRNG (mulberry32). Same seed -> same sequence everywhere. */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = a;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

/** Stable integer hash of any number of integers (FNV-1a style, no floats). */
export function hash32(...nums) {
  let h = 0x811c9dc5;
  for (const n of nums) {
    let v = (Number.isFinite(n) ? Math.trunc(n) : 0) | 0;
    for (let i = 0; i < 4; i++) {
      h ^= (v >>> (i * 8)) & 0xff;
      h = Math.imul(h, 0x01000193) >>> 0;
    }
  }
  return h >>> 0;
}

/** 0..1 pseudo-random from a set of integer coordinates. */
export const rand = (...nums) => hash32(...nums) / 4294967296;

/** Frame index constant across one frame's shutter — use this, not Math.floor(t*fps), for per-frame jitter. */
export const frameIdx = (t, fps) => Math.floor(t * fps + 1e-9);

export const ease = {
  outExpo: (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
  inOutCubic: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  outCubic: (x) => 1 - Math.pow(1 - x, 3),
};

export const smoothstep = (a, b, x) => {
  const k = clamp((x - a) / (b - a));
  return k * k * (3 - 2 * k);
};

// ---------------------------------------------------------------- colour (opaque only)
// We never use rgba()/globalAlpha: blending differs slightly between Skia and
// browser Canvas. Pre-mixing two solid colours keeps preview and export pixel-identical.

function rgb(hex) {
  const s = hex.replace('#', '');
  const n = parseInt(s.length === 3 ? s.split('').map((c) => c + c).join('') : s, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function colour(hex, against = '#000000', k = 1) {
  const [r, g, b] = rgb(hex);
  const [r2, g2, b2] = rgb(against);
  const h = (v) => Math.round(v).toString(16).padStart(2, '0');
  // k = 1 -> the requested colour, k = 0 -> the background it is mixed against.
  return `#${h(mix(r2, r, k))}${h(mix(g2, g, k))}${h(mix(b2, b, k))}`;
}

// ---------------------------------------------------------------- 3x5 bitmap font
// A tiny font drawn with fillRect only. No system fonts -> identical pixels on
// headless Skia and in Chrome, which is the whole point of this prototype.
const GLYPHS = {
  ' ': '000/000/000/000/000',
  A: '010/101/111/101/101', B: '110/101/110/101/110', C: '011/100/100/100/011',
  D: '110/101/101/101/110', E: '111/100/110/100/111', F: '111/100/110/100/100',
  G: '011/100/101/101/011', H: '101/101/111/101/101', I: '111/010/010/010/111',
  J: '001/001/001/101/010', K: '101/101/110/101/101', L: '100/100/100/100/111',
  M: '101/111/111/101/101', N: '101/111/111/111/101', O: '010/101/101/101/010',
  P: '110/101/110/100/100', Q: '010/101/101/111/011', R: '110/101/110/101/101',
  S: '011/100/010/001/110', T: '111/010/010/010/010', U: '101/101/101/101/111',
  V: '101/101/101/101/010', W: '101/101/111/111/101', X: '101/101/010/101/101',
  Y: '101/101/010/010/010', Z: '111/001/010/100/111',
  '0': '111/101/101/101/111', '1': '010/110/010/010/111', '2': '111/001/111/100/111',
  '3': '111/001/111/001/111', '4': '101/101/111/001/001', '5': '111/100/111/001/111',
  '6': '111/100/111/101/111', '7': '111/001/001/010/010', '8': '111/101/111/101/111',
  '9': '111/101/111/001/111',
  '.': '000/000/000/000/010', ':': '000/010/000/010/000', '-': '000/000/111/000/000',
  '/': '001/001/010/100/100', '(': '001/010/010/010/001', ')': '100/010/010/010/100',
  '?': '110/001/010/000/010', '%': '101/001/010/100/101', '+': '000/010/111/010/000',
  '=': '000/111/000/111/000', ',': '000/000/000/010/100', '!': '010/010/010/000/010',
  '#': '101/111/101/111/101', '*': '000/101/010/101/000', '<': '001/010/100/010/001',
  '>': '100/010/001/010/100', "'": '010/010/000/000/000', '[': '011/010/010/010/011',
  ']': '110/010/010/010/110', '_': '000/000/000/000/111', '|': '010/010/010/010/010',
};

export const GLYPH_W = 3;
export const GLYPH_H = 5;

/** Pixel width of a string at size `s` (1 bitmap pixel = s logical px, 1px gap). */
export const textWidth = (str, s = 1) => str.length * (GLYPH_W + 1) * s - s;

/** Draws text with a Canvas2D-like context's fillRect/fillStyle only. */
export function drawText(ctx, str, x, y, s, fillStyle, scale = 1) {
  const put = (px, py, pw, ph, c) => {
    const X = Math.round(px), Y = Math.round(py);
    const Wd = Math.max(1, Math.round(pw)), Hd = Math.max(1, Math.round(ph));
    ctx.fillStyle = c;
    ctx.fillRect(X * scale, Y * scale, Wd * scale, Hd * scale);
  };
  const chars = String(str).toUpperCase().split('');
  for (let i = 0; i < chars.length; i++) {
    const rows = (GLYPHS[chars[i]] ?? GLYPHS['?']).split('/');
    for (let r = 0; r < GLYPH_H; r++) {
      for (let c = 0; c < GLYPH_W; c++) {
        if (rows[r][c] === '1') {
          put(x + (i * (GLYPH_W + 1) + c) * s, y + r * s, s, s, fillStyle);
        }
      }
    }
  }
}

/** A Canvas2D-like surface that only uses fillRect, in LOGICAL coordinates. */
export function surface(ctx, W, H, scale = 1) {
  const rect = (x, y, w, h, c) => {
    // Quantise in LOGICAL space first, then scale. Otherwise a fractional
    // coordinate rounds differently at 1x and 2x and the two outputs diverge.
    const X = Math.round(x), Y = Math.round(y);
    const Wd = Math.max(1, Math.round(w)), Hd = Math.max(1, Math.round(h));
    ctx.fillStyle = c;
    ctx.fillRect(X * scale, Y * scale, Wd * scale, Hd * scale);
  };
  return {
    ctx, W, H, scale,
    clear: (c) => rect(0, 0, W, H, c),
    rect,
    text: (str, x, y, s, c) => drawText(ctx, str, x, y, s, c, scale),
    textW: (str, s) => textWidth(str, s),
    /** Line made of squares — identical rasterisation on every Canvas2D backend. */
    line: (x0, y0, x1, y1, w, c) => {
      const steps = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0)));
      for (let i = 0; i <= steps; i++) {
        const k = i / steps;
        rect(lerp(x0, x1, k) - w / 2, lerp(y0, y1, k) - w / 2, w, w, c);
      }
    },
    ring: (cx, cy, r, w, c) => {
      const steps = Math.max(8, Math.ceil(r * 3));
      for (let i = 0; i < steps; i++) {
        const a = (i / steps) * Math.PI * 2;
        rect(cx + Math.cos(a) * r - w / 2, cy + Math.sin(a) * r - w / 2, w, w, c);
      }
    },
  };
}

/** FNV-1a hash over RGBA bytes — the number printed by both preview and exporter. */
export function hashPixels(rgba) {
  let h = 0x811c9dc5;
  for (let i = 0; i < rgba.length; i += 4) {
    h = Math.imul(h ^ rgba[i], 0x01000193) >>> 0;
    h = Math.imul(h ^ rgba[i + 1], 0x01000193) >>> 0;
    h = Math.imul(h ^ rgba[i + 2], 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, '0');
}
