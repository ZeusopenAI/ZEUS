#!/usr/bin/env node
// Standalone "Second Brain" importer for Zeus / Hermes.
//
// Imports ChatGPT / Claude.ai / Gemini conversation exports into plain Markdown
// notes under `memory/imports/<source>/` directory for Hermes memory retrieval.
// This script runs standalone with Node >= 22 (node --experimental-strip-types or native).
//
// Usage:
//   node scripts/second-brain-import.mjs import chatgpt --from ~/Downloads/conversations.json
//   node scripts/second-brain-import.mjs import claude-ai --from ~/Downloads/claude-export/
//   node scripts/second-brain-import.mjs import gemini --from ~/Downloads/Takeout/Gemini/
//   node scripts/second-brain-import.mjs list --out ~/.hermes/memory/imports
//
// The `--out` directory defaults to ~/.hermes/memory/imports so notes land where
// Hermes memory indexes can find them.

import os from "node:os";
import path from "node:path";
import {
  importSecondBrainSource,
  ingestSecondBrainInbox,
  listSecondBrainSources,
} from "./second-brain/import-conversations.ts";
import {
  SECOND_BRAIN_SOURCE_IDS,
  SECOND_BRAIN_SOURCE_LABELS,
} from "./second-brain/types.ts";

const DEFAULT_IMPORTS_ROOT =
  process.env.SECOND_BRAIN_IMPORTS_DIR ||
  path.join(os.homedir(), ".hermes", "memory", "imports");

function parseArgs(argv) {
  const args = argv.slice(2);
  const command = args[0];
  const positional = [];
  const flags = new Map();
  for (let index = 1; index < args.length; index += 1) {
    const token = args[index];
    if (token === undefined) {
      break;
    }
    if (token.startsWith("--")) {
      const equals = token.indexOf("=");
      if (equals !== -1) {
        flags.set(token.slice(2, equals), token.slice(equals + 1));
      } else {
        const next = args[index + 1];
        if (next !== undefined && !next.startsWith("--")) {
          flags.set(token.slice(2), next);
          index += 1;
        } else {
          flags.set(token.slice(2), true);
        }
      }
    } else {
      positional.push(token);
    }
  }
  return { command, positional, flags };
}

function fail(message) {
  process.stderr.write(`second-brain: ${message}\n`);
  process.exitCode = 1;
}

function printUsage() {
  process.stdout.write(
    [
      "Usage:",
      "  node scripts/second-brain-import.mjs import <source> --from <path> [--out <dir>] [--overwrite] [--dry-run] [--max-files <n>]",
      "  node scripts/second-brain-import.mjs ingest --from <inbox-dir> [--out <dir>] [--overwrite] [--dry-run]",
      "  node scripts/second-brain-import.mjs list [--out <dir>]",
      "",
      `Sources: ${SECOND_BRAIN_SOURCE_IDS.join(", ")}`,
      `Default --out: ${DEFAULT_IMPORTS_ROOT}`,
      "",
      "Inbox layout for `ingest` (file names or folder names are auto-detected):",
      "  <inbox>/chatgpt.json | chatgpt/    (ChatGPT export)",
      "  <inbox>/claude-ai.json | claude/   (Claude.ai export)",
      "  <inbox>/gemini.json | gemini/      (Gemini Takeout, JSON hoặc Chat-*.html)",
      "",
    ].join("\n"),
  );
}

