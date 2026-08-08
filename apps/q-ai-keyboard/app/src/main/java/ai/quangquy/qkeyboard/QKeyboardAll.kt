package ai.quangquy.qkeyboard

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.inputmethodservice.InputMethodService
import android.text.InputType
import android.view.HapticFeedbackConstants
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.TranslatorOptions
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread
import kotlin.math.floor

/**
 * Simple Telex mode for daily Vietnamese typing.
 * Important: standalone "w" stays "w". Shape keys only apply in Telex pairs
 * such as aw/ow/uw, so the engine never maps w -> ư by itself.
 */
class TelexEngine {
    private var raw = StringBuilder()

    fun reset() { raw = StringBuilder() }
    fun currentRaw(): String = raw.toString()

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
        val out = StringBuilder()
        var tone = 0

        input.forEach { ch ->
            when {
                ch == 's' && out.any { isVowel(it) } -> tone = 1
                ch == 'f' && out.any { isVowel(it) } -> tone = 2
                ch == 'r' && out.any { isVowel(it) } -> tone = 3
                ch == 'x' && out.any { isVowel(it) } -> tone = 4
                ch == 'j' && out.any { isVowel(it) } -> tone = 5
                ch == 'z' && out.any { hasVietnameseMark(it) } -> {
                    for (i in out.indices) out.setCharAt(i, baseChar(out[i]))
                    tone = 0
                }
                ch == 'd' && out.lastOrNull() == 'd' -> out.setCharAt(out.length - 1, 'đ')
                ch == 'a' && out.lastOrNull() == 'a' -> out.setCharAt(out.length - 1, 'â')
                ch == 'e' && out.lastOrNull() == 'e' -> out.setCharAt(out.length - 1, 'ê')
                ch == 'o' && out.lastOrNull() == 'o' -> out.setCharAt(out.length - 1, 'ô')
                ch == 'w' && out.lastOrNull() == 'a' -> out.setCharAt(out.length - 1, 'ă')
                ch == 'w' && out.lastOrNull() == 'o' -> out.setCharAt(out.length - 1, 'ơ')
                ch == 'w' && out.lastOrNull() == 'u' -> out.setCharAt(out.length - 1, 'ư')
                else -> out.append(ch)
            }
        }

        return if (tone == 0) out.toString() else applyTone(out.toString(), tone)
    }

    private fun applyTone(word: String, tone: Int): String {
        if (word.isEmpty()) return word
        val indexes = word.indices.filter { isVowel(word[it]) }
        if (indexes.isEmpty()) return word

        val preferred = indexes.lastOrNull { word[it] in "ăâêôơư" }
        val idx = preferred ?: when {
            indexes.size == 1 -> indexes.first()
            word.endsWith("i") || word.endsWith("y") || word.endsWith("u") -> indexes[indexes.size - 2]
            else -> indexes.last()
        }
        val chars = word.toCharArray()
        chars[idx] = toneChar(chars[idx], tone)
        return String(chars)
    }

    private fun isVowel(c: Char) = baseChar(c) in "aăâeêioôơuưy"

    private fun hasVietnameseMark(c: Char): Boolean = c != baseChar(c)

    private fun baseChar(c: Char): Char {
        val groups = listOf(
            "aáàảãạ", "ăắằẳẵặ", "âấầẩẫậ", "eéèẻẽẹ", "êếềểễệ",
            "iíìỉĩị", "oóòỏõọ", "ôốồổỗộ", "ơớờởỡợ", "uúùủũụ",
            "ưứừửữự", "yýỳỷỹỵ"
        )
        groups.forEach { g -> if (c in g) return g[0] }
        return if (c == 'đ') 'd' else c
    }

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
        translator.downloadModelIfNeeded(DownloadConditions.Builder().build())
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

    var keyboardHeightPercent: Int
        get() = p.getInt("keyboard_height", 100)
        set(v) = p.edit().putInt("keyboard_height", v.coerceIn(75, 120)).apply()

    var keyTextPercent: Int
        get() = p.getInt("key_text", 100)
        set(v) = p.edit().putInt("key_text", v.coerceIn(80, 125)).apply()

    var gapPercent: Int
        get() = p.getInt("key_gap", 80)
        set(v) = p.edit().putInt("key_gap", v.coerceIn(50, 150)).apply()

    var haptic: Boolean
        get() = p.getBoolean("haptic", true)
        set(v) = p.edit().putBoolean("haptic", v).apply()

    var showSymbols: Boolean
        get() = p.getBoolean("show_symbols", true)
        set(v) = p.edit().putBoolean("show_symbols", v).apply()
}

