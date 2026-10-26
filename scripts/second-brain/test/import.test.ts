import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { importSecondBrainSource, listSecondBrainSources } from "../import-conversations.ts";

async function makeTempDir(): Promise<string> {
  return await fs.mkdtemp(path.join(os.tmpdir(), "second-brain-"));
}

// Fixture giả lập key: ghép tại runtime để secret scanner của CI không báo nhầm,
// nhưng vẫn đủ dài (>= 16 ký tự sau tiền tố) để khớp pattern redaction
// /\bsk-[A-Za-z0-9_-]{16,}\b/ trong normalize/shared.ts.
const FAKE_OPENAI_KEY = ["sk", "abcdefghijklmnopqrstuvwx"].join("-");

const chatGptExport = [
  {
    title: "Secret handling",
    conversation_id: "conv-secret",
    create_time: 1710000000,
    current_node: "n2",
    mapping: {
      n1: {
        parent: null,
        children: ["n2"],
        message: { id: "m1", author: { role: "user" }, create_time: 1710000000, content: { parts: [`My token is ${FAKE_OPENAI_KEY} please keep it`] } },
      },
      n2: {
        parent: "n1",
        children: [],
        message: { id: "m2", author: { role: "assistant" }, create_time: 1710000030, content: { parts: ["I'll remember that."] } },
      },
    },
  },
];

test("import: writes markdown notes and redacts secrets", async () => {
  const dir = await makeTempDir();
  const importsRoot = path.join(dir, "memory", "imports");
  const exportFile = path.join(dir, "conversations.json");
  await fs.writeFile(exportFile, JSON.stringify(chatGptExport), "utf8");

  const report = await importSecondBrainSource({
    source: "chatgpt",
    from: exportFile,
    importsRoot,
  });

  assert.equal(report.created, 1);
  assert.equal(report.skipped, 0);
  assert.equal(report.errors, 0);
  assert.equal(report.redactions, 1);

  const note = report.files.find((file) => file.status === "created");
  assert.ok(note);
  const contents = await fs.readFile(path.join(importsRoot, note!.relativePath), "utf8");
  assert.match(contents, /# Secret handling/);
  assert.match(contents, /## You/);
  assert.match(contents, /## ChatGPT/);
  assert.ok(!contents.includes(FAKE_OPENAI_KEY));
  assert.match(contents, /\[redacted\]/);

  await fs.rm(dir, { recursive: true, force: true });
});

test("import: is idempotent and respects --overwrite", async () => {
  const dir = await makeTempDir();
  const importsRoot = path.join(dir, "memory", "imports");
  const exportFile = path.join(dir, "conversations.json");
  await fs.writeFile(exportFile, JSON.stringify(chatGptExport), "utf8");

  const first = await importSecondBrainSource({ source: "chatgpt", from: exportFile, importsRoot });
  assert.equal(first.created, 1);

  const second = await importSecondBrainSource({ source: "chatgpt", from: exportFile, importsRoot });
  assert.equal(second.created, 0);
  assert.equal(second.skipped, 1);

  const overwritten = await importSecondBrainSource({
    source: "chatgpt",
    from: exportFile,
    importsRoot,
    overwrite: true,
  });
  assert.equal(overwritten.created, 1);
  assert.equal(overwritten.skipped, 0);

  await fs.rm(dir, { recursive: true, force: true });
});

test("import: dry-run reports without writing", async () => {
  const dir = await makeTempDir();
  const importsRoot = path.join(dir, "memory", "imports");
  const exportFile = path.join(dir, "conversations.json");
  await fs.writeFile(exportFile, JSON.stringify(chatGptExport), "utf8");

  const report = await importSecondBrainSource({
    source: "chatgpt",
    from: exportFile,
    importsRoot,
    dryRun: true,
  });
  assert.equal(report.created, 1);
  const files = await fs.readdir(path.join(importsRoot, "chatgpt")).catch(() => []);
  assert.equal(files.length, 0);

  await fs.rm(dir, { recursive: true, force: true });
});

test("import: directory input picks conversations.json", async () => {
  const dir = await makeTempDir();
  const importsRoot = path.join(dir, "memory", "imports");
  const exportDir = path.join(dir, "export");
  await fs.mkdir(exportDir, { recursive: true });
  await fs.writeFile(path.join(exportDir, "conversations.json"), JSON.stringify(chatGptExport), "utf8");

  const report = await importSecondBrainSource({ source: "chatgpt", from: exportDir, importsRoot });
  assert.equal(report.created, 1);

  await fs.rm(dir, { recursive: true, force: true });
});

test("list: reports imported sources", async () => {
  const dir = await makeTempDir();
  const importsRoot = path.join(dir, "memory", "imports");
  const exportFile = path.join(dir, "conversations.json");
  await fs.writeFile(exportFile, JSON.stringify(chatGptExport), "utf8");
  await importSecondBrainSource({ source: "chatgpt", from: exportFile, importsRoot });

  const sources = await listSecondBrainSources(importsRoot);
  assert.deepEqual(sources, [{ source: "chatgpt", files: 1, bytes: sources[0]?.bytes ?? 0 }]);

  await fs.rm(dir, { recursive: true, force: true });
});
