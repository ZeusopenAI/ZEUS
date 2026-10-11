/* ══════════════════════════════════════════════════════════════════════
   chat-demo.js — Demo chatbot AI (mô phỏng phía trình duyệt)
   Không gọi API, không gửi dữ liệu đi đâu. Chỉ minh hoạ cách một chatbot
   RAG vận hành: hiểu câu hỏi → truy xuất đúng dữ liệu → trả lời + gửi ảnh.
   Dữ liệu dưới đây là ví dụ cho cửa hàng nội thất "Minh Phát".
   ══════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ─────────────── DỮ LIỆU DEMO [SỬA Ở ĐÂY] ─────────────── */
  const PRODUCTS = {
    SF204: {
      sku: "SF204",
      emoji: "🛋️",
      name: "Sofa L-Shape SF204",
      color: "Ghi xám",
      price: "12.800.000",
      stock: "Còn hàng · giao 3–5 ngày",
      sizes: "2,4m × 1,6m — hợp phòng 18–24m²",
    },
    SF118: {
      sku: "SF118",
      emoji: "🪑",
      name: "Sofa 3 chỗ SF118",
      color: "Beige",
      price: "9.500.000",
      stock: "Còn hàng · giao trong ngày",
      sizes: "2,1m × 0,9m — hợp phòng 12–16m²",
    },
    SG102: {
      sku: "SG102",
      emoji: "🛋️",
      name: "Sofa giường SG102",
      color: "Xám đậm",
      price: "14.200.000",
      stock: "Còn 4 chiếc · giao 5–7 ngày",
      sizes: "1,9m — gấp thành giường 1,4m",
    },
  };

  const COLORS = [
    { code: "SF204-KT", label: "Kem trắng", emoji: "🤍" },
    { code: "SF204-NV", label: "Navy", emoji: "💙" },
    { code: "SF204-XG", label: "Xanh rêu", emoji: "💚" },
    { code: "SF204-ND", label: "Nâu da bò", emoji: "🤎" },
    { code: "SF204-GX", label: "Ghi xám", emoji: "🩶" },
  ];

  const HOTLINE = "0763 123 992";
  const ADDRESS = "123 Nguyễn Văn Linh, Q7";

  /* ─────────────── TIỆN ÍCH ─────────────── */
  const $ = (sel, root = document) => root.querySelector(sel);
  const now = () => {
    const d = new Date();
    return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const stripTone = (s) =>
    s
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();

  /* ─────────────── DOM ─────────────── */
  const bodyEl = $("#chatBody");
  const quickEl = $("#chatQuick");
  const formEl = $("#chatForm");
  const inputEl = $("#chatInput");
  const replayEl = $("#chatReplay");

  if (!bodyEl || !formEl) return;

  let scriptToken = 0;      // huỷ kịch bản tự chạy khi người dùng can thiệp
  let busy = false;

  /* ─────────────── RENDER ─────────────── */
  function scrollDown() {
    bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  function addMsg(role, html, tag) {
    const wrap = document.createElement("div");
    wrap.className = "msg msg--" + (role === "user" ? "out" : "in");

    const who = document.createElement("div");
    who.className = "msg__who";
    who.innerHTML =
      (role === "user" ? "Khách" : "AI Assistant") +
      ' <span class="msg__tag">' + esc(tag || (role === "user" ? now() : "tự động")) + "</span>";

    const bubble = document.createElement("div");
    bubble.className = "msg__bubble";
    bubble.innerHTML = html;

    if (role === "user") {
      wrap.append(bubble, who);
    } else {
      wrap.append(who, bubble);
    }
    bodyEl.appendChild(wrap);
    scrollDown();
    return wrap;
  }

  function addTyping() {
    const wrap = document.createElement("div");
    wrap.className = "msg msg--in";
    wrap.innerHTML =
      '<div class="msg__who">AI Assistant <span class="msg__tag">đang soạn</span></div>' +
      '<div class="typing"><i></i><i></i><i></i></div>';
    bodyEl.appendChild(wrap);
    scrollDown();
    return wrap;
  }

  function productCards(skus) {
    const cards = skus
      .map((sku) => {
        const p = PRODUCTS[sku];
        if (!p) return "";
        return (
          '<div class="prod">' +
          '<div class="prod__thumb">' + p.emoji + "</div>" +
          '<div class="prod__info">' +
          "<b>" + esc(p.name) + "</b>" +
          '<span>' + esc(p.color) + " · " + esc(p.sizes) + "</span>" +
          '<span class="prod__price">' + p.price + " VNĐ</span>" +
          '<span class="prod__stock">✓ ' + esc(p.stock) + "</span>" +
          "</div></div>"
        );
      })
      .join("");
    return '<div class="msg__products">' + cards + "</div>";
  }

  function colorCards() {
    const cards = COLORS.slice(0, 5)
      .map(
        (c) =>
          '<div class="prod"><div class="prod__thumb">' + c.emoji + "</div>" +
          '<div class="prod__info"><b>' + esc(c.label) + "</b><span class=\"mono\">" + esc(c.code) + "</span></div></div>"
      )
      .join("");
    return '<div class="msg__products">' + cards + "</div>";
  }

  function handoffCard() {
    return (
      '<div class="prod" style="margin-top:8px">' +
      '<div class="prod__info">' +
      "<b>🧑‍💼 Đã chuyển cho nhân viên — Ms. Hân</b>" +
      '<span>Tóm tắt hội thoại: khách hỏi sofa 20m², ngân sách 15tr, thích SF204 màu kem, đã hỏi bảo hành &amp; giao hàng.</span>' +
      '<span class="prod__stock">Thời gian chờ ước tính: &lt; 2 phút</span>' +
      "</div></div>"
    );
  }

  /* ─────────────── BOT TRẢ LỜI THEO TỪ KHOÁ ─────────────── */
  function reply(raw) {
    const t = stripTone(raw);

    const has = (...keys) => keys.some((k) => t.includes(k));

    // Khiếu nại / yêu cầu gặp người thật → handoff
    if (has("nhan vien", "gap nguoi", "khieu nai", "complain", "te qua", "doi tra", "phan nan")) {
      return {
        html:
          "Mình xin lỗi vì trải nghiệm chưa tốt ạ 🙏 Mình đã ghi nhận và chuyển ngay cho nhân viên phụ trách." +
          handoffCard(),
        tag: "handoff · human-in-the-loop",
      };
    }

    // Giá
    if (has("gia", "bao nhieu", "price", "nhieu tien")) {
      return {
        html:
          "Dạ mình gửi bạn mặt bằng giá 3 mẫu bán chạy nhất:\n" +
          "• SF204 (L-shape) — 12.800.000 VNĐ\n" +
          "• SF118 (3 chỗ) — 9.500.000 VNĐ\n" +
          "• SG102 (sofa giường) — 14.200.000 VNĐ\n\n" +
          "Giá đã gồm khung gỗ + vải bọc, chưa gồm phí phụ kiện trang trí. Bạn cho mình biết diện tích phòng và ngân sách, mình gợi ý đúng mẫu hơn nhé.",
        tag: "truy xuất: products.json",
        products: ["SF204", "SF118"],
      };
    }

    // Bảo hành
    if (has("bao hanh", "warranty", "chinh sach")) {
      return {
        html:
          "Về bảo hành ạ:\n" +
          "• Khung gỗ: 3 năm\n" +
          "• Vải bọc: 1 năm (hỗ trợ thay nếu lỗi đường may)\n" +
          "• Đổi trả trong 7 ngày nếu không đúng mẫu/không đúng mã đặt\n\n" +
          "Miễn phí vận chuyển &amp; lắp đặt nội thành TP.HCM, miễn phí bảo dưỡng 1 lần trong năm đầu.",
        tag: "knowledge base: chính sách",
      };
    }

    // Màu sắc
    if (has("mau", "color", "kem trang", "navy")) {
      return {
        html:
          "SF204 hiện có 5 màu: ghi xám, kem trắng, navy, xanh rêu, nâu da bò — tất cả đều còn hàng tại kho HCM.\n\nHai màu được chọn nhiều nhất là kem trắng và navy. Mình gửi ảnh thực tế bạn xem nhé 📸",
        tag: "auto image sending",
        colors: true,
      };
    }

    // Tồn kho / giao hàng
    if (has("kho", "con hang", "giao", "ship", "van chuyen", "bao lau")) {
      return {
        html:
          "Kiểm tra kho real-time ạ:\n" +
          "• SF204 (ghi xám): còn 12 chiếc — giao 3–5 ngày\n" +
          "• SF118 (beige): còn 23 chiếc — giao trong ngày\n" +
          "• SG102: còn 4 chiếc — giao 5–7 ngày\n\n" +
          "Đặt trước 12h hôm nay, trong nội thành TP.HCM giao miễn phí ngay trong buổi chiều 🚚",
        tag: "database: 50.241 SKU",
      };
    }

    // Đặt hàng
    if (has("dat", "order", "mua", "chot", "lay", "tien hanh")) {
      return {
        html:
          "Được ạ! Bạn đặt hàng theo cách nào tiện nhất:\n\n" +
          "1️⃣ Đặt ngay tại đây — mình tạo đơn và gửi link thanh toán\n" +
          "2️⃣ Gọi hotline: " + HOTLINE + "\n" +
          "3️⃣ Đến showroom: " + ADDRESS + "\n\n" +
          "Mình giữ hàng cho bạn trong 24h nhé — bạn cho mình xin tên và số điện thoại ạ.",
        tag: "workflow: chốt đơn",
      };
    }

    // Sản phẩm nói chung
    if (has("sofa", "ghe", "ban", "giuong", "san pham", "tu", "20m2", "15 trieu")) {
      return {
        html:
          "Với phòng khách khoảng 20m² và ngân sách tầm 15 triệu, mình có 3 lựa chọn phù hợp nhất. Cho mình gửi ảnh để bạn tham khảo nhé:",
        tag: "AI phân tích nhu cầu",
        products: ["SF204", "SF118", "SG102"],
      };
    }

    // Liên hệ
    if (has("hotline", "so dien thoai", "lien he", "dia chi", "showroom")) {
      return {
        html:
          "Bạn liên hệ mình qua:\n• Hotline/Zalo: " + HOTLINE + "\n• Showroom: " + ADDRESS +
          " (mở 8:00–21:00)\n• Hoặc Zalo OA — nhắn là có người phản hồi trong 2 phút ạ.",
        tag: "thông tin liên hệ",
      };
    }

    // Cảm ơn
    if (has("cam on", "thank", "ok", "oke", "duoc do")) {
      return {
        html: "Dạ cảm ơn bạn 🙏 Bạn cần mình kiểm tra thêm mẫu nào, màu nào hay thời gian giao cụ thể không ạ?",
        tag: "tự động",
      };
    }

    // Mặc định
    return {
      html:
        "Mình chưa chắc đã hiểu đúng ý bạn 🤔 Bạn có thể hỏi mình về:\n" +
        "• Giá và tình trạng kho từng mẫu\n• Màu sắc, kích thước, chất liệu\n• Bảo hành, đổi trả, vận chuyển\n• Đặt hàng hoặc kiểm tra đơn đã có\n\n" +
        "Hoặc nếu bạn muốn trao đổi trực tiếp, mình chuyển sang nhân viên ngay ạ.",
      tag: "fallback · confidence thấp",
    };
  }

  /* ─────────────── GỬI TIN NHẮN ─────────────── */
  async function send(text, opts = {}) {
    const value = String(text || "").trim();
    if (!value || busy) return;

    busy = true;
    scriptToken++;                 // dừng kịch bản tự chạy nếu đang chạy

    addMsg("user", esc(value));
    inputEl.value = "";

    const typing = addTyping();
    await sleep(opts.fast ? 420 : 900);
    typing.remove();

    const r = reply(value);
    addMsg("bot", r.html, r.tag);
    if (r.products) bodyEl.querySelector(".msg:last-child").insertAdjacentHTML("beforeend", productCards(r.products));
    if (r.colors) bodyEl.querySelector(".msg:last-child").insertAdjacentHTML("beforeend", colorCards());
    scrollDown();

    busy = false;
  }

  /* ─────────────── KỊCH BẢN TỰ CHẠY ─────────────── */
  const SCRIPT = [
    {
      role: "bot",
      text:
        "Xin chào! Tôi là trợ lý AI của Minh Phát. Tôi có thể giúp bạn tìm sản phẩm, kiểm tra giá, tình trạng kho hoặc tư vấn lựa chọn phù hợp. Bạn đang cần tìm gì ạ? 😊",
      tag: "tự động",
      delay: 700,
    },
    { role: "user", text: "Mình cần ghế sofa cho phòng khách khoảng 20m2, ngân sách tầm 15 triệu", delay: 1500 },
    {
      role: "bot",
      text: "Với phòng 20m² và ngân sách 15 triệu, mình có 3 options phù hợp. Cho mình gửi ảnh để bạn tham khảo nhé:",
      tag: "AI phân tích nhu cầu",
      products: ["SF204", "SF118", "SG102"],
      delay: 1700,
    },
    { role: "user", text: "Cái SF204 nhìn được đó. Có màu nào khác không? Và có bảo hành không?", delay: 1500 },
    {
      role: "bot",
      text:
        "SF204 có 5 màu: ghi xám, kem trắng, navy, xanh rêu, nâu da bò. Tất cả đều còn hàng tại kho HCM.\n\n" +
        "Về bảo hành: 3 năm khung gỗ, 1 năm vải bọc. Miễn phí vận chuyển và lắp đặt nội thành.\n\n" +
        "Bạn muốn xem ảnh thực tế màu nào không? Mình gửi ngay ạ 📸",
      tag: "tự động · database: 50.241 SKU",
      delay: 1900,
    },
    { role: "user", text: "Cho mình xem màu kem trắng và navy đi", delay: 1500 },
    {
      role: "bot",
      text:
        "Cả 2 đều rất hợp phòng khách hiện đại. Kem trắng tạo cảm giác rộng hơn cho phòng 20m². Navy sang trọng và dễ phối với nội thất gỗ tự nhiên. Bạn thích phong cách nào hơn ạ?",
      tag: "AI tư vấn theo context",
      colors: true,
      delay: 1800,
    },
    { role: "user", text: "Oke mình lấy màu kem. Đặt được luôn không?", delay: 1600 },
    {
      role: "bot",
      text:
        "Được ạ! Bạn đặt hàng theo cách nào tiện nhất:\n\n" +
        "1️⃣ Đặt ngay tại đây — mình tạo đơn, gửi link thanh toán\n" +
        "2️⃣ Gọi hotline: " + HOTLINE + "\n" +
        "3️⃣ Đến showroom: " + ADDRESS + "\n\n" +
        "Đặt trước 12h hôm nay — giao chiều tối cùng ngày miễn phí nội thành HCM 🚚",
      tag: "chuyển sang bước chốt đơn",
      delay: 1900,
    },
  ];

  async function playScript() {
    const token = ++scriptToken;
    bodyEl.innerHTML = "";
    busy = true;

    for (const step of SCRIPT) {
      if (token !== scriptToken) { busy = false; return; }

      if (step.role === "user") {
        addMsg("user", esc(step.text));
        await sleep(step.delay);
      } else {
        const typing = addTyping();
        await sleep(Math.min(step.delay, 1200));
        if (token !== scriptToken) { typing.remove(); busy = false; return; }
        typing.remove();
        addMsg("bot", esc(step.text).replace(/\n/g, "<br />"), step.tag);
        const last = bodyEl.querySelector(".msg:last-child");
        if (step.products) last.insertAdjacentHTML("beforeend", productCards(step.products));
        if (step.colors) last.insertAdjacentHTML("beforeend", colorCards());
        scrollDown();
        await sleep(step.delay);
      }
    }
    busy = false;
  }

  /* ─────────────── SỰ KIỆN ─────────────── */
  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    send(inputEl.value);
  });

  if (quickEl) {
    quickEl.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-q]");
      if (!btn) return;
      const q = btn.dataset.q;
      // Gợi ý "xem màu" hoặc "đặt hàng" dùng câu trả lời trực tiếp cho mượt
      send(q);
    });
  }

  if (replayEl) {
    replayEl.addEventListener("click", () => {
      busy = false;
      playScript();
    });
  }

  /* Khởi động demo: tự chạy kịch bản khi khung chat vào khung nhìn */
  const phone = $(".chatphone");
  let started = false;

  function startOnce() {
    if (started) return;
    started = true;
    playScript();
  }

  if ("IntersectionObserver" in window && phone) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) { startOnce(); io.disconnect(); }
        });
      },
      { threshold: 0.35 }
    );
    io.observe(phone);
  } else {
    startOnce();
  }

  // Cho phép app.js gọi send() khi người dùng bấm CTA "thử chatbot"
  window.ChatDemo = { send, replay: playScript };
})();