/**
 * Calls a user-controlled server-side gateway. No AI provider key is embedded in the APK.
 * Contract: POST {"action":"chat","text":"..."} -> {"text":"..."}
 */
class AiGateway(private val prefs: AppPrefs) {
    fun ask(text: String, done: (Result<String>) -> Unit) {
        val endpoint = prefs.gatewayUrl
        if (endpoint.isBlank()) {
            done(Result.failure(IllegalStateException("Chưa cấu hình AI Gateway. Dịch vẫn dùng được miễn phí trên thiết bị.")))
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

class QKeyboardView(
    context: Context,
    private val prefs: AppPrefs,
    private val listener: Listener
) : View(context) {

    interface Listener {
        fun onKey(text: String)
        fun onBackspace()
        fun onEnter()
        fun onSpace()
        fun onToolbarAction(action: String)
        fun onSuggestion(text: String)
        fun onReferenceAction(action: String)
    }

    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val keyBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }
    private val panelBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(242, 244, 249) }
    private val referenceBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }

    private var panelMode = "suggestions"
    private var referenceText: String? = null
    private var keys = mutableListOf<Key>()
    private val referenceActions = listOf("insert", "replace", "copy")

    var suggestions: List<String> = listOf("anh", "em", "không")

    data class Key(val rect: RectF, val value: String, val small: String? = null)

    fun showSuggestions() { panelMode = "suggestions"; invalidate() }
    fun showTools() { panelMode = "tools"; invalidate() }
    fun showLibrary() { panelMode = "library"; invalidate() }
    fun showAiActions() { panelMode = "ai"; invalidate() }

    fun setReference(text: String?) {
        referenceText = text?.takeIf { it.isNotBlank() }
        requestLayout()
        invalidate()
    }

