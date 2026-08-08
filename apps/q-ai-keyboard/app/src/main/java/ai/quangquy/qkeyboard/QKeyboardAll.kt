package ai.quangquy.qkeyboard

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.*
import android.inputmethodservice.InputMethodService
import android.view.MotionEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.TranslatorOptions
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread
import kotlin.math.floor
import org.json.JSONObject

/** Small Telex engine for the V1 alpha. It focuses on common Vietnamese typing. */
class TelexEngine {
    private var raw = StringBuilder()

    fun reset() { raw = StringBuilder() }
    fun currentRaw(): String = raw.toString()
    fun setRaw(value: String) { raw = StringBuilder(value) }

    fun push(c: Char): String {
        raw.append(c.lowercaseChar())
        return transform(raw.toString())
    }

    fun backspace(): String {
        if (raw.isNotEmpty()) raw.deleteCharAt(raw.length - 1)
        return transform(raw.toString())
    }

    private fun transform(input: String): String {
        if (input.isBlank()) return ""
        var s = input
        s = s.replace("dd", "đ")
            .replace("aa", "â")
            .replace("aw", "ă")
            .replace("ee", "ê")
            .replace("oo", "ô")
            .replace("ow", "ơ")
            .replace("uw", "ư")

        val tone = when (s.lastOrNull()) {
            's' -> 1
            'f' -> 2
            'r' -> 3
            'x' -> 4
            'j' -> 5
            else -> 0
        }
        if (tone != 0) s = applyTone(s.dropLast(1), tone)
        return s
    }

    private fun applyTone(word: String, tone: Int): String {
        if (word.isEmpty()) return word
        val vowelIndexes = word.indices.filter { isVowel(word[it]) }
        if (vowelIndexes.isEmpty()) return word
        val marked = vowelIndexes.lastOrNull { word[it] in "ăâêôơư" }
        val idx = marked ?: if (vowelIndexes.size >= 2) vowelIndexes[vowelIndexes.size - 2] else vowelIndexes.last()
        val chars = word.toCharArray()
        chars[idx] = toneChar(chars[idx], tone)
        return String(chars)
    }

    private fun isVowel(c: Char) = c in "aăâeêioôơuưy"

    private fun toneChar(c: Char, tone: Int): Char {
        val rows = mapOf(
            'a' to "aáàảãạ", 'ă' to "ăắằẳẵặ", 'â' to "âấầẩẫậ",
            'e' to "eéèẻẽẹ", 'ê' to "êếềểễệ", 'i' to "iíìỉĩị",
            'o' to "oóòỏõọ", 'ô' to "ôốồổỗộ", 'ơ' to "ơớờởỡợ",
            'u' to "uúùủũụ", 'ư' to "ưứừửữự", 'y' to "yýỳỷỹỵ"
        )
        return rows[c]?.getOrNull(tone) ?: c
    }
}

class TranslationManager(private val context: Context) {
    private fun code(tag: String): String = when (tag) {
        "vi" -> TranslateLanguage.VIETNAMESE
        "en" -> TranslateLanguage.ENGLISH
        "ja" -> TranslateLanguage.JAPANESE
        "zh" -> TranslateLanguage.CHINESE
        "ko" -> TranslateLanguage.KOREAN
        else -> TranslateLanguage.ENGLISH
    }

    fun translate(text: String, source: String, target: String, done: (Result<String>) -> Unit) {
        val options = TranslatorOptions.Builder()
            .setSourceLanguage(code(source))
            .setTargetLanguage(code(target))
            .build()
        val translator = Translation.getClient(options)
        val conditions = DownloadConditions.Builder().build()
        translator.downloadModelIfNeeded(conditions)
            .addOnSuccessListener {
                translator.translate(text)
                    .addOnSuccessListener { out -> translator.close(); done(Result.success(out)) }
                    .addOnFailureListener { e -> translator.close(); done(Result.failure(e)) }
            }
            .addOnFailureListener { e -> translator.close(); done(Result.failure(e)) }
    }
}

