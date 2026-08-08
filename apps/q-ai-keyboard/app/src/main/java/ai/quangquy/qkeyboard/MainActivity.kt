package ai.quangquy.qkeyboard

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.*

class MainActivity : Activity() {
    private lateinit var prefs: AppPrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = AppPrefs(this)
        setContentView(buildUi())
    }

    private fun buildUi(): View {
        val scroller = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(28))
        }
        scroller.addView(root)

        root.addView(TextView(this).apply {
            text = "Q AI Keyboard"
            textSize = 28f
            setTextColor(Color.BLACK)
        })
        root.addView(TextView(this).apply {
            text = "Alpha 0.1 • Telex đơn giản • Dịch nhiều ngôn ngữ • AI Chat qua gateway"
            textSize = 15f
            setTextColor(Color.DKGRAY)
            setPadding(0, dp(6), 0, dp(18))
        })

        root.addView(Button(this).apply {
            text = "1. Bật Q AI Keyboard"
            setOnClickListener { startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS)) }
        })
        root.addView(Button(this).apply {
            text = "2. Chọn bàn phím"
            setOnClickListener { (getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager).showInputMethodPicker() }
        })

        root.addView(label("AI Gateway URL (OpenAI chạy ở server)"))
        val gateway = EditText(this).apply {
            hint = "https://.../api/q-keyboard"
            setText(prefs.gatewayUrl)
            inputType = android.text.InputType.TYPE_TEXT_VARIATION_URI
        }
        root.addView(gateway)
        root.addView(Button(this).apply {
            text = "Lưu AI Gateway"
            setOnClickListener {
                prefs.gatewayUrl = gateway.text.toString()
                Toast.makeText(this@MainActivity, "Đã lưu", Toast.LENGTH_SHORT).show()
            }
        })

        root.addView(label("Ngôn ngữ dịch mặc định"))
        val langLabels = arrayOf("Tiếng Anh", "日本語", "中文", "한국어")
        val langCodes = arrayOf("en", "ja", "zh", "ko")
        val spinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, langLabels)
            val idx = langCodes.indexOf(prefs.targetLang).let { if (it < 0) 0 else it }
            setSelection(idx)
            onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                    prefs.targetLang = langCodes[position]
                }
                override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
            }
        }
        root.addView(spinner)

        root.addView(label("Ghi chú nhanh (mỗi dòng một ghi chú)"))
        val notes = EditText(this).apply {
            minLines = 4
            setText(prefs.notes)
            gravity = android.view.Gravity.TOP
        }
        root.addView(notes)

        root.addView(label("Gõ tắt (mỗi dòng: từ_tắt=nội_dung)"))
        val shortcuts = EditText(this).apply {
            minLines = 4
            setText(prefs.shortcuts)
            gravity = android.view.Gravity.TOP
        }
        root.addView(shortcuts)
        root.addView(Button(this).apply {
            text = "Lưu ghi chú & gõ tắt"
            setOnClickListener {
                prefs.notes = notes.text.toString()
                prefs.shortcuts = shortcuts.text.toString()
                Toast.makeText(this@MainActivity, "Đã lưu", Toast.LENGTH_SHORT).show()
            }
        })

        root.addView(TextView(this).apply {
            text = "Bảo mật: bản Alpha không nhúng OpenAI API key vào APK. Dịch dùng ML Kit trên thiết bị; model ngôn ngữ sẽ tải khi dùng lần đầu. Google Sync và Vault mã hóa sẽ bổ sung ở bản tiếp theo."
            textSize = 13f
            setTextColor(Color.DKGRAY)
            setPadding(0, dp(20), 0, 0)
        })
        return scroller
    }

    private fun label(t: String) = TextView(this).apply {
        text = t
        textSize = 16f
        setTextColor(Color.BLACK)
        setPadding(0, dp(18), 0, dp(5))
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
}