    fun clearReference() = setReference(null)

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        val scale = prefs.keyboardHeightPercent / 100f
        val h = (300f * scale * resources.displayMetrics.density).toInt()
        setMeasuredDimension(w, h)
    }

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        c.drawColor(panelBg.color)
        keys.clear()

        val d = resources.displayMetrics.density
        val referenceH = if (referenceText != null) 38f * d else 0f
        val toolbarH = 36f * d
        val topPad = 3f * d

        if (referenceText != null) drawReference(c, referenceH)
        drawToolbar(c, referenceH, toolbarH)

        val rows = listOf(
            listOf("1","2","3","4","5","6","7","8","9","0"),
            listOf("q","w","e","r","t","y","u","i","o","p"),
            listOf("a","s","d","f","g","h","j","k","l"),
            listOf("⇧","z","x","c","v","b","n","m","⌫")
        )
        val secondary = mapOf(
            "a" to "@", "s" to "#", "d" to "$", "f" to "%", "g" to "-", "h" to "+", "j" to "(", "k" to ")", "l" to "'",
            "z" to "*", "x" to "\"", "c" to "'", "v" to ":", "b" to ";", "n" to "!", "m" to "?"
        )

        val gap = 3f * d * (prefs.gapPercent / 100f)
        val side = 5f * d
        val startY = referenceH + toolbarH + topPad
        val availableH = height - startY - 4f * d
        val rowH = availableH / 5f
        var y = startY

        for ((ri, row) in rows.withIndex()) {
            val indent = if (ri == 2) 19f * d else 0f
            val availableW = width - side * 2 - indent * 2 - gap * (row.size - 1)
            val kw = availableW / row.size
            var x = side + indent
            for (v in row) {
                val r = RectF(x, y, x + kw, y + rowH - gap)
                val small = if (prefs.showSymbols) secondary[v] else null
                drawKey(c, r, v.uppercase(), small, rowH)
                keys += Key(r, v, small)
                x += kw + gap
            }
            y += rowH
        }

        val bottom = listOf("?123", "VI", ",", "SPACE", "⌨", ".", "↵")
        val weights = listOf(1.05f, 0.72f, 0.58f, 3.35f, 0.72f, 0.58f, 1.0f)
        val totalWeight = weights.sum()
        val availableW = width - side * 2 - gap * (bottom.size - 1)
        var x = side
        for (i in bottom.indices) {
            val kw = availableW * weights[i] / totalWeight
            val r = RectF(x, y, x + kw, y + rowH - gap)
            val label = if (bottom[i] == "SPACE") "Q AI" else bottom[i]
            drawKey(c, r, label, null, rowH)
            keys += Key(r, bottom[i])
            x += kw + gap
        }
    }

    private fun drawReference(c: Canvas, h: Float) {
        val d = resources.displayMetrics.density
        val pad = 5f * d
        val r = RectF(pad, 3f * d, width - pad, h - 2f * d)
        c.drawRoundRect(r, 9f * d, 9f * d, referenceBg)

        val actionWidth = 34f * d
        val rightStart = width - pad - actionWidth * 3
        p.textAlign = Paint.Align.LEFT
        p.color = Color.rgb(45, 45, 50)
        p.textSize = 13f * d
        val availableChars = ((rightStart - 18f * d) / (7f * d)).toInt().coerceAtLeast(8)
        val shown = referenceText.orEmpty().replace('\n', ' ').let {
            if (it.length > availableChars) it.take(availableChars - 1) + "…" else it
        }
        c.drawText(shown, 12f * d, h / 2f + 5f * d, p)

        val icons = listOf("↳", "↻", "⧉")
        p.textAlign = Paint.Align.CENTER
        p.textSize = 19f * d
        icons.forEachIndexed { i, icon ->
            c.drawText(icon, rightStart + actionWidth * (i + .5f), h / 2f + 6f * d, p)
        }
    }

    private fun drawToolbar(c: Canvas, top: Float, h: Float) {
        val d = resources.displayMetrics.density
        val centerY = top + h / 2f + 6f * d
        when (panelMode) {
            "suggestions" -> {
                p.color = Color.rgb(45, 45, 50)
                p.textAlign = Paint.Align.CENTER
                p.textSize = 21f * d
                c.drawText("☰", 27f * d, centerY, p)

                val start = 58f * d
                val end = width - 44f * d
                val slot = (end - start) / 3f
                p.textSize = 15f * d
                suggestions.take(3).forEachIndexed { i, s ->
                    c.drawText(compact(s, 14), start + slot * (i + .5f), centerY, p)
                }
                p.textSize = 20f * d
                c.drawText("☺", width - 22f * d, centerY, p)
            }
            "tools" -> drawIconRow(c, top, h, listOf("←", "🌐", "✦", "▣", "⚙"))
            "library" -> drawIconRow(c, top, h, listOf("←", "📝", "📋", "⚡", "⚙"))
            "ai" -> drawIconRow(c, top, h, listOf("←", "🌐", "↻", "💬", "✦"))
        }
    }

    private fun drawIconRow(c: Canvas, top: Float, h: Float, icons: List<String>) {
        val d = resources.displayMetrics.density
        p.color = Color.rgb(40, 40, 45)
        p.textAlign = Paint.Align.CENTER
        p.textSize = 20f * d
        val slot = width / icons.size.toFloat()
        icons.forEachIndexed { i, icon ->
            c.drawText(icon, slot * (i + .5f), top + h / 2f + 7f * d, p)
        }
    }

    private fun drawKey(c: Canvas, r: RectF, label: String, small: String?, rowH: Float) {
        val d = resources.displayMetrics.density
        c.drawRoundRect(r, 7f * d, 7f * d, keyBg)
        p.color = Color.BLACK
        p.textAlign = Paint.Align.CENTER
        val base = if (label.length > 2) 13f else 23f
        p.textSize = base * d * (prefs.keyTextPercent / 100f)
        c.drawText(label, r.centerX(), r.centerY() + p.textSize * .33f, p)
        if (small != null) {
            p.textSize = 9.5f * d
            p.color = Color.DKGRAY
            c.drawText(small, r.centerX() + r.width() * .23f, r.top + (rowH * .22f), p)
        }
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.action != MotionEvent.ACTION_UP) return true
        if (prefs.haptic) performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)

        val d = resources.displayMetrics.density
        val referenceH = if (referenceText != null) 38f * d else 0f
        val toolbarH = 36f * d

        if (referenceText != null && e.y < referenceH) {
            val actionWidth = 34f * d
            val rightStart = width - 5f * d - actionWidth * 3
            if (e.x >= rightStart) {
                val idx = floor((e.x - rightStart) / actionWidth).toInt().coerceIn(0, 2)
                listener.onReferenceAction(referenceActions[idx])
            } else listener.onReferenceAction("insert")
            return true
        }

        if (e.y >= referenceH && e.y < referenceH + toolbarH) {
            when (panelMode) {
                "suggestions" -> {
                    if (e.x < 54f * d) listener.onToolbarAction("menu")
                    else if (e.x > width - 42f * d) listener.onToolbarAction("emoji")
                    else {
                        val start = 58f * d
                        val end = width - 44f * d
                        val idx = floor((e.x - start) / ((end - start) / 3f)).toInt()
                        suggestions.getOrNull(idx)?.let { listener.onSuggestion(it) }
                    }
                }
                "tools" -> {
                    val actions = listOf("back", "translate", "ai", "library", "settings")
                    listener.onToolbarAction(actions[slotIndex(e.x, actions.size)])
                }
                "library" -> {
                    val actions = listOf("back", "notes", "clipboard", "shortcuts", "settings")
                    listener.onToolbarAction(actions[slotIndex(e.x, actions.size)])
                }
                "ai" -> {
                    val actions = listOf("back", "ai_translate", "rewrite", "comment", "chat")
                    listener.onToolbarAction(actions[slotIndex(e.x, actions.size)])
                }
            }
            return true
        }

        val key = keys.firstOrNull { it.rect.contains(e.x, e.y) } ?: return true
        when (key.value) {
            "⌫" -> listener.onBackspace()
            "↵" -> listener.onEnter()
            "SPACE" -> listener.onSpace()
            "⇧" -> Unit
            "?123", "VI", "⌨" -> Unit
            else -> listener.onKey(key.value)
        }
        return true
    }

    private fun slotIndex(x: Float, count: Int): Int =
        floor(x / (width / count.toFloat())).toInt().coerceIn(0, count - 1)

    private fun compact(s: String, max: Int): String {
        val oneLine = s.replace('\n', ' ')
        return if (oneLine.length <= max) oneLine else oneLine.take(max - 1) + "…"
    }
}

