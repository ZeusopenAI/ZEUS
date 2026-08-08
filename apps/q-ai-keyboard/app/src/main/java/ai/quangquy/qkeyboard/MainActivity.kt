package ai.quangquy.qkeyboard

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast

class MainActivity : Activity() {
    private lateinit var prefs: AppPrefs
    private lateinit var translator: TranslationManager
    private lateinit var ai: AiGateway
    private lateinit var host: FrameLayout
    private lateinit var nav: LinearLayout
    private val navButtons = linkedMapOf<Tab, TextView>()
    private lateinit var uiPrefs: android.content.SharedPreferences
    private var dark = false

    private enum class Tab { HOME, TOOLS, AI, KEYBOARD, SETTINGS }

    private val bg get() = if (dark) Color.rgb(31, 29, 30) else Color.rgb(247, 248, 251)
    private val surface get() = if (dark) Color.rgb(57, 56, 57) else Color.WHITE
    private val surface2 get() = if (dark) Color.rgb(72, 71, 72) else Color.rgb(238, 241, 247)
    private val text get() = if (dark) Color.WHITE else Color.rgb(25, 25, 28)
    private val muted get() = if (dark) Color.rgb(190, 188, 192) else Color.rgb(100, 103, 112)
    private val blue = Color.rgb(91, 148, 239)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = AppPrefs(this)
        translator = TranslationManager(this)
        ai = AiGateway(prefs)
        uiPrefs = getSharedPreferences("q_keyboard_ui", Context.MODE_PRIVATE)
        resolveTheme()
        applyWindowColors()
        setContentView(buildShell())
        render(Tab.HOME)
    }

    private fun resolveTheme() {
        val mode = uiPrefs.getInt("theme_mode", 0) // 0 system, 1 light, 2 dark
        val systemDark = (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES
        dark = when (mode) { 1 -> false; 2 -> true; else -> systemDark }
    }

    private fun applyWindowColors() {
        window.statusBarColor = bg
        window.navigationBarColor = bg
        window.decorView.systemUiVisibility = if (dark) 0 else View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
    }

    private fun buildShell(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
        }
        host = FrameLayout(this)
        root.addView(host, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(dp(6), dp(6), dp(6), dp(8))
            setBackgroundColor(if (dark) Color.rgb(35, 33, 34) else Color.WHITE)
        }
        val items = listOf(
            Tab.HOME to "⌂\nTrang chủ",
            Tab.TOOLS to "▦\nCông cụ",
            Tab.AI to "✦\nAI",
            Tab.KEYBOARD to "⌨\nBàn phím",
            Tab.SETTINGS to "⚙\nCài đặt"
        )
        items.forEach { (tab, label) ->
            val v = TextView(this).apply {
                this.text = label
                textSize = 12f
                gravity = Gravity.CENTER
                setTextColor(muted)
                setPadding(dp(4), dp(5), dp(4), dp(4))
                setOnClickListener { render(tab) }
            }
            navButtons[tab] = v
            nav.addView(v, LinearLayout.LayoutParams(0, dp(58), 1f))
        }
        root.addView(nav, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(66)))
        return root
    }

    private fun render(tab: Tab) {
        host.removeAllViews()
        navButtons.forEach { (k, v) ->
            v.setTextColor(if (k == tab) blue else muted)
            v.setTypeface(null, if (k == tab) Typeface.BOLD else Typeface.NORMAL)
        }
        host.addView(
            when (tab) {
                Tab.HOME -> homePage()
                Tab.TOOLS -> toolsPage()
                Tab.AI -> aiPage()
                Tab.KEYBOARD -> keyboardPage()
                Tab.SETTINGS -> settingsPage()
            },
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        )
    }

    private fun page(title: String, subtitle: String? = null): Pair<ScrollView, LinearLayout> {
        val scroll = ScrollView(this).apply { setBackgroundColor(bg) }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(20), dp(18), dp(32))
        }
        scroll.addView(root)
        root.addView(TextView(this).apply {
            text = title
            textSize = 27f
            setTextColor(text)
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(0, dp(4), 0, dp(4))
        })
        if (!subtitle.isNullOrBlank()) {
            root.addView(TextView(this).apply {
                text = subtitle
                textSize = 14f
                setTextColor(muted)
                gravity = Gravity.CENTER_HORIZONTAL
                setPadding(dp(10), dp(2), dp(10), dp(16))
            })
        }
        return scroll to root
    }

    private fun homePage(): View {
        val (scroll, root) = page("Q AI Keyboard", "Alpha 0.3 • bàn phím gọn + app quản lý đầy đủ")

        val hero = card().apply {
            addView(TextView(this@MainActivity).apply {
                text = "Quang Quý AI Keyboard"
                textSize = 22f
                setTextColor(text)
                setTypeface(null, Typeface.BOLD)
            })
            addView(TextView(this@MainActivity).apply {
                text = "Telex đơn giản • Hàng số luôn hiện • Dịch tại chỗ • AI theo ngữ cảnh"
                textSize = 14f
                setTextColor(muted)
                setPadding(0, dp(7), 0, dp(14))
            })
            addView(primaryButton("Bật bàn phím") {
                startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
            })
            addView(secondaryButton("Chọn Q AI Keyboard") {
                (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showInputMethodPicker()
            })
        }
        root.addView(hero)

        root.addView(section("Dùng nhanh"))
        val quick = listOf(
            Triple("✦", "Trò chuyện AI", "Hỏi AI hoặc xử lý đoạn văn"),
            Triple("🌐", "Dịch", "Việt → Anh/Nhật/Trung/Hàn"),
            Triple("📝", "Ghi chú", "Lưu nội dung cần dùng lại"),
            Triple("⌨", "Tùy chỉnh bàn phím", "Chiều cao, cỡ chữ, khoảng cách")
        )
        quick.chunked(2).forEach { chunk ->
            val row = gridRow()
            chunk.forEachIndexed { index, item ->
                val click = when (item.second) {
                    "Trò chuyện AI" -> ({ render(Tab.AI) })
                    "Dịch" -> ({ openAiWorkspace("Dịch", "translate") })
                    "Ghi chú" -> ({ openNotes() })
                    else -> ({ render(Tab.KEYBOARD) })
                }
                row.addView(toolCard(item.first, item.second, item.third, click), cardParams(index == 0))
            }
            root.addView(row)
        }

        root.addView(section("Thiết kế 0.3"))
        root.addView(infoCard("Keyboard chỉ giữ phần cần gõ", "☰ + gợi ý + icon. Các màn hình Công cụ, AI, Ghi chú và Cài đặt được tách sang app chính để không làm bàn phím cao hoặc rối."))
        return scroll
    }

    private fun toolsPage(): View {
        val (scroll, root) = page("Công cụ", "Lưu trữ và thao tác nhanh")
        root.addView(section("Công cụ lưu trữ"))
        val tools = listOf(
            Tool("⚡", "Tin nhắn soạn sẵn", "Phản hồi dùng lại nhanh", { openNotes("Tin nhắn soạn sẵn") }),
            Tool("📝", "Ghi chú", "Lưu thông tin quan trọng", { openNotes() }),
            Tool("📋", "Bảng ghi tạm", "Xem và chèn clipboard hiện tại", { openClipboard() }),
            Tool("⌨", "Gõ tắt", "Tạo từ tắt để nhập nhanh", { openShortcuts() }),
            Tool("📖", "Từ điển cá nhân", "Kho từ riêng cho gợi ý", { toast("Từ điển cá nhân sẽ được nối vào engine gợi ý ở bản tiếp theo") }),
            Tool("🔐", "Kho bảo mật", "Mật khẩu/API key mã hóa", { toast("Kho bảo mật sẽ chỉ mở khi phần mã hóa + vân tay hoàn chỉnh") })
        )
        addToolGrid(root, tools)

        root.addView(section("Công cụ AI"))
        val aiTools = listOf(
            Tool("↩", "Trả lời", "Soạn phản hồi theo ngữ cảnh", { openAiWorkspace("Trả lời", "reply") }),
            Tool("✎", "Viết lại", "Diễn đạt lại rõ ràng hơn", { openAiWorkspace("Viết lại", "rewrite") }),
            Tool("🌐", "Dịch", "Dịch nhanh bằng model trên máy", { openAiWorkspace("Dịch", "translate") }),
            Tool("💬", "Comment FB", "Tạo bình luận từ nội dung tham chiếu", { openAiWorkspace("Comment Facebook", "comment") }),
            Tool("✉", "Email", "Soạn email chuyên nghiệp", { openAiWorkspace("Email", "email") }),
            Tool("≡", "Tóm tắt", "Rút gọn nội dung dài", { openAiWorkspace("Tóm tắt", "summary") })
        )
        addToolGrid(root, aiTools)
        return scroll
    }

    private fun aiPage(): View {
        val (scroll, root) = page("AI", "Chat và trợ lý theo tác vụ")

        val chat = card().apply {
            addView(TextView(this@MainActivity).apply {
                text = "✦  Trò chuyện với AI"
                textSize = 20f
                setTextColor(text)
                setTypeface(null, Typeface.BOLD)
            })
            addView(TextView(this@MainActivity).apply {
                text = if (prefs.gatewayUrl.isBlank()) "Chưa cấu hình AI Gateway. Dịch vẫn dùng được trên thiết bị." else "AI Gateway đã sẵn sàng."
                textSize = 13f
                setTextColor(muted)
                setPadding(0, dp(7), 0, dp(12))
            })
            addView(primaryButton("Mở Chat AI") { openAiWorkspace("Trò chuyện AI", "chat") })
        }
        root.addView(chat)

        root.addView(section("Hỗ trợ tác vụ"))
        val tasks = listOf(
            Tool("f", "Bài đăng mạng xã hội", "Viết nội dung social", { openAiWorkspace("Bài đăng mạng xã hội", "social") }),
            Tool("💭", "Bình luận", "Tạo comment theo ngữ cảnh", { openAiWorkspace("Bình luận", "comment") }),
            Tool("✎", "Viết lại", "Diễn đạt lại tự nhiên hơn", { openAiWorkspace("Viết lại", "rewrite") }),
            Tool("✉", "Email", "Soạn và trả lời email", { openAiWorkspace("Email", "email") }),
            Tool("🌐", "Dịch", "Dịch văn bản nhiều ngôn ngữ", { openAiWorkspace("Dịch", "translate") }),
            Tool("▶", "Ý tưởng video", "Gợi ý nội dung video", { openAiWorkspace("Ý tưởng video", "video") }),
            Tool("≡", "Tóm tắt", "Tóm tắt nội dung", { openAiWorkspace("Tóm tắt", "summary") }),
            Tool("↩", "Trả lời", "Soạn phản hồi nhanh", { openAiWorkspace("Trả lời", "reply") })
        )
        addToolGrid(root, tasks)
        return scroll
    }

    private fun keyboardPage(): View {
        val (scroll, root) = page("Bàn phím", "Tinh chỉnh sâu nhưng giữ giao diện gọn")
        root.addView(primaryButton("Bật Q AI Keyboard") {
            startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
        })
        root.addView(secondaryButton("Chọn bàn phím") {
            (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showInputMethodPicker()
        })

        root.addView(section("Kích thước & cảm giác gõ"))
        addSeekSetting(root, "Chiều cao bàn phím", 75, 120, prefs.keyboardHeightPercent, "%") { prefs.keyboardHeightPercent = it }
        addSeekSetting(root, "Cỡ chữ trên phím", 80, 125, prefs.keyTextPercent, "%") { prefs.keyTextPercent = it }
        addSeekSetting(root, "Khoảng cách giữa phím", 50, 150, prefs.gapPercent, "%") { prefs.gapPercent = it }
        root.addView(styledCheck("Rung nhẹ khi chạm phím", prefs.haptic) { prefs.haptic = it })
        root.addView(styledCheck("Hiện ký tự phụ @ # $ % - + ( ) …", prefs.showSymbols) { prefs.showSymbols = it })
        root.addView(infoCard("Hàng số", "Luôn hiển thị theo cấu hình đã chốt. Telex đơn giản ưu tiên không phá từ tiếng Anh; w đứng riêng vẫn là w."))

        root.addView(section("Cách gọi công cụ"))
        root.addView(infoCard("Thanh mặc định", "☰  |  gợi ý 1  |  gợi ý 2  |  gợi ý 3  |  ☺"))
        root.addView(infoCard("Khi bấm ☰", "Chỉ hiện icon Dịch, AI, Thư viện và Cài đặt. Chỉ Dịch/Typing mới mở thêm ô tham chiếu nhỏ."))
        return scroll
    }

    private fun settingsPage(): View {
        val (scroll, root) = page("Cài đặt", "Ngôn ngữ • AI • giao diện • bảo mật")

        root.addView(section("Giao diện"))
        val themeRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        listOf(0 to "Hệ thống", 1 to "Sáng", 2 to "Tối").forEach { (value, name) ->
            val b = Button(this).apply {
                text = name
                isAllCaps = false
                setOnClickListener {
                    uiPrefs.edit().putInt("theme_mode", value).apply()
                    recreate()
                }
            }
            themeRow.addView(b, LinearLayout.LayoutParams(0, dp(50), 1f).apply { setMargins(dp(3), 0, dp(3), 0) })
        }
        root.addView(themeRow)

        root.addView(section("Ngôn ngữ dịch"))
        val langLabels = arrayOf("Tiếng Anh", "日本語", "中文", "한국어")
        val langCodes = arrayOf("en", "ja", "zh", "ko")
        val spinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, langLabels)
            setSelection(langCodes.indexOf(prefs.targetLang).let { if (it < 0) 0 else it })
            onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                    prefs.targetLang = langCodes[position]
                }
                override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
            }
        }
        root.addView(spinner)

        root.addView(section("AI"))
        root.addView(infoCard("AI Gateway", "Q AI Keyboard không nhúng API key vào APK. Khi có Gateway, Chat/Viết lại/Comment/Email sẽ dùng Gateway; Dịch không cần Gateway."))
        val gateway = EditText(this).apply {
            hint = "https://.../api/q-keyboard"
            setHintTextColor(muted)
            setText(prefs.gatewayUrl)
            setTextColor(text)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            background = rounded(surface, 12f)
            setPadding(dp(14), dp(12), dp(14), dp(12))
        }
        root.addView(gateway, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(54)).apply { setMargins(0, dp(8), 0, dp(8)) })
        root.addView(primaryButton("Lưu AI Gateway") {
            prefs.gatewayUrl = gateway.text.toString()
            toast("Đã lưu AI Gateway")
        })

        root.addView(section("Nâng cao"))
        root.addView(infoCard("Bubble AI", "Thiết kế đã dành chỗ nhưng mặc định tắt. Sẽ chỉ bật khi overlay được làm ổn định để không che màn hình."))
        root.addView(infoCard("Google Sync", "Ghi chú, cấu hình và Vault sẽ được đồng bộ sau khi hoàn thiện mã hóa đầu-cuối và khôi phục thiết bị."))
        root.addView(infoCard("Bảo mật", "AI/Dịch không tự gửi toàn bộ nội dung gõ. Các tác vụ AI chỉ chạy khi người dùng chủ động gọi; trường mật khẩu/PIN được bảo vệ ở keyboard."))
        return scroll
    }

    private fun openAiWorkspace(title: String, mode: String) {
        navButtons.forEach { (_, v) -> v.setTextColor(muted) }
        host.removeAllViews()
        val (scroll, root) = page(title, when (mode) {
            "translate" -> "Nhập đoạn cần dịch; bản dịch sẽ hiển thị để kiểm tra trước khi copy."
            else -> "Dán hoặc nhập nội dung, sau đó gửi yêu cầu."
        })
        val back = TextView(this).apply {
            text = "‹  Quay lại"
            textSize = 16f
            setTextColor(blue)
            setPadding(0, 0, 0, dp(10))
            setOnClickListener { render(if (mode == "chat") Tab.AI else Tab.TOOLS) }
        }
        root.addView(back, 0)

        val input = EditText(this).apply {
            hint = if (mode == "translate") "Nhập văn bản tiếng Việt…" else "Nhập nội dung hoặc yêu cầu…"
            setHintTextColor(muted)
            setTextColor(text)
            gravity = Gravity.TOP
            minLines = 5
            background = rounded(surface, 16f)
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
        root.addView(input, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(150)).apply { setMargins(0, dp(8), 0, dp(12)) })

        val output = TextView(this).apply {
            text = "Kết quả sẽ hiện ở đây"
            textSize = 16f
            setTextColor(muted)
            gravity = Gravity.TOP
            background = rounded(surface, 16f)
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
        root.addView(output, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(170)))

        val actionRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val run = Button(this).apply {
            text = "➤"
            textSize = 22f
            isAllCaps = false
            setTextColor(Color.WHITE)
            background = rounded(blue, 14f)
            setOnClickListener {
                val value = input.text.toString().trim()
                if (value.isBlank()) { toast("Nhập nội dung trước"); return@setOnClickListener }
                output.setTextColor(muted)
                output.text = if (mode == "translate") "Đang dịch…" else "AI đang xử lý…"
                if (mode == "translate") {
                    translator.translate(value, "vi", prefs.targetLang) { result ->
                        runOnUiThread {
                            result.onSuccess { output.text = it; output.setTextColor(text) }
                                .onFailure { output.text = "Không dịch được: ${it.message}" }
                        }
                    }
                } else {
                    val instruction = instructionFor(mode)
                    ai.ask("$instruction\n\n$value") { result ->
                        runOnUiThread {
                            result.onSuccess { output.text = it; output.setTextColor(text) }
                                .onFailure { output.text = it.message ?: "AI chưa sẵn sàng" }
                        }
                    }
                }
            }
        }
        actionRow.addView(run, LinearLayout.LayoutParams(0, dp(52), 1f).apply { setMargins(0, dp(10), dp(5), 0) })
        val copy = Button(this).apply {
            text = "⧉"
            textSize = 20f
            isAllCaps = false
            setOnClickListener {
                val value = output.text.toString()
                if (value.isBlank() || value == "Kết quả sẽ hiện ở đây") return@setOnClickListener
                val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("Q AI", value))
                toast("Đã sao chép")
            }
        }
        actionRow.addView(copy, LinearLayout.LayoutParams(0, dp(52), 1f).apply { setMargins(dp(5), dp(10), 0, 0) })
        root.addView(actionRow)
        host.addView(scroll)
    }

    private fun instructionFor(mode: String): String = when (mode) {
        "rewrite" -> "Viết lại đoạn văn sau bằng tiếng Việt tự nhiên, rõ ràng, giữ nguyên ý chính."
        "comment" -> "Tạo một bình luận Facebook tự nhiên, phù hợp với nội dung sau. Không dài dòng."
        "reply" -> "Soạn một câu trả lời phù hợp, tự nhiên và hữu ích cho nội dung sau."
        "email" -> "Soạn email chuyên nghiệp dựa trên nội dung sau."
        "summary" -> "Tóm tắt nội dung sau ngắn gọn, giữ các ý quan trọng."
        "social" -> "Viết bài đăng mạng xã hội hấp dẫn, rõ ràng dựa trên nội dung sau."
        "video" -> "Đề xuất ý tưởng video ngắn dựa trên nội dung sau."
        else -> "Trả lời yêu cầu sau một cách rõ ràng và hữu ích."
    }

    private fun openNotes(title: String = "Ghi chú") {
        host.removeAllViews()
        val (scroll, root) = page(title, "Mỗi dòng là một mục; lưu xong có thể gọi lại từ bàn phím.")
        root.addView(TextView(this).apply {
            text = "‹  Quay lại Công cụ"
            textSize = 16f
            setTextColor(blue)
            setOnClickListener { render(Tab.TOOLS) }
        }, 0)
        val edit = EditText(this).apply {
            setText(prefs.notes)
            setTextColor(text)
            setHintTextColor(muted)
            hint = "Nhập ghi chú…"
            gravity = Gravity.TOP
            minLines = 12
            background = rounded(surface, 16f)
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
        root.addView(edit, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(340)).apply { setMargins(0, dp(14), 0, dp(12)) })
        root.addView(primaryButton("Lưu") {
            prefs.notes = edit.text.toString()
            toast("Đã lưu ghi chú")
        })
        host.addView(scroll)
    }

    private fun openShortcuts() {
        host.removeAllViews()
        val (scroll, root) = page("Gõ tắt", "Mỗi dòng: từ_tắt=nội_dung")
        root.addView(TextView(this).apply {
            text = "‹  Quay lại Công cụ"
            textSize = 16f
            setTextColor(blue)
            setOnClickListener { render(Tab.TOOLS) }
        }, 0)
        val edit = EditText(this).apply {
            setText(prefs.shortcuts)
            setTextColor(text)
            setHintTextColor(muted)
            hint = "qq=Quang Quý AI"
            gravity = Gravity.TOP
            minLines = 10
            background = rounded(surface, 16f)
            setPadding(dp(14), dp(14), dp(14), dp(14))
        }
        root.addView(edit, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(300)).apply { setMargins(0, dp(14), 0, dp(12)) })
        root.addView(primaryButton("Lưu") {
            prefs.shortcuts = edit.text.toString()
            toast("Đã lưu gõ tắt")
        })
        host.addView(scroll)
    }

    private fun openClipboard() {
        host.removeAllViews()
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val current = cm.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
        val (scroll, root) = page("Bảng ghi tạm", "Clipboard hiện tại trên thiết bị")
        root.addView(TextView(this).apply {
            text = "‹  Quay lại Công cụ"
            textSize = 16f
            setTextColor(blue)
            setOnClickListener { render(Tab.TOOLS) }
        }, 0)
        root.addView(infoCard("Nội dung", current.ifBlank { "Clipboard đang trống" }))
        root.addView(secondaryButton("Mở bàn phím để chèn") {
            (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showInputMethodPicker()
        })
        host.addView(scroll)
    }

    private data class Tool(val icon: String, val title: String, val sub: String, val click: () -> Unit)

    private fun addToolGrid(root: LinearLayout, items: List<Tool>) {
        items.chunked(2).forEach { chunk ->
            val row = gridRow()
            chunk.forEachIndexed { index, item ->
                row.addView(toolCard(item.icon, item.title, item.sub, item.click), cardParams(index == 0))
            }
            if (chunk.size == 1) row.addView(View(this), cardParams(false))
            root.addView(row)
        }
    }

    private fun gridRow() = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.TOP
    }

    private fun cardParams(left: Boolean) = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
        setMargins(if (left) 0 else dp(6), dp(5), if (left) dp(6) else 0, dp(5))
    }

    private fun toolCard(icon: String, title: String, sub: String, click: () -> Unit): View {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.START
            background = rounded(surface, 18f)
            setPadding(dp(14), dp(14), dp(14), dp(14))
            minimumHeight = dp(128)
            isClickable = true
            isFocusable = true
            setOnClickListener { click() }
            addView(TextView(this@MainActivity).apply {
                text = icon
                textSize = 27f
                setTextColor(blue)
            })
            addView(TextView(this@MainActivity).apply {
                text = title
                textSize = 17f
                setTextColor(text)
                setTypeface(null, Typeface.BOLD)
                setPadding(0, dp(7), 0, dp(4))
            })
            addView(TextView(this@MainActivity).apply {
                text = sub
                textSize = 13f
                setTextColor(muted)
            })
        }
    }

    private fun card() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = rounded(surface, 20f)
        setPadding(dp(18), dp(18), dp(18), dp(18))
    }

    private fun infoCard(title: String, body: String): View = card().apply {
        addView(TextView(this@MainActivity).apply {
            text = title
            textSize = 17f
            setTextColor(text)
            setTypeface(null, Typeface.BOLD)
        })
        addView(TextView(this@MainActivity).apply {
            text = body
            textSize = 14f
            setTextColor(muted)
            setPadding(0, dp(6), 0, 0)
        })
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            setMargins(0, dp(5), 0, dp(5))
        }
    }

    private fun primaryButton(label: String, click: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        textSize = 16f
        setTextColor(Color.WHITE)
        background = rounded(blue, 14f)
        setOnClickListener { click() }
    }

    private fun secondaryButton(label: String, click: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        textSize = 15f
        setTextColor(text)
        background = rounded(surface2, 14f)
        setOnClickListener { click() }
    }

    private fun styledCheck(label: String, checked: Boolean, change: (Boolean) -> Unit) = CheckBox(this).apply {
        text = label
        setTextColor(text)
        textSize = 15f
        isChecked = checked
        setPadding(0, dp(5), 0, dp(5))
        setOnCheckedChangeListener { _, value -> change(value) }
    }

    private fun section(value: String) = TextView(this).apply {
        text = value
        textSize = 19f
        setTextColor(text)
        setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(22), 0, dp(8))
    }

    private fun addSeekSetting(root: LinearLayout, title: String, min: Int, max: Int, value: Int, suffix: String, onChange: (Int) -> Unit) {
        val label = TextView(this).apply {
            text = "$title: $value$suffix"
            textSize = 15f
            setTextColor(text)
            setPadding(0, dp(10), 0, 0)
        }
        root.addView(label)
        root.addView(SeekBar(this).apply {
            this.max = max - min
            progress = value - min
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    val actual = min + progress
                    label.text = "$title: $actual$suffix"
                    if (fromUser) onChange(actual)
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit
                override fun onStopTrackingTouch(seekBar: SeekBar?) = Unit
            })
        })
    }

    private fun rounded(color: Int, radiusDp: Float): GradientDrawable = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radiusDp)
    }

    private fun toast(value: String) = Toast.makeText(this, value, Toast.LENGTH_SHORT).show()
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
    private fun dp(v: Float) = v * resources.displayMetrics.density
}
