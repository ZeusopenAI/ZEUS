/* ══════════════════════════════════════════════════════════════════════
   app.js — Toàn bộ hành vi của landing page
   Không phụ thuộc thư viện ngoài. Không gửi dữ liệu ra ngoài trừ khi bạn
   cấu hình FORM_ENDPOINT bên dưới.
   ══════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ═══════════════ CẤU HÌNH [SỬA Ở ĐÂY] ═══════════════ */
  const CONFIG = {
    phone: "0763123992",
    phoneDisplay: "0763 123 992",
    zalo: "https://zalo.me/0763123992",
    email: "hello@quangquy.ai",
    // Để trống = form hoạt động ở chế độ tĩnh (lưu trong trình duyệt + gửi qua Zalo).
    // Có thể trỏ tới Google Apps Script / n8n / Formspree nếu bạn muốn nhận lead tự động.
    formEndpoint: "",
    petals: true,
  };

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  // Guard cho môi trường không có matchMedia (trình duyệt cũ / môi trường test)
  const media = (q) =>
    typeof window.matchMedia === "function" ? window.matchMedia(q) : { matches: false, addEventListener() {}, addListener() {} };
  const reduceMotion = media("(prefers-reduced-motion: reduce)").matches;
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* bỏ qua */ } },
  };

  /* ═══════════════ TOAST ═══════════════ */
  const toastEl = $("#toast");
  let toastTimer;
  function toast(msg, ms = 3600) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add("is-show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("is-show"), ms);
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "-1000px";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); resolve(); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  /* ═══════════════ HEADER + NAV ═══════════════ */
  const header = $("#header");
  const nav = $("#nav");
  const burger = $("#burger");

  function onScrollHeader() {
    if (header) header.classList.toggle("is-stuck", window.scrollY > 12);
  }

  if (burger && nav) {
    burger.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", String(open));
      burger.setAttribute("aria-label", open ? "Đóng menu" : "Mở menu");
    });
    nav.addEventListener("click", (e) => {
      if (e.target.tagName === "A") {
        nav.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Đánh dấu mục đang xem
  const navLinks = $$("#nav a");
  const sectionIds = navLinks.map((a) => a.getAttribute("href")).filter((h) => h && h.startsWith("#"));
  if ("IntersectionObserver" in window && sectionIds.length) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (!en.isIntersecting) return;
          const id = "#" + en.target.id;
          navLinks.forEach((a) => a.classList.toggle("is-active", a.getAttribute("href") === id));
        });
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    sectionIds.forEach((id) => {
      const el = document.querySelector(id);
      if (el) io.observe(el);
    });
  }

  /* ═══════════════ THANH TIẾN ĐỘ ĐỌC ═══════════════ */
  const bar = $("#readingBar");
  function onScrollProgress() {
    if (!bar) return;
    const h = document.documentElement;
    const max = h.scrollHeight - h.clientHeight;
    const pct = max > 0 ? (h.scrollTop || document.body.scrollTop) / max * 100 : 0;
    bar.style.width = pct.toFixed(2) + "%";
  }

  /* ═══════════════ NÚT LÊN ĐẦU TRANG ═══════════════ */
  const toTop = $("#toTop");
  if (toTop) {
    toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" }));
  }
  function onScrollTop() {
    if (toTop) toTop.classList.toggle("is-visible", window.scrollY > 700);
  }

  let rafPending = false;
  window.addEventListener("scroll", () => {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => {
      onScrollHeader();
      onScrollProgress();
      onScrollTop();
      rafPending = false;
    });
  }, { passive: true });
  onScrollHeader(); onScrollProgress(); onScrollTop();

  /* ═══════════════ THANH THÔNG BÁO ═══════════════ */
  const announce = $("#announce");
  const announceClose = $("#announceClose");
  const HIDE_KEY = "qq_announce_hidden_until";
  if (announce) {
    const until = store.get(HIDE_KEY, 0);
    if (until && Date.now() < until) announce.classList.add("is-hidden");
    if (announceClose) {
      announceClose.addEventListener("click", () => {
        announce.classList.add("is-hidden");
        store.set(HIDE_KEY, Date.now() + 3 * 24 * 60 * 60 * 1000); // ẩn 3 ngày
      });
    }
  }

  /* ═══════════════ COUNTDOWN (hết tháng) ═══════════════ */
  const cdEl = $("#countdown");
  if (cdEl) {
    const cells = {
      d: $('[data-cd="d"]', cdEl),
      h: $('[data-cd="h"]', cdEl),
      m: $('[data-cd="m"]', cdEl),
      s: $('[data-cd="s"]', cdEl),
    };
    const pad = (n) => String(Math.max(0, n)).padStart(2, "0");
    function tick() {
      const now = new Date();
      // Mốc: 23:59:59 ngày cuối cùng của tháng hiện tại
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59);
      let diff = Math.max(0, end - now);
      const d = Math.floor(diff / 86400000); diff -= d * 86400000;
      const h = Math.floor(diff / 3600000); diff -= h * 3600000;
      const m = Math.floor(diff / 60000); diff -= m * 60000;
      const s = Math.floor(diff / 1000);
      if (cells.d) cells.d.textContent = pad(d);
      if (cells.h) cells.h.textContent = pad(h);
      if (cells.m) cells.m.textContent = pad(m);
      if (cells.s) cells.s.textContent = pad(s);
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ═══════════════ REVEAL + ĐẾM SỐ ═══════════════ */
  function countUp(el) {
    const target = parseFloat(el.dataset.count);
    if (isNaN(target)) return;
    if (reduceMotion) { el.textContent = target.toLocaleString("vi-VN"); return; }
    const dur = 1200;
    const start = performance.now();
    function frame(t) {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString("vi-VN");
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function activate(el) {
    el.classList.add("is-visible");
    $$("[data-count]", el).forEach((n) => {
      if (!n.dataset.done) { n.dataset.done = "1"; countUp(n); }
    });
    if (el.hasAttribute && el.hasAttribute("data-count") && !el.dataset.done) {
      el.dataset.done = "1";
      countUp(el);
    }
    const term = el.matches("[data-terminal]") ? el : el.querySelector("[data-terminal]");
    if (term) runTerminal(term);
    const render = el.querySelector("#renderFill");
    if (render) runRender(render);
  }

  if ("IntersectionObserver" in window && !reduceMotion) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) { activate(en.target); io.unobserve(en.target); }
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -40px 0px" }
    );
    $$(".reveal").forEach((el) => io.observe(el));
    // Phần không có class .reveal nhưng cần kích hoạt (terminal, render bar, số liệu hero)
    $$("[data-terminal], .term-render, .hero__panel").forEach((el) => {
      if (!el.closest(".reveal")) io.observe(el);
    });
    // Số liệu hero chạy ngay
    $$(".kpi__value [data-count], .stat__num [data-count]").forEach((n) => {
      if (!n.dataset.done) { n.dataset.done = "1"; countUp(n); }
    });
  } else {
    $$(".reveal").forEach((el) => activate(el));
  }

  /* ═══════════════ TERMINAL GÕ CHỮ ═══════════════ */
  function tokenize(html) {
    const tokens = [];
    const re = /<[^>]+>/g;
    let last = 0, m;
    while ((m = re.exec(html))) {
      for (let i = last; i < m.index; i++) {
        if (html[i] === "&") {
          const semi = html.indexOf(";", i);
          if (semi > -1 && semi - i <= 8) { tokens.push({ c: html.slice(i, semi + 1) }); i = semi; continue; }
        }
        tokens.push({ c: html[i] });
      }
      tokens.push({ h: m[0] });
      last = re.lastIndex;
    }
    for (let i = last; i < html.length; i++) tokens.push({ c: html[i] });
    return tokens;
  }

  function runTerminal(term) {
    const code = term.querySelector("[data-term-lines]");
    if (!code || code.dataset.typed) return;
    code.dataset.typed = "1";

    const tokens = tokenize(code.innerHTML);
    if (reduceMotion) return;

    code.innerHTML = "";
    let out = "", count = 0, i = 0;
    const totalChars = tokens.filter((t) => t.c !== undefined).length;

    const timer = setInterval(() => {
      // gõ 2 ký tự mỗi nhịp
      for (let step = 0; step < 2 && i < tokens.length; step++) {
        while (i < tokens.length) {
          const t = tokens[i++];
          if (t.h !== undefined) out += t.h;
          else { out += t.c; count++; break; }
        }
      }
      code.innerHTML = out;
      if (count >= totalChars || i >= tokens.length) clearInterval(timer);
    }, 15);
  }

  function runRender(fill) {
    if (fill.dataset.run) return;
    fill.dataset.run = "1";
    const pctEl = $("#renderPct");
    let p = 0;
    const target = 92;
    const step = () => {
      p += Math.max(1, (target - p) * 0.08);
      if (p >= target) p = target;
      fill.style.width = p + "%";
      if (pctEl) pctEl.textContent = Math.round(p) + "%";
      if (p < target) setTimeout(step, reduceMotion ? 0 : 60);
    };
    step();
  }

  /* ═══════════════ CAROUSEL SẢN PHẨM ═══════════════ */
  const carousel = $("#carousel");
  if (carousel) {
    const slides = $$(".slide", carousel);
    const dotsWrap = $("#dots");
    const prev = $("#prevBtn");
    const next = $("#nextBtn");
    const viewport = $("#carouselViewport");
    let index = 0;
    let autoTimer;

    slides.forEach((s, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-label", "Sản phẩm " + (i + 1) + ": " + ($("h3", s)?.textContent || ""));
      b.addEventListener("click", () => go(i, true));
      dotsWrap && dotsWrap.appendChild(b);
    });
    const dots = dotsWrap ? $$("button", dotsWrap) : [];

    function go(i, stopAuto) {
      index = (i + slides.length) % slides.length;
      slides.forEach((s, k) => s.classList.toggle("is-active", k === index));
      dots.forEach((d, k) => {
        d.classList.toggle("is-active", k === index);
        d.setAttribute("aria-selected", String(k === index));
      });
      if (stopAuto) restartAuto();
    }

    function restartAuto() {
      clearInterval(autoTimer);
      if (reduceMotion) return;
      autoTimer = setInterval(() => go(index + 1), 9000);
    }

    if (prev) prev.addEventListener("click", () => go(index - 1, true));
    if (next) next.addEventListener("click", () => go(index + 1, true));

    if (viewport) {
      viewport.addEventListener("keydown", (e) => {
        if (e.key === "ArrowLeft") { go(index - 1, true); e.preventDefault(); }
        if (e.key === "ArrowRight") { go(index + 1, true); e.preventDefault(); }
      });

      let x0 = null;
      viewport.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
      viewport.addEventListener("touchend", (e) => {
        if (x0 === null) return;
        const dx = e.changedTouches[0].clientX - x0;
        if (Math.abs(dx) > 48) go(index + (dx < 0 ? 1 : -1), true);
        x0 = null;
      }, { passive: true });

      viewport.addEventListener("mouseenter", () => clearInterval(autoTimer));
      viewport.addEventListener("mouseleave", restartAuto);
      viewport.addEventListener("focusin", () => clearInterval(autoTimer));
    }

    go(0);
    restartAuto();
  }

  /* ═══════════════ DÒNG HOẠT ĐỘNG (hero) ═══════════════ */
  const feed = $("#feedList");
  if (feed && !reduceMotion) {
    const items = $$("li", feed);
    let t = 0;
    setInterval(() => {
      const el = items[t % items.length];
      el.style.animation = "none";
      void el.offsetWidth;
      el.style.animation = "";
      feed.appendChild(el);           // đẩy xuống cuối → tạo cảm giác cập nhật
      t++;
    }, 5200);
  }

  /* ═══════════════ BỘ ĐẾM LIVE ═══════════════ */
  const readingEl = $("#readingNow");
  const totalEl = $("#totalReads");
  if (readingEl || totalEl) {
    const total = store.get("qq_total_reads", 8448) + 1;
    store.set("qq_total_reads", total);
    let reading = 40 + Math.floor(Math.random() * 12);

    const fmt = (n) => n.toLocaleString("vi-VN");
    function paint() {
      if (readingEl) readingEl.textContent = fmt(reading);
      if (totalEl) totalEl.textContent = fmt(total);
    }
    paint();

    setInterval(() => {
      reading += Math.floor(Math.random() * 5) - 2;          // dao động ±2
      reading = Math.min(96, Math.max(21, reading));
      paint();
    }, 4200);

    setInterval(() => {
      const next = store.get("qq_total_reads", 8448) + 1;
      store.set("qq_total_reads", next);
      if (totalEl) totalEl.textContent = fmt(next);
    }, 60000);
  }

  /* ═══════════════ NĂM Ở FOOTER ═══════════════ */
  const yearEl = $("#year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  /* ═══════════════ NÚT CHỌN GÓI → ĐIỀN FORM ═══════════════ */
  const planMap = {
    Starter: { need: "AI Chatbot CSKH 24/7", note: "Quan tâm gói Starter — chatbot 1 kênh, tới 500 SKU." },
    Professional: { need: "Automation đa kênh (Zalo + Facebook + CRM)", note: "Quan tâm gói Professional — chatbot 4 kênh + automation n8n." },
    Enterprise: { need: "Chưa rõ — cần tư vấn hướng đi", note: "Quan tâm gói Enterprise — nhiều chi nhánh / dữ liệu lớn." },
  };
  $$("[data-plan]").forEach((link) => {
    link.addEventListener("click", () => {
      const p = planMap[link.dataset.plan];
      if (!p) return;
      const need = $("#fNeed");
      const note = $("#fNote");
      if (need) need.value = p.need;
      if (note && !note.value.trim()) note.value = p.note;
      setTimeout(() => {
        const name = $("#fName");
        if (name) name.focus({ preventScroll: true });
      }, 620);
    });
  });

  /* ═══════════════ FORM LEAD ═══════════════ */
  const form = $("#leadForm");
  if (form) {
    const submitBtn = $("#submitBtn");
    const errOf = (id, msg) => {
      const el = form.querySelector('[data-err-for="' + id + '"]');
      if (el) el.textContent = msg || "";
      const input = form.querySelector("#" + id);
      if (input) input.classList.toggle("is-invalid", !!msg);
    };

    const rules = {
      fName: (v) => (v.trim().length >= 2 ? "" : "Vui lòng nhập tên (ít nhất 2 ký tự)."),
      fPhone: (v) => {
        const digits = v.replace(/[\s.\-()]/g, "");
        return /^(0|\+84)\d{8,10}$/.test(digits) ? "" : "Số điện thoại/Zalo chưa đúng (VD: 0901 234 567).";
      },
      fNeed: (v) => (v ? "" : "Chọn một nhu cầu để tôi chuẩn bị trước."),
    };

    ["fName", "fPhone", "fNeed"].forEach((id) => {
      const el = form.querySelector("#" + id);
      if (!el) return;
      el.addEventListener("blur", () => errOf(id, rules[id](el.value)));
      el.addEventListener("input", () => { if (el.classList.contains("is-invalid")) errOf(id, ""); });
    });

    function validate() {
      let ok = true;
      Object.keys(rules).forEach((id) => {
        const el = form.querySelector("#" + id);
        if (!el) return;
        const msg = rules[id](el.value);
        errOf(id, msg);
        if (msg) ok = false;
      });
      return ok;
    }

    function buildMessage() {
      const data = new FormData(form);
      const lines = [
        "— Yêu cầu tư vấn từ landing page —",
        "Tên: " + (data.get("name") || "").toString().trim(),
        "SĐT/Zalo: " + (data.get("phone") || "").toString().trim(),
        "Nhu cầu: " + (data.get("need") || "").toString().trim(),
      ];
      const note = (data.get("note") || "").toString().trim();
      if (note) lines.push("Ghi chú: " + note);
      lines.push("Thời gian: " + new Date().toLocaleString("vi-VN"));
      return lines.join("\n");
    }

    function showResult(message) {
      let box = $("#leadResult");
      if (!box) {
        box = document.createElement("div");
        box.id = "leadResult";
        box.style.cssText =
          "border:1px solid rgba(230,193,118,.4);border-radius:12px;padding:14px;background:rgba(230,193,118,.08);display:grid;gap:10px";
        form.appendChild(box);
      }
      box.innerHTML =
        "<b style='color:var(--gold-soft)'>✅ Đã ghi nhận yêu cầu của bạn</b>" +
        "<span style='font-size:.84rem;color:var(--text-2)'>Bấm nút bên dưới để gửi ngay qua Zalo (nội dung đã soạn sẵn), " +
        "hoặc copy rồi dán vào bất kỳ kênh nào bạn muốn.</span>" +
        "<div style='display:flex;gap:10px;flex-wrap:wrap'>" +
        '<a class="btn btn--gold btn--sm" href="' + CONFIG.zalo + '" target="_blank" rel="noopener">💬 Mở Zalo để gửi</a>' +
        '<button class="btn btn--outline btn--sm" type="button" id="copyLead">📋 Copy nội dung</button>' +
        '<a class="btn btn--ghost btn--sm" href="tel:' + CONFIG.phone + '">📞 Gọi ngay</a>' +
        "</div>" +
        '<span class="mono" style="color:var(--muted);white-space:pre-wrap">' + message.replace(/</g, "&lt;") + "</span>";

      const copyBtn = $("#copyLead");
      if (copyBtn) {
        copyBtn.addEventListener("click", () => {
          copyText(message).then(
            () => toast("Đã copy nội dung — dán vào Zalo/Messenger để gửi nhé!"),
            () => toast("Trình duyệt chặn copy. Bạn chọn nội dung và copy thủ công giúp mình.")
          );
        });
      }
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!validate()) {
        toast("Vui lòng kiểm tra lại các ô được đánh dấu đỏ.");
        const bad = form.querySelector(".is-invalid");
        if (bad) bad.focus();
        return;
      }

      const message = buildMessage();

      // Lưu cục bộ để không mất dữ liệu nếu người dùng đổi trang
      const leads = store.get("qq_leads", []);
      leads.push({ at: new Date().toISOString(), message });
      store.set("qq_leads", leads.slice(-30));

      if (CONFIG.formEndpoint) {
        try {
          if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Đang gửi…"; }
          await fetch(CONFIG.formEndpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.fromEntries(new FormData(form))),
          });
          toast("Đã gửi yêu cầu! Tôi sẽ phản hồi trong 30 phút (8:00–21:00).");
        } catch (err) {
          toast("Chưa gửi được tự động — nội dung đã được lưu, bạn gửi qua Zalo giúp mình nhé.");
        } finally {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Nhận tư vấn miễn phí"; }
        }
      } else {
        toast("Đã lưu yêu cầu trong trình duyệt — bấm “Mở Zalo để gửi” để hoàn tất.");
      }

      showResult(message);
      form.querySelector("#fName").value = "";
      form.querySelector("#fPhone").value = "";
      form.querySelector("#fNote").value = "";
    });
  }

  /* ═══════════════ HOA ĐÀO RƠI ═══════════════ */
  const canvas = $("#petals");
  if (canvas && CONFIG.petals && !reduceMotion) {
    const ctx = canvas.getContext("2d");
    let W = 0, H = 0, petals = [], running = true;

    const COLORS = [
      "rgba(255,183,197,.72)",
      "rgba(255,214,224,.58)",
      "rgba(255,240,245,.42)",
      "rgba(230,193,118,.34)",
    ];

    function resize() {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = Math.floor(W * dpr);
      canvas.height = Math.floor(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(30, Math.max(10, Math.round(W / 58)));
      petals = new Array(count).fill(0).map(() => spawn(true));
    }

    function spawn(anywhere) {
      return {
        x: Math.random() * W,
        y: anywhere ? Math.random() * H : -20,
        r: 4 + Math.random() * 7,
        vy: 0.25 + Math.random() * 0.7,
        sway: 0.5 + Math.random() * 1.4,
        phase: Math.random() * Math.PI * 2,
        spin: (Math.random() - 0.5) * 0.02,
        rot: Math.random() * Math.PI,
        alpha: 0.35 + Math.random() * 0.5,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
      };
    }

    function drawPetal(p) {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      // cánh hoa: hai cung đối xứng tạo hình giọt nước hơi cong
      ctx.moveTo(0, -p.r);
      ctx.bezierCurveTo(p.r * 0.9, -p.r * 0.5, p.r * 0.75, p.r * 0.7, 0, p.r);
      ctx.bezierCurveTo(-p.r * 0.75, p.r * 0.7, -p.r * 0.9, -p.r * 0.5, 0, -p.r);
      ctx.fill();
      ctx.restore();
    }

    let t = 0;
    function loop() {
      if (!running) return;
      t += 0.012;
      ctx.clearRect(0, 0, W, H);
      for (let i = 0; i < petals.length; i++) {
        const p = petals[i];
        p.y += p.vy;
        p.x += Math.sin(t * p.sway + p.phase) * 0.55;
        p.rot += p.spin;
        if (p.y - p.r > H + 20 || p.x < -40 || p.x > W + 40) petals[i] = spawn(false);
        drawPetal(p);
      }
      requestAnimationFrame(loop);
    }

    let resizeTimer;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 180);
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) { running = false; }
      else if (!running) { running = true; requestAnimationFrame(loop); }
    });

    resize();
    requestAnimationFrame(loop);
  }

  /* ═══════════════ CTA: dẫn tới khung chat demo ═══════════════ */
  $$('a[href="#chatbot"]').forEach((a) => {
    a.addEventListener("click", () => {
      const input = $("#chatInput");
      if (input) setTimeout(() => input.focus({ preventScroll: true }), 900);
    });
  });
})();