class QKeyboardService : InputMethodService(), QKeyboardView.Listener {
    private lateinit var keyboard: QKeyboardView
    private lateinit var prefs: AppPrefs
    private lateinit var translator: TranslationManager
    private lateinit var ai: AiGateway

    private val telex = TelexEngine()
    private var composing = ""
    private var translatedCandidate: String? = null
    private var aiCandidate: String? = null
    private var lastContextText: String = ""
    private var sensitiveField = false

    override fun onCreate() {
        super.onCreate()
        prefs = AppPrefs(this)
        translator = TranslationManager(this)
        ai = AiGateway(prefs)
    }

    override fun onCreateInputView(): View {
        keyboard = QKeyboardView(this, prefs, this)
        return keyboard
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        super.onStartInput(attribute, restarting)
        telex.reset()
        composing = ""
        translatedCandidate = null
        aiCandidate = null
        lastContextText = ""
        sensitiveField = isSensitive(attribute?.inputType ?: 0)
        if (::keyboard.isInitialized) {
            keyboard.clearReference()
            keyboard.suggestions = listOf("anh", "em", "không")
            keyboard.showSuggestions()
        }
    }

    override fun onKey(text: String) {
        if (text.length == 1 && text[0].isLetter()) {
            composing = telex.push(text[0])
            currentInputConnection.setComposingText(composing, 1)
            keyboard.suggestions = suggest(composing)
            keyboard.showSuggestions()
        } else {
            commitComposing()
            currentInputConnection.commitText(text, 1)
        }
    }

    override fun onBackspace() {
        if (telex.currentRaw().isNotEmpty()) {
            composing = telex.backspace()
            currentInputConnection.setComposingText(composing, 1)
            keyboard.suggestions = suggest(composing)
            keyboard.showSuggestions()
        } else currentInputConnection.deleteSurroundingText(1, 0)
    }

    override fun onSpace() {
        val expanded = expandShortcut(composing)
        if (expanded != null) currentInputConnection.setComposingText(expanded, 1)
        commitComposing()
        currentInputConnection.commitText(" ", 1)
        keyboard.suggestions = listOf("anh", "em", "không")
        keyboard.showSuggestions()
    }

