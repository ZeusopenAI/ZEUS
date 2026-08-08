package ai.quangquy.qkeyboard

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast

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
            setPadding(dp(20), dp(24), dp(20), dp(32))
        }
        scroller.addView(root)

        root.addView(TextView(this).apply {
            text = "Q AI Keyboard"
            textSize = 28f
            setTextColor(Color.BLACK)
        })
        root.addView(TextView(this).apply {
            text = "Alpha 0.2 • Telex đơn giản • UI icon gọn • Dịch trực tiếp • AI theo đoạn được chọn"
            textSize = 14f
            setTextColor(Color.DKGRAY)
            setPadding(0, dp(6), 0, dp(18))
        })

        root.addView(Button(this).apply {
            text = "1. Bật Q AI Keyboard"
            setOnClickListener { startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS)) }
        })
        root.addView(Button(this).apply {
            text = "2. Chọn bàn phím"
            setOnClickListener {
                (getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager)
                    .showInputMethodPicker()
            }
        })

        root.addView(section("Kích thước & cảm giác gõ"))
        root.addView(TextView(this).apply {
            text = "Hàng số luôn hiển thị. Các thay đổi kích thước được áp dụng khi bàn phím mở lại."
            textSize = 13f
            setTextColor(Color.DKGRAY)
        })

        addSeekSetting(
            root = root,
            title = "Chiều cao bàn phím",
            min = 75,
            max = 120,
            value = prefs.keyboardHeightPercent,
            suffix = "%"
        ) { prefs.keyboardHeightPercent = it }

        addSeekSetting(
            root = root,
            title = "Cỡ chữ trên phím",
            min = 80,
            max = 125,
            value = prefs.keyTextPercent,
            suffix = "%"
        ) { prefs.keyTextPercent = it }

        addSeekSetting(
            root = root,
            title = "Khoảng cách giữa phím",
            min = 50,
            max = 150,
            value = prefs.gapPercent,
            suffix = "%"
        ) { prefs.gapPercent = it }

        root.addView(CheckBox(this).apply {
            text = "Rung nhẹ khi chạm phím"
            isChecked = prefs.haptic
            setOnCheckedChangeListener { _, checked -> prefs.haptic = checked }
        })
        root.addView(CheckBox(this).apply {
            text = "Hiện ký tự phụ @ # $ % - + ( ) … trên phím"
            isChecked = prefs.showSymbols
            setOnCheckedChangeListener { _, checked -> prefs.showSymbols = checked }
        })

        root.addView(section("Dịch thuật"))
        root.addView(TextView(this).apply {
            text = "Bản dịch xuất hiện trong một ô tham chiếu nhỏ. Các nút thao tác dùng icon để giữ bàn phím gọn."
            textSize = 13f
            setTextColor(Color.DKGRAY)
        })

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

        root.addView(section("AI theo ngữ cảnh"))
        root.addView(TextView(this).apply {
            text = "Chọn/copy một đoạn văn → bấm ✦ → chọn icon Dịch, Viết lại, Comment Facebook hoặc hỏi AI. Bản Alpha không tự gửi nội dung đang gõ lên AI."
            textSize = 13f
            setTextColor(Color.DKGRAY)
        })
        root.addView(label("AI Gateway URL"))
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

        root.addView(section("Ghi chú • Clipboard • Gõ tắt"))
        root.addView(TextView(this).apply {
            text = "Trên bàn phím chỉ hiện một icon thư viện. Bấm vào mới chọn Ghi chú, Clipboard hoặc Gõ tắt."
            textSize = 13f
            setTextColor(Color.DKGRAY)
        })

        root.addView(label("Ghi chú nhanh — mỗi dòng một ghi chú"))
        val notes = EditText(this).apply {
            minLines = 4
            setText(prefs.notes)
            gravity = Gravity.TOP
        }
        root.addView(notes)

        root.addView(label("Gõ tắt — mỗi dòng: từ_tắt=nội_dung"))
        val shortcuts = EditText(this).apply {
            minLines = 4
            setText(prefs.shortcuts)
            gravity = Gravity.TOP
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

        root.addView(section("Bảo mật"))
        root.addView(TextView(this).apply {
            text = "AI và Dịch tự tắt trong ô mật khẩu/PIN. Dịch dùng ML Kit và tải model khi dùng lần đầu. AI chỉ chạy khi anh chủ động bấm chức năng và đã cấu hình gateway."
            textSize = 13f
            setTextColor(Color.DKGRAY)
        })

        return scroller
    }

    private fun addSeekSetting(
        root: LinearLayout,
        title: String,
        min: Int,
        max: Int,
        value: Int,
        suffix: String,
        onChange: (Int) -> Unit
    ) {
        val valueLabel = TextView(this).apply {
            text = "$title: $value$suffix"
            textSize = 15f
            setTextColor(Color.BLACK)
            setPadding(0, dp(14), 0, 0)
        }
        root.addView(valueLabel)
        root.addView(SeekBar(this).apply {
            this.max = max - min
            progress = value - min
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                    val actual = min + progress
                    valueLabel.text = "$title: $actual$suffix"
                    if (fromUser) onChange(actual)
                }
                override fun onStartTrackingTouch(seekBar: SeekBar?) = Unit
                override fun onStopTrackingTouch(seekBar: SeekBar?) = Unit
            })
        })
    }

    private fun section(t: String) = TextView(this).apply {
        text = t
        textSize = 19f
        setTextColor(Color.rgb(30, 90, 180))
        setPadding(0, dp(24), 0, dp(7))
    }

    private fun label(t: String) = TextView(this).apply {
        text = t
        textSize = 15f
        setTextColor(Color.BLACK)
        setPadding(0, dp(16), 0, dp(5))
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()
}