class AppPrefs(context: Context) {
    private val p = context.getSharedPreferences("q_keyboard", Context.MODE_PRIVATE)

    var gatewayUrl: String
        get() = p.getString("gateway_url", "") ?: ""
        set(v) = p.edit().putString("gateway_url", v.trim()).apply()

    var sourceLang: String
        get() = p.getString("source_lang", "vi") ?: "vi"
        set(v) = p.edit().putString("source_lang", v).apply()

    var targetLang: String
        get() = p.getString("target_lang", "en") ?: "en"
        set(v) = p.edit().putString("target_lang", v).apply()

    var notes: String
        get() = p.getString("notes", "Quang Quý AI\nChúc mừng sinh nhật\nChúc ngủ ngon") ?: ""
        set(v) = p.edit().putString("notes", v).apply()

    var shortcuts: String
        get() = p.getString("shortcuts", "qq=Quang Quý AI\nmail=Email của tôi") ?: ""
        set(v) = p.edit().putString("shortcuts", v).apply()
}

/**
 * Calls a user-controlled server-side gateway. No OpenAI API key is embedded in the APK.
 * Gateway contract: POST {"action":"chat","text":"..."} -> {"text":"..."}
 */
class AiGateway(private val prefs: AppPrefs) {
    fun ask(text: String, done: (Result<String>) -> Unit) {
        val endpoint = prefs.gatewayUrl
        if (endpoint.isBlank()) {
            done(Result.failure(IllegalStateException("Chưa cấu hình AI Gateway trong ứng dụng Q AI Keyboard.")))
            return
        }
        thread {
            runCatching {
                val conn = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 10000
                    readTimeout = 30000
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                }
                val body = JSONObject().put("action", "chat").put("text", text).toString()
                conn.outputStream.use { it.write(body.toByteArray()) }
                val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
                val payload = stream.bufferedReader().use { it.readText() }
                if (conn.responseCode !in 200..299) error("AI Gateway HTTP ${conn.responseCode}: $payload")
                JSONObject(payload).optString("text").ifBlank { error("Gateway không trả về trường text") }
            }.also(done)
        }
    }
}