    override fun onEnter() {
        commitComposing()
        currentInputConnection.sendKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_ENTER))
        currentInputConnection.sendKeyEvent(KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_ENTER))
    }

    override fun onToolbarAction(action: String) {
        when (action) {
            "menu" -> keyboard.showTools()
            "back" -> {
                keyboard.clearReference()
                keyboard.showSuggestions()
            }
            "library" -> keyboard.showLibrary()
            "ai" -> {
                if (sensitiveField) toast("AI đã tắt trong ô mật khẩu/PIN")
                else {
                    lastContextText = getContextText()
                    keyboard.showAiActions()
                }
            }
            "translate" -> {
                if (sensitiveField) toast("Dịch đã tắt trong ô mật khẩu/PIN")
                else translateContext(getContextText())
            }
            "ai_translate" -> {
                if (sensitiveField) toast("Dịch đã tắt trong ô mật khẩu/PIN")
                else translateContext(lastContextText.ifBlank { getContextText() })
            }
            "rewrite" -> runContextAi("Viết lại đoạn sau tự nhiên, rõ ràng, giữ nguyên ý. Chỉ trả về nội dung đã viết lại:\n")
            "comment" -> runContextAi("Viết một comment Facebook ngắn, tự nhiên, phù hợp với nội dung sau. Chỉ trả về comment:\n")
            "chat" -> runContextAi("Hãy trả lời hoặc xử lý nội dung sau một cách hữu ích và ngắn gọn:\n")
            "notes" -> showNotes()
            "clipboard" -> showClipboard()
            "shortcuts" -> showShortcuts()
            "settings" -> {
                keyboard.showSuggestions()
                startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
            "emoji" -> toast("Emoji picker sẽ hoàn thiện ở bản kế tiếp")
        }
    }

    override fun onSuggestion(text: String) {
        aiCandidate?.let { candidate ->
            if (text == compact(candidate)) {
                commitComposing()
                currentInputConnection.commitText(candidate, 1)
                aiCandidate = null
                keyboard.suggestions = listOf("anh", "em", "không")
                keyboard.showSuggestions()
                return
            }
        }

        if (prefs.notes.lines().contains(text)) {
            commitComposing()
            currentInputConnection.commitText(text, 1)
            keyboard.showSuggestions()
            return
        }

        if (text == "⧉" && aiCandidate != null) {
            copy(aiCandidate.orEmpty())
            toast("Đã sao chép")
            return
        }

        commitComposing()
        currentInputConnection.commitText(text + " ", 1)
        keyboard.showSuggestions()
    }

    override fun onReferenceAction(action: String) {
        val candidate = translatedCandidate ?: return
        when (action) {
            "copy" -> {
                copy(candidate)
                toast("Đã sao chép bản dịch")
            }
            "replace" -> {
                val selected = currentInputConnection.getSelectedText(0)?.toString().orEmpty()
                if (selected.isNotBlank()) currentInputConnection.commitText(candidate, 1)
                else {
                    val ctx = lastContextText
                    if (ctx.isNotBlank()) currentInputConnection.deleteSurroundingText(ctx.length, 0)
                    currentInputConnection.commitText(candidate, 1)
                }
                finishCandidate()
            }
            else -> {
                currentInputConnection.commitText(candidate, 1)
                finishCandidate()
            }
        }
    }

    private fun translateContext(textInput: String) {
        commitComposing()
        val text = textInput.trim()
        if (text.isBlank()) {
            toast("Chọn hoặc gõ đoạn cần dịch trước")
            keyboard.showSuggestions()
            return
        }
        lastContextText = text
        keyboard.setReference("${langLabel(prefs.sourceLang)} → ${langLabel(prefs.targetLang)} • Đang dịch…")
        keyboard.showSuggestions()
        translator.translate(text, prefs.sourceLang, prefs.targetLang) { result ->
            keyboard.post {
                result.onSuccess { out ->
                    translatedCandidate = out
                    keyboard.setReference(out)
                }.onFailure {
                    keyboard.clearReference()
                    toast("Không dịch được: ${it.message}")
                }
            }
        }
    }

    private fun runContextAi(instruction: String) {
        if (sensitiveField) {
            toast("AI đã tắt trong ô mật khẩu/PIN")
            return
        }
        val context = lastContextText.ifBlank { getContextText() }.trim()
        if (context.isBlank()) {
            toast("Chọn hoặc copy đoạn văn trước rồi bấm ✦")
            keyboard.showSuggestions()
            return
        }
        keyboard.suggestions = listOf("AI…", "", "")
        keyboard.showSuggestions()
        ai.ask(instruction + context) { result ->
            keyboard.post {
                result.onSuccess { out ->
                    aiCandidate = out
                    keyboard.suggestions = listOf(compact(out), "↳", "⧉")
                    keyboard.showSuggestions()
                }.onFailure {
                    toast(it.message ?: "AI lỗi")
                    keyboard.suggestions = listOf("anh", "em", "không")
                    keyboard.showSuggestions()
                }
            }
        }
    }

    private fun getContextText(): String {
        commitComposing()
        val selected = currentInputConnection.getSelectedText(0)?.toString().orEmpty().trim()
        if (selected.isNotBlank()) return selected
        val before = currentInputConnection.getTextBeforeCursor(800, 0)?.toString().orEmpty()
        return before.substringAfterLast('\n')
            .substringAfterLast('.')
            .substringAfterLast('!')
            .substringAfterLast('?')
            .trim()
    }

    private fun showNotes() {
        keyboard.suggestions = prefs.notes.lines().filter { it.isNotBlank() }.take(3)
            .ifEmpty { listOf("Chưa có ghi chú") }
        keyboard.showSuggestions()
    }

    private fun showClipboard() {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val text = cm.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty()
        if (text.isBlank()) {
            toast("Clipboard đang trống")
            keyboard.showSuggestions()
        } else {
            keyboard.suggestions = listOf(compact(text), "↳", "⧉")
            aiCandidate = text
            keyboard.showSuggestions()
        }
    }

    private fun showShortcuts() {
        keyboard.suggestions = prefs.shortcuts.lines().mapNotNull { line ->
            line.substringBefore('=', "").trim().takeIf { it.isNotBlank() }
        }.take(3).ifEmpty { listOf("Chưa có gõ tắt") }
        keyboard.showSuggestions()
    }

    private fun expandShortcut(value: String): String? {
        if (value.isBlank()) return null
        return prefs.shortcuts.lines().mapNotNull { line ->
            val idx = line.indexOf('=')
            if (idx <= 0) null else line.substring(0, idx).trim() to line.substring(idx + 1)
        }.firstOrNull { it.first == value }?.second
    }

    private fun suggest(v: String): List<String> = when {
        v.isBlank() -> listOf("anh", "em", "không")
        v.startsWith("a") -> listOf(v, "anh", "ạ")
        v.startsWith("e") -> listOf(v, "em", "em nhé")
        v.startsWith("k") -> listOf(v, "không", "khi")
        else -> listOf(v, "anh", "em")
    }

    private fun commitComposing() {
        if (telex.currentRaw().isNotEmpty()) {
            currentInputConnection.finishComposingText()
            telex.reset()
            composing = ""
        }
    }

    private fun finishCandidate() {
        translatedCandidate = null
        lastContextText = ""
        keyboard.clearReference()
        keyboard.suggestions = listOf("anh", "em", "không")
        keyboard.showSuggestions()
    }

    private fun copy(text: String) {
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("Q AI Keyboard", text))
    }

    private fun compact(s: String, max: Int = 18): String {
        val oneLine = s.replace('\n', ' ')
        return if (oneLine.length <= max) oneLine else oneLine.take(max - 1) + "…"
    }

    private fun isSensitive(inputType: Int): Boolean {
        val clazz = inputType and InputType.TYPE_MASK_CLASS
        val variation = inputType and InputType.TYPE_MASK_VARIATION
        return clazz == InputType.TYPE_CLASS_TEXT && variation in setOf(
            InputType.TYPE_TEXT_VARIATION_PASSWORD,
            InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD,
            InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
        ) || clazz == InputType.TYPE_CLASS_NUMBER && variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_SHORT).show()

    private fun langLabel(code: String) = when (code) {
        "vi" -> "VI"
        "en" -> "EN"
        "ja" -> "JA"
        "zh" -> "ZH"
        "ko" -> "KO"
        else -> code.uppercase()
    }
}
