// Timeline = semantic lyric anchors snapped to a beat grid.
// Port of the idea in mexicat/pdoom-video `app/src/timeline.ts`, kept tiny and
// data-driven: change the words/BPM in project.json and every cut moves with it.

export const norm = (s) => String(s).toUpperCase().replace(/[^A-Z0-9]/g, '');

export function beatPeriod(project) {
  return 60 / project.bpm;
}

export function beatAt(project, t) {
  return (t - (project.beatOffset ?? 0)) / beatPeriod(project);
}

export function timeOfBeat(project, i) {
  return (project.beatOffset ?? 0) + i * beatPeriod(project);
}

/** Cut on the last beat at/before the first matched word (never after the word). */
export function cut(project, query, nth = 0, tol = 0.02) {
  const q = norm(query);
  const hits = project.words.filter((w) => norm(w.w).includes(q));
  const word = hits[nth];
  if (!word) throw new Error(`timeline: no word matching "${query}" (#${nth})`);
  return timeOfBeat(project, Math.floor(beatAt(project, word.start + tol)));
}

export function makeTimeline(project) {
  const E = (id, start, end, kind, params = {}) => ({ id, start, end, kind, params });
  return project.scenes.map((s, i) => {
    const start = s.start ?? cut(project, s.query, s.nth ?? 0);
    const next = project.scenes[i + 1];
    const end = next
      ? (next.start ?? cut(project, next.query, next.nth ?? 0))
      : project.duration;
    return E(s.id, start, end, s.kind, s.params ?? {});
  });
}

export function sceneAt(timeline, t) {
  return timeline.find((s) => t >= s.start && t < s.end) ?? timeline[timeline.length - 1];
}

/** 0..1 progress of a word being "sung"; karaoke highlighting never runs ahead. */
export function wordProgress(word, t) {
  if (t <= word.start) return 0;
  if (t >= word.end) return 1;
  return (t - word.start) / (word.end - word.start);
}

export function wordsAt(project, t) {
  return project.words.filter((w) => t >= w.start - 0.4 && t <= w.end + 0.15);
}