class QKeyboardView(context: Context, private val listener: Listener) : View(context) {
    interface Listener {
        fun onKey(text: String)
        fun onBackspace()
        fun onEnter()
        fun onSpace()
        fun onMenu()
        fun onTool(tool: String)
        fun onSuggestion(text: String)
    }

    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val keyBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }
    private val panelBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(240, 242, 248) }
    private var menuOpen = false
    var suggestions: List<String> = listOf("anh", "em", "không")
    private var keys = mutableListOf<Key>()

    data class Key(val rect: RectF, val value: String, val label: String = value, val small: String? = null)

    fun setMenuOpen(open: Boolean) { menuOpen = open; invalidate() }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        val h = (390 * resources.displayMetrics.density).toInt()
        setMeasuredDimension(w, h)
    }

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        c.drawColor(panelBg.color)
        keys.clear()
        val d = resources.displayMetrics.density
        val toolbarH = 48f * d
        if (menuOpen) drawTools(c) else drawSuggestionBar(c)

        val rows = listOf(
            listOf("1","2","3","4","5","6","7","8","9","0"),
            listOf("q","w","e","r","t","y","u","i","o","p"),
            listOf("a","s","d","f","g","h","j","k","l"),
            listOf("⇧","z","x","c","v","b","n","m","⌫")
        )
        val secondary = mapOf(
            "a" to "@", "s" to "#", "d" to "\$", "f" to "%", "g" to "-", "h" to "+", "j" to "(", "k" to ")", "l" to "'",
            "z" to "*", "x" to "\"", "c" to "'", "v" to ":", "b" to ";", "n" to "!", "m" to "?"
        )
        val gap = 4f * d
        val side = 6f * d
        val rowH = 62f * d
        var y = toolbarH + 4f*d
        for ((ri,row) in rows.withIndex()) {
            val indent = if (ri == 2) 26f*d else 0f
            val available = width - side*2 - indent*2 - gap*(row.size-1)
            val kw = available / row.size
            var x = side + indent
            for (v in row) {
                val r = RectF(x, y, x+kw, y+rowH-gap)
                drawKey(c, r, v.uppercase(), secondary[v])
                keys += Key(r, v, v, secondary[v])
                x += kw + gap
            }
            y += rowH
        }

        val bottom = listOf("?123","VI",",","SPACE","⌨",".","↵")
        val weights = listOf(1.15f,0.8f,0.65f,3.2f,0.75f,0.65f,1.1f)
        val totalWeight = weights.sum()
        val available = width - side*2 - gap*(bottom.size-1)
        var x = side
        for (i in bottom.indices) {
            val kw = available * weights[i]/totalWeight
            val r = RectF(x,y,x+kw,y+rowH-gap)
            val label = if(bottom[i]=="SPACE") "Q AI Keyboard" else bottom[i]
            drawKey(c,r,label,null)
            keys += Key(r,bottom[i],label)
            x += kw+gap
        }
    }

    private fun drawSuggestionBar(c: Canvas) {
        val d = resources.displayMetrics.density
        p.color = Color.rgb(40,40,45)
        p.textSize = 24f*d
        p.textAlign = Paint.Align.CENTER
        c.drawText("☰", 32f*d, 32f*d, p)
        val start = 70f*d
        val usable = width-start-48f*d
        val sw = usable / 3f
        suggestions.take(3).forEachIndexed { i,s -> c.drawText(s, start+sw*(i+.5f),32f*d,p) }
        c.drawText("☺", width-24f*d,32f*d,p)
    }

    private fun drawTools(c: Canvas) {
        val d = resources.displayMetrics.density
        val tools = listOf("←","Dịch","AI Chat","Ghi chú","Clipboard","Gõ tắt","Cài đặt")
        p.textAlign = Paint.Align.CENTER
        p.textSize = 13f*d
        p.color = Color.rgb(35,35,40)
        val w = width/tools.size.toFloat()
        tools.forEachIndexed { i,t -> c.drawText(t, w*(i+.5f), 30f*d, p) }
    }

    private fun drawKey(c: Canvas, r: RectF, label: String, small: String?) {
        val d = resources.displayMetrics.density
        c.drawRoundRect(r, 8f*d, 8f*d, keyBg)
        p.color = Color.BLACK
        p.textAlign = Paint.Align.CENTER
        p.textSize = if(label.length>2) 15f*d else 26f*d
        c.drawText(label, r.centerX(), r.centerY()+8f*d, p)
        if (small != null) {
            p.textSize = 11f*d
            p.color = Color.DKGRAY
            p.textAlign = Paint.Align.CENTER
            c.drawText(small, r.centerX()+r.width()*0.22f, r.top+13f*d, p)
        }
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.action != MotionEvent.ACTION_UP) return true
        val d = resources.displayMetrics.density
        val toolbarH = 48f*d
        if (e.y < toolbarH) {
            if (!menuOpen) {
                if (e.x < 64f*d) listener.onMenu()
                else {
                    val start = 70f*d
                    val usable = width-start-48f*d
                    val idx = floor((e.x-start)/(usable/3f)).toInt()
                    suggestions.getOrNull(idx)?.let { listener.onSuggestion(it) }
                }
            } else {
                val tools = listOf("back","translate","ai","notes","clipboard","shortcuts","settings")
                val idx = floor(e.x/(width/tools.size.toFloat())).toInt().coerceIn(0,tools.lastIndex)
                listener.onTool(tools[idx])
            }
            return true
        }
        val key = keys.firstOrNull { it.rect.contains(e.x,e.y) } ?: return true
        when(key.value) {
            "⌫" -> listener.onBackspace()
            "↵" -> listener.onEnter()
            "SPACE" -> listener.onSpace()
            "⇧" -> Unit
            "?123","VI","⌨" -> Unit
            else -> listener.onKey(key.value)
        }
        return true
    }
}

