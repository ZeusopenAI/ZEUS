#!/usr/bin/env node
/* ══════════════════════════════════════════════════════════════════════
   site-smoke-test.mjs — Kiểm thử tự động landing page trong site/
   Mô phỏng trình duyệt bằng jsdom: bấm menu, carousel, gửi form, chat demo,
   chờ kịch bản chatbot tự chạy và bắt lỗi runtime.

   Chạy:
     npm i --no-save jsdom        # cài 1 lần (không ghi vào package.json)
     node scripts/site-smoke-test.mjs

   Thoát mã 0 = tất cả OK · khác 0 = có lỗi (dùng được trong CI).
   ══════════════════════════════════════════════════════════════════════ */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE = path.join(ROOT, "site");

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require("jsdom"));
} catch {
  console.error(
    "✗ Chưa có jsdom. Cài bằng:\n    npm i --no-save jsdom\n  rồi chạy lại:\n    node scripts/site-smoke-test.mjs"
  );
  process.exit(2);
}

const html = fs.readFileSync(path.join(SITE, "index.html"), "utf8");
const problems = [];

const vc = new VirtualConsole();
const ignore = /Could not load|fonts\.googleapis|fonts\.gstatic|Not implemented: (HTMLCanvasElement|Window's scrollTo|window\.scrollTo)/;
vc.on("jsdomError", (e) => {
  const msg = String((e && (e.stack || e.message)) || e);
  if (!ignore.test(msg)) problems.push("jsdomError: " + msg.split("\n").slice(0, 2).join(" | "));
});
vc.on("error", (...a) => {
  const msg = a.map(String).join(" ");
  if (!ignore.test(msg)) problems.push("console.error: " + msg);
});

function stubCanvas(win) {
  const noop = () => {};
  const ctx = new Proxy({}, {
    get: (t, k) => (k in t ? t[k] : noop),
    set: (t, k, v) => { t[k] = v; return true; },
  });
  win.HTMLCanvasElement.prototype.getContext = () => ctx;
}

function makeDom({ withIO }) {
  return new JSDOM(html, {
    url: "file://" + path.join(SITE, "index.html"),
    runScripts: "dangerously",
    resources: "usable",
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(win) {
      stubCanvas(win);
      win.scrollTo = () => {};
      if (withIO) {
        win.IntersectionObserver = class {
          constructor(cb) { this.cb = cb; }
          observe(el) { this.cb([{ isIntersecting: true, target: el }], this); }
          unobserve() {} disconnect() {}
        };
      } else {
        delete win.IntersectionObserver;
      }
    },
  });
}

const waitLoad = (win) => new Promise((r) => win.addEventListener("load", r, { once: true }));

/* ── Kịch bản: người dùng tương tác liên tục ── */
async function interactiveRun(label, withIO) {
  const dom = makeDom({ withIO });
  const win = dom.window, doc = win.document;
  const errors = [];
  const step = (name, fn) => { try { fn(); } catch (e) { errors.push(name + ": " + e.message); } };

  await waitLoad(win);

  step("mở/đóng menu", () => {
    const b = doc.getElementById("burger");
    b.dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
    if (!doc.getElementById("nav").classList.contains("is-open")) throw new Error("menu không mở");
    b.dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
  });

  step("nút chọn gói điền sẵn form", () => {
    doc.querySelector('[data-plan="Professional"]').dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
    if (doc.getElementById("fNeed").value.indexOf("Automation") === -1) throw new Error("không điền nhu cầu theo gói");
  });

  step("carousel: nút, dot, bàn phím", () => {
    const first = doc.querySelector(".slide.is-active");
    doc.getElementById("nextBtn").dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
    if (first === doc.querySelector(".slide.is-active")) throw new Error("next không đổi slide");
    const dots = doc.querySelectorAll("#dots button");
    if (dots.length !== 6) throw new Error("số dot = " + dots.length);
    dots[4].dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
    if (doc.querySelector(".slide.is-active").dataset.slide !== "4") throw new Error("dot không nhảy đúng");
    doc.getElementById("carouselViewport").dispatchEvent(new win.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    if (doc.querySelector(".slide.is-active").dataset.slide !== "5") throw new Error("phím → không hoạt động");
  });

  step("form chặn dữ liệu sai", () => {
    doc.getElementById("fName").value = "A";
    doc.getElementById("fPhone").value = "abc";
    doc.getElementById("leadForm").dispatchEvent(new win.Event("submit", { bubbles: true, cancelable: true }));
    if (!doc.querySelector('[data-err-for="fName"]').textContent) throw new Error("không báo lỗi tên");
    if (!doc.querySelector('[data-err-for="fPhone"]').textContent) throw new Error("không báo lỗi SĐT");
    if (doc.getElementById("leadResult")) throw new Error("vẫn hiện kết quả khi dữ liệu sai");
  });

  step("form nhận dữ liệu hợp lệ", () => {
    doc.getElementById("fName").value = "Anh Minh";
    doc.getElementById("fPhone").value = "0901 234 567";
    doc.getElementById("fNeed").value = "AI Chatbot CSKH 24/7";
    doc.getElementById("fNote").value = "800 SKU";
    doc.getElementById("leadForm").dispatchEvent(new win.Event("submit", { bubbles: true, cancelable: true }));
    if (!doc.getElementById("leadResult")) throw new Error("không hiện khối kết quả");
    if (!doc.getElementById("copyLead")) throw new Error("thiếu nút copy");
  });

  // Người dùng gõ ngay khi kịch bản demo đang tự chạy → phải được phản hồi
  step("gõ tin nhắn giữa kịch bản", () => {
    doc.getElementById("chatInput").value = "Có giao hàng quận 7 không shop?";
    doc.getElementById("chatForm").dispatchEvent(new win.Event("submit", { bubbles: true, cancelable: true }));
  });

  // Bấm gợi ý liền sau đó (bot còn đang trả lời) → phải vào hàng đợi, không bị mất
  step("bấm gợi ý liên tiếp", () => {
    doc.querySelector("#chatQuick button[data-q]").dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
  });

  step("đóng thanh thông báo", () => {
    doc.getElementById("announceClose").dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
    if (!doc.getElementById("announce").classList.contains("is-hidden")) throw new Error("không ẩn được");
  });

  step("cuộn trang", () => {
    win.scrollTo(0, 1200);
    win.dispatchEvent(new win.Event("scroll"));
  });

  await new Promise((r) => setTimeout(r, 2200)); // chờ 2 câu trả lời hoàn tất

  const s1 = parseInt(doc.querySelector('[data-cd="s"]').textContent, 10);
  await new Promise((r) => setTimeout(r, 2500));
  const s2 = parseInt(doc.querySelector('[data-cd="s"]').textContent, 10);

  const typed = [...doc.querySelectorAll("#chatBody .msg--out .msg__bubble")].some((b) =>
    b.textContent.includes("giao hàng quận 7")
  );
  const botMsgs = doc.querySelectorAll("#chatBody .msg--in").length;
  const outMsgs = doc.querySelectorAll("#chatBody .msg--out").length;

  dom.window.close();

  if (!typed) errors.push("tin nhắn tự gõ không được render");
  if (botMsgs < 2) errors.push("bot phải trả lời cả 2 lượt tương tác, hiện có: " + botMsgs);
  if (outMsgs < 2) errors.push("tin của khách không đủ: " + outMsgs);
  if (!((s1 - s2 + 60) % 60 <= 4)) errors.push(`countdown không chạy: ${s1} → ${s2}`);

  console.log(`\n── ${label} ──`);
  console.log("  lỗi:", errors.length ? errors : "không có");
  console.log(`  chat: ${botMsgs} bot · ${outMsgs} khách · render tin tự gõ: ${typed}`);
  console.log(`  countdown: ${s1}s → ${s2}s`);
  errors.forEach((e) => problems.push(`[${label}] ` + e));
  return errors.length;
}

/* ── Kịch bản: không tương tác, kịch bản chatbot phải chạy hết ── */
async function passiveRun() {
  const dom = makeDom({ withIO: true });
  const win = dom.window, doc = win.document;
  await waitLoad(win);
  await new Promise((r) => setTimeout(r, 26000));

  const bot = doc.querySelectorAll("#chatBody .msg--in").length;
  const user = doc.querySelectorAll("#chatBody .msg--out").length;
  const products = doc.querySelectorAll("#chatBody .prod").length;
  const typingLeft = doc.querySelectorAll("#chatBody .typing").length;

  dom.window.close();

  const errors = [];
  if (bot !== 5) errors.push("số tin bot = " + bot + " (mong đợi 5)");
  if (user !== 4) errors.push("số tin khách = " + user + " (mong đợi 4)");
  if (products < 5) errors.push("product card = " + products + " (mong đợi ≥5)");
  if (typingLeft !== 0) errors.push("còn " + typingLeft + " con trỏ 'đang soạn' treo");

  console.log("\n── kịch bản tự chạy (không tương tác) ──");
  console.log(`  chat: ${bot} bot · ${user} khách · ${products} product card · typing treo: ${typingLeft}`);
  console.log("  lỗi:", errors.length ? errors : "không có");
  errors.forEach((e) => problems.push("[passive] " + e));
  return errors.length;
}

console.log("Kiểm thử landing page trong site/ …");
await interactiveRun("có IntersectionObserver + tương tác", true);
await interactiveRun("không có IntersectionObserver (fallback)", false);
await passiveRun();

console.log("\n================ KẾT LUẬN ================");
if (problems.length) {
  console.log("✗ Còn vấn đề:");
  problems.forEach((p) => console.log("   - " + p));
  process.exit(1);
}
console.log("✓ Tất cả luồng chạy không lỗi: nav, carousel, form, chatbot, countdown, kịch bản tự chạy.");