async function runImport(positional, flags) {
  const source = positional[0];
  const from = typeof flags.get("from") === "string" ? flags.get("from") : undefined;
  if (!SECOND_BRAIN_SOURCE_IDS.includes(source)) {
    fail(`unknown source "${source}". Expected one of: ${SECOND_BRAIN_SOURCE_IDS.join(", ")}`);
    return;
  }
  if (!from) {
    fail("--from <path> is required.");
    return;
  }
  const importsRoot = path.resolve(
    typeof flags.get("out") === "string" ? flags.get("out") : DEFAULT_IMPORTS_ROOT,
  );
  const maxFilesRaw = flags.get("max-files");
  const maxFiles =
    typeof maxFilesRaw === "string" && maxFilesRaw.length > 0
      ? Number.parseInt(maxFilesRaw, 10)
      : undefined;
  if (maxFiles !== undefined && (!Number.isFinite(maxFiles) || maxFiles < 1)) {
    fail("--max-files must be a positive integer.");
    return;
  }
  const dryRun = flags.has("dry-run");
  const report = await importSecondBrainSource({
    source,
    from: path.resolve(from),
    importsRoot,
    overwrite: flags.has("overwrite"),
    dryRun,
    maxFiles,
  });
  const label = SECOND_BRAIN_SOURCE_LABELS[report.source];
  process.stdout.write(`\n${dryRun ? "Dry run" : "Import"} complete for ${label}:\n`);
  process.stdout.write(`  created : ${report.created}\n  skipped : ${report.skipped}\n  errors  : ${report.errors}\n`);
  if (report.redactions > 0) {
    process.stdout.write(`  redacted secrets: ${report.redactions}\n`);
  }
  for (const file of report.files) {
    if (file.status === "created") {
      process.stdout.write(`  + ${file.relativePath} (${file.messageCount} messages)\n`);
    } else if (file.status === "skipped") {
      process.stdout.write(`  = ${file.relativePath} (${file.reason ?? "skipped"})\n`);
    } else if (file.status === "error") {
      process.stdout.write(`  ! ${file.relativePath || "(warning)"}: ${file.reason ?? "error"}\n`);
    }
  }
  process.stdout.write("\n");
}

async function runList(flags) {
  const importsRoot = path.resolve(
    typeof flags.get("out") === "string" ? flags.get("out") : DEFAULT_IMPORTS_ROOT,
  );
  const sources = await listSecondBrainSources(importsRoot);
  process.stdout.write(`\nSecond Brain imports at ${importsRoot}\n\n`);
  if (sources.length === 0) {
    process.stdout.write("No second-brain imports found yet.\n\n");
    return;
  }
  for (const entry of sources) {
    const label = SECOND_BRAIN_SOURCE_LABELS[entry.source];
    process.stdout.write(`  ${label.padEnd(10)} ${String(entry.files).padStart(6)} files  ${entry.bytes} bytes\n`);
  }
  process.stdout.write("\n");
}

async function runIngest(flags) {
  const inboxDir = typeof flags.get("from") === "string" ? flags.get("from") : undefined;
  if (!inboxDir) {
    fail("--from <inbox-dir> is required.");
    return;
  }
  const importsRoot = path.resolve(
    typeof flags.get("out") === "string" ? flags.get("out") : DEFAULT_IMPORTS_ROOT,
  );
  const dryRun = flags.has("dry-run");
  const report = await ingestSecondBrainInbox({
    inboxDir: path.resolve(inboxDir),
    importsRoot,
    overwrite: flags.has("overwrite"),
    dryRun,
  });

  if (report.unrecognized.length > 0) {
    process.stdout.write(
      `\nSkipped (unrecognized; name them chatgpt/claude-ai/gemini or use the import command):\n`,
    );
    for (const name of report.unrecognized) {
      process.stdout.write(`  ? ${name}\n`);
    }
  }
  if (report.missingSources.length > 0) {
    process.stdout.write(
      `\nNot found in inbox: ${report.missingSources.join(", ")}\n`,
    );
  }
  for (const sourceReport of report.reports) {
    const label = SECOND_BRAIN_SOURCE_LABELS[sourceReport.source];
    process.stdout.write(
      `\n${dryRun ? "Dry run" : "Import"} ${label}: +${sourceReport.created} =${sourceReport.skipped} !${sourceReport.errors}`,
    );
    if (sourceReport.redactions > 0) {
      process.stdout.write(` (redacted secrets: ${sourceReport.redactions})`);
    }
    process.stdout.write("\n");
  }
  process.stdout.write("\n");
}

async function main() {
  const { command, positional, flags } = parseArgs(process.argv);
  // `node scripts/second-brain-import.mjs --help` / `-h` / `help` đều in usage
  // (trước đây `--help` bị coi là command và báo lỗi "unknown command").
  if (
    flags.has("help") ||
    flags.has("h") ||
    command === undefined ||
    command === "help" ||
    command === "--help" ||
    command === "-h"
  ) {
    printUsage();
    return;
  }
  if (command === "import") {
    await runImport(positional, flags);
    return;
  }
  if (command === "ingest") {
    await runIngest(flags);
    return;
  }
  if (command === "list") {
    await runList(flags);
    return;
  }
  printUsage();
  fail(`unknown command "${command}".`);
}

await main();