class QKeyboardService : InputMethodService(), QKeyboardView.Listener {
    private lateinit var keyboard: QKeyboardView
    private lateinit var prefs: AppPrefs
    private lateinit var translator: TranslationManager
    private lateinit var ai: AiGateway
    private val telex = TelexEngine()
    private var composing = ""
    private var aiCapture = false
    private var aiPrompt = StringBuilder()
    private var translatedCandidate: String? = null

    override fun onCreate() {
        super.onCreate()
        prefs = AppPrefs(this)
        translator = TranslationManager(this)
        ai = AiGateway(prefs)
    }

    override fun onCreateInputView(): View {
        keyboard = QKeyboardView(this, this)
        return keyboard
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        super.onStartInput(attribute, restarting)
        telex.reset()
        composing = ""
        aiCapture = false
        aiPrompt.clear()
        translatedCandidate = null
        if (::keyboard.isInitialized) keyboard.suggestions = listOf("anh","em","không")
    }

    override fun onKey(text: String) {
        if (aiCapture) {
            aiPrompt.append(text)
            keyboard.suggestions = listOf(aiPrompt.toString().takeLast(20), "Gửi AI", "Hủy")
            keyboard.invalidate()
            return
        }
        if (text.length == 1 && text[0].isLetter()) {
            composing = telex.push(text[0])
            currentInputConnection.setComposingText(composing, 1)
            keyboard.suggestions = suggest(composing)
            keyboard.invalidate()
        } else {
            commitComposing()
            currentInputConnection.commitText(text,1)
        }
    }

    override fun onBackspace() {
        if (aiCapture && aiPrompt.isNotEmpty()) {
            aiPrompt.deleteCharAt(aiPrompt.length-1)
            keyboard.suggestions = listOf(aiPrompt.toString().takeLast(20),"Gửi AI","Hủy")
            keyboard.invalidate()
            return
        }
        if (telex.currentRaw().isNotEmpty()) {
            composing = telex.backspace()
            currentInputConnection.setComposingText(composing,1)
        } else currentInputConnection.deleteSurroundingText(1,0)
    }

    override fun onSpace() {
        if (aiCapture) {
            aiPrompt.append(' ')
            keyboard.suggestions = listOf(aiPrompt.toString().takeLast(20),"Gửi AI","Hủy")
            keyboard.invalidate()
            return
        }
        val expanded = expandShortcut(composing)
        if (expanded != null) currentInputConnection.setComposingText(expanded,1)
        commitComposing()
        currentInputConnection.commitText(" ",1)
    }

