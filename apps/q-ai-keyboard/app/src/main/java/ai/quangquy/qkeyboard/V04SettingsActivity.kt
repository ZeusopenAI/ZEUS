package ai.quangquy.qkeyboard

import android.app.Activity
import android.content.Intent
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
import android.widget.AdapterView
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

class V04SettingsActivity : Activity() {
    private lateinit var prefs: V04Prefs
    private lateinit var learning: V04LearningStore
    private val bg = Color.rgb(246,247,250)
    private val surface = Color.WHITE
    private val fg = Color.rgb(30,31,35)
    private val muted = Color.rgb(100,104,115)
    private val accent = Color.rgb(65,123,230)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = V04Prefs(this); learning = V04LearningStore(this)
        window.statusBarColor = bg; window.navigationBarColor = bg; window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
        setContentView(page())
    }

    private fun page(): View {
        val scroll = ScrollView(this).apply { setBackgroundColor(bg) }
        val root = LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(dp(18),dp(18),dp(18),dp(32)) }
        scroll.addView(root)
        root.addView(TextView(this).apply { text="Q Ai Key v04"; textSize=28f; setTextColor(fg); setTypeface(null,Typeface.BOLD); gravity=Gravity.CENTER_HORIZONTAL })
        root.addView(TextView(this).apply { text="Bàn phím Việt gọn • tự học • Dịch + AI"; textSize=14f; setTextColor(muted); gravity=Gravity.CENTER_HORIZONTAL; setPadding(0,dp(5),0,dp(16)) })

        root.addView(card().apply {
            addView(primary("Bật Q Ai Key v04") { startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS)) })
            addView(space(8)); addView(secondary("Chọn bàn phím") { (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).showInputMethodPicker() })
        })

        root.addView(section("Test bàn phím ngay trong app")); root.addView(card().apply {
            addView(info("Chạm vào ô bên dưới để gọi bàn phím. Khung này dùng để test Telex, gợi ý từ, emoji, Dịch và AI mà không cần mở app khác."))
            val test = EditText(this@V04SettingsActivity).apply {
                hint = "Gõ thử ở đây…\nVí dụ: tieengs vieetj, chúc mừng sinh nhật…"
                setHintTextColor(muted)
                setTextColor(fg)
                textSize = 17f
                gravity = Gravity.TOP or Gravity.START
                minLines = 5
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                background = round(Color.rgb(239,241,246),14)
                setPadding(dp(14),dp(14),dp(14),dp(14))
            }
            addView(test, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(150)).apply { setMargins(0,dp(10),0,dp(10)) })
            addView(primary("Mở Q Ai Key để test") {
                test.requestFocus()
                val imm = getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager
                imm.showSoftInput(test, InputMethodManager.SHOW_IMPLICIT)
            })
            addView(space(8))
            val status = TextView(this@V04SettingsActivity).apply {
                textSize=13f; setTextColor(muted); setPadding(dp(2),dp(8),dp(2),dp(2))
                text = imeStatus()
            }
            addView(status)
            addView(space(6))
            addView(secondary("Kiểm tra lại trạng thái bàn phím") { status.text = imeStatus() })
        })

        root.addView(section("Gợi ý & tự học")); root.addView(card().apply {
            addView(label("Số từ gợi ý")); val sp=spinner(listOf("3 từ — mặc định","4 từ","5 từ"),prefs.suggestionCount-3); addView(sp); sp.onItemSelectedListener=Selected{prefs.suggestionCount=it+3}
            addView(space(8)); addView(check("Gợi ý 1 emoji theo ngữ cảnh",prefs.contextualEmoji){prefs.contextualEmoji=it})
            addView(check("Tự học cách gõ trên máy",prefs.personalLearning){prefs.personalLearning=it})
            addView(check("Dùng từ điển chung mở rộng",prefs.commonDictionary){prefs.commonDictionary=it})
            addView(space(8)); addView(secondary("Xóa dữ liệu đã học") { learning.reset(); toast("Đã xóa dữ liệu học trên máy") })
            addView(info("Từ điển chung mở rộng vốn từ cho mọi cài đặt; phần tự học cá nhân lưu cục bộ và không học trong ô mật khẩu/PIN."))
        })

        root.addView(section("Bố cục & cảm giác gõ")); root.addView(card().apply {
            addView(secondary("Preset gọn kiểu LabanKey") { prefs.compactPreset(); toast("Đã áp dụng preset gọn"); recreate() }); addView(space(8))
            seek(this,"Chiều cao bàn phím",75,120,prefs.keyboardHeight,"%"){prefs.keyboardHeight=it}
            seek(this,"Cỡ chữ phím",80,125,prefs.keyText,"%"){prefs.keyText=it}
            seek(this,"Khoảng cách phím",50,150,prefs.gap,"%"){prefs.gap=it}
            seek(this,"Cỡ chữ gợi ý",80,125,prefs.suggestionText,"%"){prefs.suggestionText=it}
            seek(this,"Kích thước emoji",80,130,prefs.emojiSize,"%"){prefs.emojiSize=it}
            addView(check("Rung nhẹ khi gõ",prefs.haptic){prefs.haptic=it}); addView(check("Hiện ký tự phụ @ # $ % - + ( )…",prefs.showSymbols){prefs.showSymbols=it})
            addView(info("Mặc định 3 từ. Khi chọn 4–5 từ, vuốt ngang thanh gợi ý. Cụm dài tự xuống tối đa 2 dòng; hàng số luôn hiển thị."))
        })

        root.addView(section("Dịch")); root.addView(card().apply {
            val names=listOf("Tiếng Việt","English","日本語","中文","한국어"); val codes=listOf("vi","en","ja","zh","ko")
            addView(label("Ngôn ngữ nguồn")); val src=spinner(names,codes.indexOf(prefs.sourceLang).coerceAtLeast(0)); addView(src); src.onItemSelectedListener=Selected{prefs.sourceLang=codes[it]}
            addView(space(8)); addView(label("Ngôn ngữ đích")); val dst=spinner(names,codes.indexOf(prefs.targetLang).let{if(it<0)1 else it}); addView(dst); dst.onItemSelectedListener=Selected{prefs.targetLang=codes[it]}
            addView(info("Bấm 🌐 trong menu ☰ để dịch đoạn đang chọn hoặc câu ngay trước con trỏ. Kết quả có icon Chèn / Thay thế / Copy."))
        })

        root.addView(section("Chat AI")); root.addView(card().apply {
            addView(info("AI chỉ được gọi khi bấm AI; không nhúng API key cố định trong APK.")); addView(label("AI Gateway URL (tùy chọn)"))
            val url=EditText(this@V04SettingsActivity).apply { setText(prefs.gatewayUrl); hint="https://..."; inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI; textSize=14f; setPadding(dp(12),dp(10),dp(12),dp(10)); background=round(Color.rgb(239,241,246),12) }
            addView(url); addView(space(8)); addView(primary("Lưu AI Gateway") { prefs.gatewayUrl=url.text.toString(); toast("Đã lưu") })
        })

        root.addView(section("Cách dùng")); root.addView(card().apply { addView(info("Thanh chính: ☰ + 3/4/5 từ gợi ý + 1 emoji theo ngữ cảnh. Bấm ☰ để vuốt qua 🌐 Dịch, AI, Clipboard, Emoji, Cài đặt. Phím ☺ mở bộ emoji nhiều nhóm.")) })
        return scroll
    }

    private fun imeStatus(): String {
        val def = Settings.Secure.getString(contentResolver, Settings.Secure.DEFAULT_INPUT_METHOD).orEmpty()
        val enabled = Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_INPUT_METHODS).orEmpty()
        val isDefault = def.contains(packageName, ignoreCase = true)
        val isEnabled = enabled.contains(packageName, ignoreCase = true)
        return "Trạng thái: ${if (isEnabled) "ĐÃ BẬT" else "CHƯA BẬT"} • ${if (isDefault) "ĐANG LÀ BÀN PHÍM MẶC ĐỊNH" else "CHƯA ĐƯỢC CHỌN LÀM MẶC ĐỊNH"}\nIME hiện tại: ${def.ifBlank { "Không đọc được" }}"
    }

    private fun section(s:String)=TextView(this).apply{text=s;textSize=18f;setTextColor(fg);setTypeface(null,Typeface.BOLD);setPadding(dp(2),dp(20),dp(2),dp(8))}
    private fun card()=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(14),dp(14),dp(14),dp(14));background=round(surface,16)}
    private fun label(s:String)=TextView(this).apply{text=s;textSize=14f;setTextColor(fg);setTypeface(null,Typeface.BOLD);setPadding(0,dp(4),0,dp(6))}
    private fun info(s:String)=TextView(this).apply{text=s;textSize=13f;setTextColor(muted);setPadding(0,dp(10),0,dp(2))}
    private fun check(s:String,v:Boolean,on:(Boolean)->Unit)=CheckBox(this).apply{text=s;isChecked=v;textSize=14f;setTextColor(fg);setOnCheckedChangeListener{_,b->on(b)}}
    private fun primary(s:String,on:()->Unit)=Button(this).apply{text=s;isAllCaps=false;textSize=15f;setTextColor(Color.WHITE);background=round(accent,12);setOnClickListener{on()}}
    private fun secondary(s:String,on:()->Unit)=Button(this).apply{text=s;isAllCaps=false;textSize=14f;setTextColor(fg);background=round(Color.rgb(235,238,244),12);setOnClickListener{on()}}
    private fun spinner(items:List<String>,sel:Int)=Spinner(this).apply{adapter=ArrayAdapter(this@V04SettingsActivity,android.R.layout.simple_spinner_dropdown_item,items);setSelection(sel.coerceIn(0,items.lastIndex));background=round(Color.rgb(239,241,246),12);setPadding(dp(10),dp(4),dp(10),dp(4))}
    private fun seek(parent:LinearLayout,title:String,min:Int,max:Int,current:Int,suffix:String,on:(Int)->Unit){val row=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL};val name=TextView(this).apply{text=title;textSize=14f;setTextColor(fg)};val value=TextView(this).apply{text="$current$suffix";textSize=13f;setTextColor(muted);gravity=Gravity.END};row.addView(name,LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1f));row.addView(value,LinearLayout.LayoutParams(dp(64),ViewGroup.LayoutParams.WRAP_CONTENT));parent.addView(row);parent.addView(SeekBar(this).apply{this.max=max-min;progress=current.coerceIn(min,max)-min;setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener{override fun onProgressChanged(s:SeekBar?,p:Int,f:Boolean){val v=min+p;value.text="$v$suffix";on(v)};override fun onStartTrackingTouch(s:SeekBar?){};override fun onStopTrackingTouch(s:SeekBar?){}})});parent.addView(space(4))}
    private fun space(h:Int)=View(this).apply{layoutParams=LinearLayout.LayoutParams(1,dp(h))}
    private fun round(c:Int,r:Int)=GradientDrawable().apply{setColor(c);cornerRadius=dp(r).toFloat()}
    private fun dp(v:Int)=(v*resources.displayMetrics.density+.5f).toInt()
    private fun toast(s:String)=Toast.makeText(this,s,Toast.LENGTH_SHORT).show()
    private class Selected(val f:(Int)->Unit):AdapterView.OnItemSelectedListener{override fun onItemSelected(p:AdapterView<*>?,v:View?,pos:Int,id:Long)=f(pos);override fun onNothingSelected(p:AdapterView<*>?){}}
}