    override fun onEnter() {
        commitComposing()
        currentInputConnection.sendKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, android.view.KeyEvent.KEYCODE_ENTER))
        currentInputConnection.sendKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, android.view.KeyEvent.KEYCODE_ENTER))
    }

    override fun onMenu() { keyboard.setMenuOpen(true) }

    override fun onTool(tool: String) {
        when(tool) {
            "back" -> keyboard.setMenuOpen(false)
            "translate" -> {
                keyboard.setMenuOpen(false)
                translateCurrentSentence()
            }
            "ai" -> {
                keyboard.setMenuOpen(false)
                aiCapture = true
                aiPrompt.clear()
                keyboard.suggestions = listOf("Nhập prompt…","Gửi AI","Hủy")
                keyboard.invalidate()
            }
            "notes" -> {
                keyboard.setMenuOpen(false)
                keyboard.suggestions = prefs.notes.lines().filter { it.isNotBlank() }.take(3).ifEmpty { listOf("Chưa có ghi chú") }
                keyboard.invalidate()
            }
            "clipboard" -> {
                keyboard.setMenuOpen(false)
                pasteClipboard()
            }
            "shortcuts" -> {
                keyboard.setMenuOpen(false)
                keyboard.suggestions = prefs.shortcuts.lines().mapNotNull { it.substringBefore('=',"").takeIf(String::isNotBlank) }.take(3).ifEmpty { listOf("Chưa có gõ tắt") }
                keyboard.invalidate()
            }
            "settings" -> {
                keyboard.setMenuOpen(false)
                val i = Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(i)
            }
        }
    }

    override fun onSuggestion(text: String) {
        if (text == "Gửi AI" && aiCapture) {
            sendAi()
            return
        }
        if (text == "Hủy" && aiCapture) {
            aiCapture=false
            aiPrompt.clear()
            keyboard.suggestions=listOf("anh","em","không")
            keyboard.invalidate()
            return
        }
        translatedCandidate?.let { tr ->
            if (text == tr) {
                currentInputConnection.commitText(tr,1)
                translatedCandidate=null
                keyboard.suggestions=listOf("anh","em","không")
                keyboard.invalidate()
                return
            }
        }
        if (prefs.notes.lines().contains(text)) {
            commitComposing()
            currentInputConnection.commitText(text,1)
            return
        }
        commitComposing()
        currentInputConnection.commitText(text + " ",1)
    }

    private fun translateCurrentSentence() {
        commitComposing()
        val before = currentInputConnection.getTextBeforeCursor(500,0)?.toString()?.trim().orEmpty()
        val sentence = before.substringAfterLast('\n').substringAfterLast('.').trim()
        if (sentence.isBlank()) {
            toast("Gõ câu cần dịch trước, rồi mở ☰ → Dịch")
            return
        }
        keyboard.suggestions = listOf("Đang dịch…", langLabel(prefs.sourceLang), langLabel(prefs.targetLang))
        keyboard.invalidate()
        translator.translate(sentence,prefs.sourceLang,prefs.targetLang) { result ->
            keyboard.post {
                result.onSuccess { out ->
                    translatedCandidate = out
                    keyboard.suggestions=listOf(out,"VI↔${prefs.targetLang.uppercase()}","Chạm câu để chèn")
                    keyboard.invalidate()
                }.onFailure {
                    toast("Không dịch được: ${it.message}")
                    keyboard.suggestions=listOf("anh","em","không")
                    keyboard.invalidate()
                }
            }
        }
    }

    private fun sendAi() {
        val prompt = aiPrompt.toString().trim()
        if (prompt.isBlank()) {
            toast("Nhập câu hỏi AI trước")
            return
        }
        keyboard.suggestions=listOf("AI đang trả lời…","","")
        keyboard.invalidate()
        ai.ask(prompt) { result ->
            keyboard.post {
                aiCapture=false
                aiPrompt.clear()
                result.onSuccess { out ->
                    translatedCandidate=out
                    keyboard.suggestions=listOf(out,"Chạm để chèn","AI")
                    keyboard.invalidate()
                }.onFailure {
                    toast(it.message ?: "AI lỗi")
                    keyboard.suggestions=listOf("anh","em","không")
                    keyboard.invalidate()
                }
            }
        }
    }

    private fun pasteClipboard() {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val text = cm.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString()
        if (text.isNullOrBlank()) toast("Clipboard đang trống")
        else {
            commitComposing()
            currentInputConnection.commitText(text,1)
        }
    }

    private fun expandShortcut(value: String): String? {
        if (value.isBlank()) return null
        return prefs.shortcuts.lines().mapNotNull { line ->
            val idx=line.indexOf('=')
            if(idx<=0) null else line.substring(0,idx).trim() to line.substring(idx+1)
        }.firstOrNull { it.first == value }?.second
    }

    private fun suggest(v: String): List<String> = when {
        v.startsWith("a") -> listOf(v,"anh","ạ")
        v.startsWith("e") -> listOf(v,"em","em nhé")
        v.startsWith("k") -> listOf(v,"không","khi")
        else -> listOf(v,"anh","em")
    }

    private fun commitComposing() {
        if (telex.currentRaw().isNotEmpty()) {
            currentInputConnection.finishComposingText()
            telex.reset()
            composing=""
        }
    }

    private fun toast(s:String)=Toast.makeText(this,s,Toast.LENGTH_SHORT).show()
    private fun langLabel(code:String)=when(code){"vi"->"Tiếng Việt";"en"->"Tiếng Anh";"ja"->"日本語";"zh"->"中文";"ko"->"한국어";else->code}
}
